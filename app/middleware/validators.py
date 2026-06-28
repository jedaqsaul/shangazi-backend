"""
Validators / Request Schemas
----------------------------
All incoming request bodies are validated here using marshmallow.
Controllers call these before passing data to services.
Validation errors return structured 400 responses.
"""

import re
from marshmallow import Schema, fields, validate, validates, ValidationError, post_load
from app.utils.helpers import normalize_phone_number, is_valid_kenyan_phone


# ─── Auth Schemas ─────────────────────────────────────────────────────────────

class LoginSchema(Schema):
    email = fields.Email(required=True, error_messages={"required": "Email is required."})
    password = fields.Str(
        required=True,
        load_only=True,
        error_messages={"required": "Password is required."}
    )


class CreateUserSchema(Schema):
    username = fields.Str(
        required=True,
        validate=validate.Length(min=3, max=80),
        error_messages={"required": "Username is required."}
    )
    email = fields.Email(required=True)
    password = fields.Str(
        required=True,
        load_only=True,
        validate=validate.Length(min=8, max=128),
        error_messages={"required": "Password is required."}
    )
    role = fields.Str(
        load_default="admin",
        validate=validate.OneOf(["super_admin", "admin"])
    )

    @validates("password")
    def validate_password_strength(self, value: str):
        """Enforce minimum password complexity."""
        if not re.search(r"[A-Z]", value):
            raise ValidationError("Password must contain at least one uppercase letter.")
        if not re.search(r"[a-z]", value):
            raise ValidationError("Password must contain at least one lowercase letter.")
        if not re.search(r"\d", value):
            raise ValidationError("Password must contain at least one digit.")


# ─── Donation Schemas ──────────────────────────────────────────────────────────

class InitiateDonationSchema(Schema):
    donor_name = fields.Str(
        required=True,
        validate=validate.Length(min=2, max=150),
        error_messages={"required": "Donor name is required."}
    )
    phone_number = fields.Str(
        required=True,
        error_messages={"required": "Phone number is required."}
    )
    amount = fields.Float(
        required=True,
        error_messages={"required": "Amount is required."}
    )

    @validates("phone_number")
    def validate_phone(self, value: str):
        if not is_valid_kenyan_phone(value):
            raise ValidationError(
                "Invalid phone number. Use format: 07XXXXXXXX or +2547XXXXXXXX"
            )

    @validates("amount")
    def validate_amount(self, value: float):
        if value < 10:
            raise ValidationError("Minimum donation amount is KES 10.")
        if value > 999999:
            raise ValidationError("Maximum single donation amount is KES 999,999.")

    @post_load
    def normalize_phone(self, data: dict, **kwargs) -> dict:
        """Normalize phone to Daraja format after validation."""
        data["phone_number"] = normalize_phone_number(data["phone_number"])
        return data


# ─── Admin Schemas ─────────────────────────────────────────────────────────────

class DonationFilterSchema(Schema):
    page = fields.Int(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Int(load_default=20, validate=validate.Range(min=1, max=100))
    status = fields.Str(
        load_default=None,
        validate=validate.OneOf(["pending", "completed", "failed", "cancelled"])
    )
    search = fields.Str(load_default=None, validate=validate.Length(max=100))
    date_from = fields.Date(load_default=None)
    date_to = fields.Date(load_default=None)


# ─── Validation Helper ─────────────────────────────────────────────────────────

def validate_request(schema_class: type, data: dict) -> tuple[dict | None, dict | None]:
    """
    Validate request data against a schema.
    Returns (validated_data, errors).
    Usage:
        data, errors = validate_request(InitiateDonationSchema, request.get_json())
        if errors:
            return error_response(errors, "VALIDATION_ERROR", 400)
    """
    schema = schema_class()
    try:
        validated = schema.load(data or {})
        return validated, None
    except ValidationError as err:
        return None, err.messages
