"""
Helpers Utility
---------------
Shared utility functions used across services and controllers.
"""

import re
from datetime import datetime, timezone


def normalize_phone_number(phone: str) -> str:
    """
    Normalize Kenyan phone numbers to Safaricom Daraja format (2547XXXXXXXX).

    Accepted input formats:
        0712345678   → 254712345678
        +254712345678 → 254712345678
        254712345678  → 254712345678
        07XXXXXXXX   → 2547XXXXXXXX
    """
    phone = re.sub(r"\s+|-", "", phone.strip())

    if phone.startswith("+254"):
        phone = phone[1:]  # Remove leading +
    elif phone.startswith("0"):
        phone = "254" + phone[1:]  # Replace leading 0 with 254

    return phone


def is_valid_kenyan_phone(phone: str) -> bool:
    """
    Validate that a phone number is a valid Kenyan mobile number.
    After normalization, must be 12 digits starting with 2547.
    Covers Safaricom (2547), Airtel (2541X), and Telkom (2547X) ranges.
    """
    normalized = normalize_phone_number(phone)
    return bool(re.match(r"^254[17]\d{8}$", normalized))


def mask_phone_number(phone: str) -> str:
    """
    Mask a phone number for safe logging.
    254712345678 → 2547****5678
    """
    if len(phone) >= 8:
        return phone[:4] + "****" + phone[-4:]
    return "****"


def utc_now() -> datetime:
    """Return current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


def format_amount(amount: float) -> str:
    """Format donation amount as KES currency string."""
    return f"KES {amount:,.2f}"


def paginate_query(query, page: int, per_page: int = 20) -> dict:
    """
    Apply pagination to a SQLAlchemy query and return
    both the page items and pagination metadata.
    """
    per_page = min(per_page, 100)  # Hard cap at 100 per page
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return {
        "items": pagination.items,
        "pagination": {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total": pagination.total,
            "pages": pagination.pages,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev,
        }
    }
