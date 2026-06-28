"""
Donation Routes
---------------
Public-facing donation endpoints.
POST /api/donations/initiate
GET  /api/donations/status/<checkout_request_id>
"""

from flask import Blueprint
from app.controllers.donation_controller import DonationController
from app.extensions import limiter

donation_bp = Blueprint("donations", __name__, url_prefix="/api/donations")


@donation_bp.post("/initiate")
@limiter.limit("5 per minute")
def initiate():
    return DonationController.initiate()


@donation_bp.get("/status/<string:checkout_request_id>")
@limiter.limit("30 per minute")
def status(checkout_request_id: str):
    return DonationController.status(checkout_request_id)
