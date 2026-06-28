"""
Donation Model
--------------
Core financial record of the platform.
Every STK Push initiation creates a pending donation record.
The Daraja callback updates it to completed, failed, or cancelled.

payment_status lifecycle:
  pending   → STK Push sent, awaiting user response
  completed → User paid successfully, receipt recorded
  failed    → Payment failed (wrong PIN, timeout, insufficient funds)
  cancelled → User cancelled the STK prompt
"""

import uuid
from datetime import datetime, timezone
from app.extensions import db


class Donation(db.Model):
    __tablename__ = "donations"

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # Donor Information
    donor_name = db.Column(db.String(150), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False, index=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)

    # Daraja Transaction Identifiers
    merchant_request_id = db.Column(db.String(100), unique=True, nullable=True)
    checkout_request_id = db.Column(db.String(100), unique=True, nullable=True, index=True)

    # Populated by Daraja Callback
    mpesa_receipt_number = db.Column(db.String(50), nullable=True)
    result_code = db.Column(db.String(10), nullable=True)
    result_description = db.Column(db.String(255), nullable=True)
    transaction_date = db.Column(db.DateTime(timezone=True), nullable=True)

    # Status Tracking
    payment_status = db.Column(
        db.Enum("pending", "completed", "failed", "cancelled", name="payment_status"),
        nullable=False,
        default="pending",
        index=True
    )

    # Timestamps
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def mark_completed(self, receipt: str, result_desc: str, transaction_date: datetime) -> None:
        """Update donation to completed state after successful callback."""
        self.payment_status = "completed"
        self.mpesa_receipt_number = receipt
        self.result_code = "0"
        self.result_description = result_desc
        self.transaction_date = transaction_date

    def mark_failed(self, result_code: str, result_desc: str) -> None:
        """Update donation to failed state after failed callback."""
        self.payment_status = "failed"
        self.result_code = str(result_code)
        self.result_description = result_desc

    def mark_cancelled(self, result_code: str, result_desc: str) -> None:
        """Update donation to cancelled state when the user dismisses the STK prompt."""
        self.payment_status = "cancelled"
        self.result_code = str(result_code)
        self.result_description = result_desc

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "donor_name": self.donor_name,
            "phone_number": self.phone_number,
            "amount": float(self.amount),
            "merchant_request_id": self.merchant_request_id,
            "checkout_request_id": self.checkout_request_id,
            "mpesa_receipt_number": self.mpesa_receipt_number,
            "result_code": self.result_code,
            "result_description": self.result_description,
            "payment_status": self.payment_status,
            "transaction_date": self.transaction_date.isoformat() if self.transaction_date else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def to_export_dict(self) -> dict:
        """Flat dict suitable for CSV/Excel export."""
        return {
            "ID": self.id,
            "Donor Name": self.donor_name,
            "Phone Number": self.phone_number,
            "Amount (KES)": float(self.amount),
            "Receipt Number": self.mpesa_receipt_number or "N/A",
            "Status": self.payment_status,
            "Transaction Date": self.transaction_date.isoformat() if self.transaction_date else "N/A",
            "Created At": self.created_at.isoformat(),
        }

    def __repr__(self) -> str:
        return f"<Donation {self.id} | {self.donor_name} | KES {self.amount} | {self.payment_status}>"
