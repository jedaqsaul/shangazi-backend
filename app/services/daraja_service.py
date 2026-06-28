"""
Daraja Service
--------------
Encapsulates all communication with Safaricom's Daraja API.
No credentials are hardcoded — all sourced from app config.
Access tokens are obtained fresh per request to avoid expiry issues.

Key methods:
  get_access_token()  → OAuth2 bearer token from Daraja
  initiate_stk_push() → Send STK Push to donor's phone
  parse_callback()    → Validate and parse the async callback payload
"""

import base64
import requests
from datetime import datetime, timezone
from flask import current_app
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DarajaService:

    @staticmethod
    def _get_base_url() -> str:
        env = current_app.config.get("DARAJA_ENV", "sandbox")
        if env == "production":
            return "https://api.safaricom.co.ke"
        return "https://sandbox.safaricom.co.ke"

    @staticmethod
    def get_access_token() -> str:
        """
        Obtain a short-lived OAuth2 access token from Daraja.
        Tokens expire in ~1 hour. We fetch fresh per STK request
        to keep the logic simple and avoid caching stale tokens.
        Raises RuntimeError on failure.
        """
        consumer_key = current_app.config["DARAJA_CONSUMER_KEY"]
        consumer_secret = current_app.config["DARAJA_CONSUMER_SECRET"]
        base_url = DarajaService._get_base_url()

        credentials = f"{consumer_key}:{consumer_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()

        try:
            response = requests.get(
                f"{base_url}/oauth/v1/generate?grant_type=client_credentials",
                headers={"Authorization": f"Basic {encoded}"},
                timeout=15,
            )
            response.raise_for_status()
            token = response.json().get("access_token")

            if not token:
                raise RuntimeError("Access token missing from Daraja response.")

            logger.info("Daraja access token obtained successfully")
            return token

        except requests.exceptions.Timeout:
            logger.error("Daraja token request timed out")
            raise RuntimeError("Payment service is temporarily unavailable. Please try again.")

        except requests.exceptions.RequestException as e:
            logger.error(
                "Daraja token request failed",
                extra={"extra": {"error": str(e)}}
            )
            raise RuntimeError("Unable to connect to payment service.")

    @staticmethod
    def generate_password() -> tuple[str, str]:
        """
        Generate the Daraja STK Push password and timestamp.
        Password = Base64(Shortcode + Passkey + Timestamp)
        Returns (password, timestamp).
        """
        shortcode = current_app.config["DARAJA_SHORTCODE"]
        passkey = current_app.config["DARAJA_PASSKEY"]
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        raw = f"{shortcode}{passkey}{timestamp}"
        password = base64.b64encode(raw.encode()).decode()
        return password, timestamp

    @staticmethod
    def initiate_stk_push(
        phone_number: str,
        amount: float,
        account_reference: str,
        transaction_desc: str = "Shangazi Foundation Donation",
    ) -> dict:
        """
        Send an STK Push payment request to the donor's phone.

        Args:
            phone_number: Normalized Kenyan number (2547XXXXXXXX)
            amount: Donation amount in KES (integers only for Daraja)
            account_reference: Donor name or donation ID for reference
            transaction_desc: Description shown on M-Pesa prompt

        Returns:
            Daraja response dict containing MerchantRequestID and CheckoutRequestID

        Raises:
            RuntimeError: If Daraja rejects the request or network fails
        """
        access_token = DarajaService.get_access_token()
        password, timestamp = DarajaService.generate_password()

        shortcode = current_app.config["DARAJA_SHORTCODE"]
        callback_url = current_app.config["DARAJA_CALLBACK_URL"]
        base_url = DarajaService._get_base_url()

        payload = {
            "BusinessShortCode": shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(amount),  # Daraja requires integer amounts
            "PartyA": phone_number,
            "PartyB": shortcode,
            "PhoneNumber": phone_number,
            "CallBackURL": callback_url,
            "AccountReference": account_reference[:12],  # Daraja limit
            "TransactionDesc": transaction_desc[:13],    # Daraja limit
        }

        logger.info(
            "Initiating STK Push",
            extra={"extra": {
                "phone": phone_number[:6] + "****",  # Partial mask
                "amount": amount,
            }}
        )

        try:
            response = requests.post(
                f"{base_url}/mpesa/stkpush/v1/processrequest",
                json=payload,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            # Daraja uses ResponseCode "0" to indicate success
            if data.get("ResponseCode") != "0":
                error_msg = data.get("ResponseDescription", "STK Push failed.")
                logger.error(
                    "STK Push rejected by Daraja",
                    extra={"extra": {"response": data}}
                )
                raise RuntimeError(error_msg)

            logger.info(
                "STK Push initiated successfully",
                extra={"extra": {
                    "merchant_request_id": data.get("MerchantRequestID"),
                    "checkout_request_id": data.get("CheckoutRequestID"),
                }}
            )
            return data

        except requests.exceptions.Timeout:
            logger.error("STK Push request timed out")
            raise RuntimeError("Payment request timed out. Please try again.")

        except requests.exceptions.RequestException as e:
            logger.error(
                "STK Push network error",
                extra={"extra": {"error": str(e)}}
            )
            raise RuntimeError("Payment service is unavailable. Please try again.")

    @staticmethod
    def parse_callback(payload: dict) -> dict:
        """
        Parse and extract relevant data from a Daraja STK Push callback.

        Daraja callback structure:
        {
          "Body": {
            "stkCallback": {
              "MerchantRequestID": "...",
              "CheckoutRequestID": "...",
              "ResultCode": 0,
              "ResultDesc": "The service request is processed successfully.",
              "CallbackMetadata": {
                "Item": [
                  {"Name": "Amount", "Value": 100},
                  {"Name": "MpesaReceiptNumber", "Value": "ABC123"},
                  {"Name": "TransactionDate", "Value": 20241120143500},
                  {"Name": "PhoneNumber", "Value": 254712345678}
                ]
              }
            }
          }
        }

        Returns structured dict with all relevant fields.
        Raises ValueError if payload structure is invalid.
        """
        try:
            stk_callback = payload["Body"]["stkCallback"]
        except (KeyError, TypeError):
            raise ValueError("Invalid callback payload structure.")

        result_code = stk_callback.get("ResultCode")
        result_desc = stk_callback.get("ResultDesc", "")
        merchant_request_id = stk_callback.get("MerchantRequestID")
        checkout_request_id = stk_callback.get("CheckoutRequestID")

        parsed = {
            "merchant_request_id": merchant_request_id,
            "checkout_request_id": checkout_request_id,
            "result_code": result_code,
            "result_description": result_desc,
            "amount": None,
            "mpesa_receipt_number": None,
            "transaction_date": None,
            "phone_number": None,
        }

        # Metadata only present on successful payments (ResultCode == 0)
        if result_code == 0:
            metadata_items = (
                stk_callback
                .get("CallbackMetadata", {})
                .get("Item", [])
            )
            meta_map = {item["Name"]: item.get("Value") for item in metadata_items}

            parsed["amount"] = meta_map.get("Amount")
            parsed["mpesa_receipt_number"] = meta_map.get("MpesaReceiptNumber")
            parsed["phone_number"] = str(meta_map.get("PhoneNumber", ""))

            # Parse Daraja's compact timestamp format: YYYYMMDDHHmmss
            raw_date = meta_map.get("TransactionDate")
            if raw_date:
                try:
                    parsed["transaction_date"] = datetime.strptime(
                        str(raw_date), "%Y%m%d%H%M%S"
                    ).replace(tzinfo=timezone.utc)
                except ValueError:
                    parsed["transaction_date"] = datetime.now(timezone.utc)

        logger.info(
            "Daraja callback parsed",
            extra={"extra": {
                "checkout_request_id": checkout_request_id,
                "result_code": result_code,
                "receipt": parsed.get("mpesa_receipt_number"),
            }}
        )

        return parsed
