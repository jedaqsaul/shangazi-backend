"""
Donation Controller
-------------------
Handles HTTP layer for public donation endpoints.
Validates input, calls DonationService, formats responses.
"""

from flask import request
from app.services.donation_service import DonationService
from app.middleware.validators import validate_request, InitiateDonationSchema
from app.utils.error_handlers import error_response, success_response
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DonationController:

    @staticmethod
    def initiate():
        """
        POST /api/donations/initiate
        Public endpoint. Validates donor info and triggers STK Push.
        """
        data, errors = validate_request(InitiateDonationSchema, request.get_json())
        if errors:
            return error_response(str(errors), "VALIDATION_ERROR", 400)

        try:
            result = DonationService.initiate_donation(
                donor_name=data["donor_name"],
                phone_number=data["phone_number"],
                amount=data["amount"],
            )
            return success_response(
                data=result,
                message="Payment request sent to your phone.",
                status_code=201,
            )

        except RuntimeError as e:
            # Daraja errors (network, bad credentials, etc.)
            return error_response(str(e), "PAYMENT_ERROR", 502)

        except Exception as e:
            logger.error(
                "Donation initiation failed unexpectedly",
                extra={"extra": {"error": str(e)}}
            )
            return error_response("Failed to initiate payment.", "SERVER_ERROR", 500)

    @staticmethod
    def status(checkout_request_id: str):
        """
        GET /api/donations/status/<checkout_request_id>
        Public endpoint. Frontend polls this to get payment result.
        """
        if not checkout_request_id or len(checkout_request_id) > 100:
            return error_response("Invalid checkout request ID.", "VALIDATION_ERROR", 400)

        try:
            result = DonationService.get_donation_status(checkout_request_id)
            return success_response(data=result)

        except ValueError:
            return error_response("Donation not found.", "NOT_FOUND", 404)

        except Exception as e:
            logger.error(
                "Status check failed",
                extra={"extra": {"error": str(e), "id": checkout_request_id}}
            )
            return error_response("Failed to retrieve payment status.", "SERVER_ERROR", 500)
