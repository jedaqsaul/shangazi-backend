"""
Donation Service
----------------
Business logic for creating, updating, and querying donations.
The Daraja service handles API calls; this service handles
the database side of the donation lifecycle.
"""

from datetime import datetime
from sqlalchemy import or_, func
from app.extensions import db
from app.models.donation import Donation
from app.services.daraja_service import DarajaService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DonationService:

    @staticmethod
    def initiate_donation(donor_name: str, phone_number: str, amount: float) -> dict:
        """
        Create a pending donation record and trigger STK Push.
        Returns checkout_request_id for frontend polling.

        Flow:
          1. Call Daraja STK Push
          2. Create pending Donation record with Daraja IDs
          3. Return checkout_request_id to frontend for polling
        """
        # Step 1: Trigger STK Push (raises RuntimeError on failure)
        daraja_response = DarajaService.initiate_stk_push(
            phone_number=phone_number,
            amount=amount,
            account_reference=donor_name,
        )

        # Step 2: Persist pending record
        donation = Donation(
            donor_name=donor_name,
            phone_number=phone_number,
            amount=amount,
            merchant_request_id=daraja_response.get("MerchantRequestID"),
            checkout_request_id=daraja_response.get("CheckoutRequestID"),
            payment_status="pending",
        )
        db.session.add(donation)
        db.session.commit()

        logger.info(
            "Donation record created",
            extra={"extra": {
                "donation_id": donation.id,
                "checkout_request_id": donation.checkout_request_id,
                "amount": amount,
            }}
        )

        return {
            "donation_id": donation.id,
            "checkout_request_id": donation.checkout_request_id,
            "message": "Payment request sent to your phone. Please enter your M-Pesa PIN.",
        }

    @staticmethod
    def process_callback(parsed_callback: dict) -> None:
        """
        Update a donation record based on Daraja callback data.
        Called by the daraja_controller after callback validation.
        """
        checkout_request_id = parsed_callback.get("checkout_request_id")
        result_code = parsed_callback.get("result_code")

        donation = Donation.query.filter_by(
            checkout_request_id=checkout_request_id
        ).first()

        if not donation:
            logger.warning(
                "Callback received for unknown donation",
                extra={"extra": {"checkout_request_id": checkout_request_id}}
            )
            return

        if donation.payment_status != "pending":
            logger.info(
                "Callback received for already-processed donation — skipping",
                extra={"extra": {
                    "donation_id": donation.id,
                    "current_status": donation.payment_status,
                }}
            )
            return

        # Daraja ResultCode 1032 = "Request cancelled by user"
        DARAJA_CANCELLED_CODE = 1032

        if result_code == 0:
            donation.mark_completed(
                receipt=parsed_callback["mpesa_receipt_number"],
                result_desc=parsed_callback["result_description"],
                transaction_date=parsed_callback["transaction_date"],
            )
            logger.info(
                "Donation completed",
                extra={"extra": {
                    "donation_id": donation.id,
                    "receipt": parsed_callback["mpesa_receipt_number"],
                    "amount": float(donation.amount),
                }}
            )
        elif result_code == DARAJA_CANCELLED_CODE:
            donation.mark_cancelled(
                result_code=result_code,
                result_desc=parsed_callback["result_description"],
            )
            logger.info(
                "Donation cancelled by user",
                extra={"extra": {
                    "donation_id": donation.id,
                    "result_code": result_code,
                }}
            )
        else:
            donation.mark_failed(
                result_code=result_code,
                result_desc=parsed_callback["result_description"],
            )
            logger.warning(
                "Donation failed",
                extra={"extra": {
                    "donation_id": donation.id,
                    "result_code": result_code,
                    "result_desc": parsed_callback["result_description"],
                }}
            )

        db.session.commit()

    @staticmethod
    def get_donation_status(checkout_request_id: str) -> dict:
        """
        Return current status of a donation for frontend polling.
        Returns a minimal status object — not full donor data.
        """
        donation = Donation.query.filter_by(
            checkout_request_id=checkout_request_id
        ).first()

        if not donation:
            raise ValueError("Donation not found.")

        return {
            "donation_id": donation.id,
            "payment_status": donation.payment_status,
            "amount": float(donation.amount),
            "mpesa_receipt_number": donation.mpesa_receipt_number,
            "message": DonationService._status_message(donation.payment_status),
        }

    @staticmethod
    def _status_message(status: str) -> str:
        messages = {
            "pending": "Waiting for payment confirmation. Please enter your M-Pesa PIN.",
            "completed": "Thank you! Your donation was received successfully.",
            "failed": "Payment was not completed. Please try again.",
            "cancelled": "Payment was cancelled.",
        }
        return messages.get(status, "Unknown status.")

    @staticmethod
    def get_donations(
        page: int = 1,
        per_page: int = 20,
        status: str | None = None,
        search: str | None = None,
        date_from=None,
        date_to=None,
    ) -> dict:
        """
        Paginated, filterable donation list for the admin dashboard.
        """
        query = Donation.query

        if status:
            query = query.filter(Donation.payment_status == status)

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Donation.donor_name.ilike(search_term),
                    Donation.phone_number.ilike(search_term),
                    Donation.mpesa_receipt_number.ilike(search_term),
                )
            )

        if date_from:
            query = query.filter(Donation.created_at >= date_from)

        if date_to:
            query = query.filter(Donation.created_at <= date_to)

        query = query.order_by(Donation.created_at.desc())

        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        return {
            "donations": [d.to_dict() for d in pagination.items],
            "pagination": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total": pagination.total,
                "pages": pagination.pages,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev,
            }
        }

    @staticmethod
    def get_stats() -> dict:
        """
        Aggregate donation statistics for the admin dashboard.
        """
        total_donations = Donation.query.count()
        completed = Donation.query.filter_by(payment_status="completed")
        failed = Donation.query.filter_by(payment_status="failed")
        pending = Donation.query.filter_by(payment_status="pending")

        total_amount = db.session.query(
            func.sum(Donation.amount)
        ).filter_by(payment_status="completed").scalar() or 0.0

        return {
            "total_donations": total_donations,
            "completed_donations": completed.count(),
            "failed_donations": failed.count(),
            "pending_donations": pending.count(),
            "total_amount_collected": float(total_amount),
        }

    @staticmethod
    def get_all_for_export(status: str | None = None) -> list[dict]:
        """Return all donations as flat dicts for CSV export."""
        query = Donation.query
        if status:
            query = query.filter_by(payment_status=status)
        donations = query.order_by(Donation.created_at.desc()).all()
        return [d.to_export_dict() for d in donations]
