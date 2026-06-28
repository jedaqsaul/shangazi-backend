"""
Daraja Controller
-----------------
Handles the async callback from Safaricom after STK Push.
Security is critical here:
  1. IP address must match Safaricom's known IP ranges
  2. Payload structure must be valid
  3. Result code must be meaningful

Daraja expects a 200 response immediately — any slow processing
should be offloaded (future: Celery task queue).
"""

from flask import request, current_app, jsonify
from app.services.daraja_service import DarajaService
from app.services.donation_service import DonationService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DarajaController:

    @staticmethod
    def callback():
        """
        POST /api/daraja/callback
        Receives async payment result from Safaricom.
        Must respond with 200 immediately — Daraja retries on failure.
        """

        # ── Security Check 1: IP Whitelist ────────────────────────────────
        client_ip = request.remote_addr
        # Support X-Forwarded-For for reverse proxy deployments
        forwarded_ip = request.headers.get("X-Forwarded-For")
        if forwarded_ip:
            client_ip = forwarded_ip.split(",")[0].strip()

        whitelisted_ips = current_app.config.get("DARAJA_WHITELISTED_IPS", [])
        flask_env = current_app.config.get("FLASK_ENV", "development")

        if flask_env == "production" and client_ip not in whitelisted_ips:
            logger.warning(
                "Callback rejected: unauthorized IP",
                extra={"extra": {"ip": client_ip, "whitelisted": whitelisted_ips}}
            )
            # Still return 200 to prevent Daraja retry loops on rejected IPs
            return jsonify({"ResultCode": 1, "ResultDesc": "Rejected"}), 200

        # ── Security Check 2: Payload Validation ──────────────────────────
        payload = request.get_json(silent=True)

        if not payload:
            logger.warning(
                "Callback received with empty payload",
                extra={"extra": {"ip": client_ip}}
            )
            return jsonify({"ResultCode": 1, "ResultDesc": "Empty payload"}), 200

        try:
            parsed = DarajaService.parse_callback(payload)
        except ValueError as e:
            logger.warning(
                "Callback payload parsing failed",
                extra={"extra": {"error": str(e), "ip": client_ip}}
            )
            return jsonify({"ResultCode": 1, "ResultDesc": "Invalid payload"}), 200

        # ── Process the Callback ──────────────────────────────────────────
        try:
            DonationService.process_callback(parsed)
        except Exception as e:
            logger.error(
                "Callback processing error",
                extra={"extra": {"error": str(e), "checkout_id": parsed.get("checkout_request_id")}}
            )
            # Still return 200 to Daraja; our internal error doesn't need a retry
            return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), 200

        logger.info(
            "Daraja callback processed successfully",
            extra={"extra": {
                "checkout_request_id": parsed.get("checkout_request_id"),
                "result_code": parsed.get("result_code"),
            }}
        )

        # Daraja requires this exact response format to acknowledge receipt
        return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"}), 200
