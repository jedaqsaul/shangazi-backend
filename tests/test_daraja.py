"""
Daraja Callback Tests
---------------------
Tests for callback security, payload parsing, and donation updates.
Run with: pytest tests/test_daraja.py -v
"""

import pytest
from app import create_app
from app.extensions import db
from app.models.donation import Donation
from app.services.daraja_service import DarajaService


@pytest.fixture
def app():
    app = create_app("development")
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "JWT_SECRET_KEY": "test-jwt",
        "SECRET_KEY": "test-secret",
        "RATELIMIT_ENABLED": False,
        "FLASK_ENV": "development",  # Skip IP whitelist in dev
    })
    with app.app_context():
        db.create_all()
        _seed_pending_donation()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _seed_pending_donation():
    donation = Donation(
        donor_name="Callback Test User",
        phone_number="254799000001",
        amount=250.00,
        checkout_request_id="ws_CO_callback_test",
        merchant_request_id="mrq_callback_test",
        payment_status="pending",
    )
    db.session.add(donation)
    db.session.commit()


SUCCESSFUL_CALLBACK = {
    "Body": {
        "stkCallback": {
            "MerchantRequestID": "mrq_callback_test",
            "CheckoutRequestID": "ws_CO_callback_test",
            "ResultCode": 0,
            "ResultDesc": "The service request is processed successfully.",
            "CallbackMetadata": {
                "Item": [
                    {"Name": "Amount", "Value": 250},
                    {"Name": "MpesaReceiptNumber", "Value": "RCT12345ABC"},
                    {"Name": "TransactionDate", "Value": 20241120143500},
                    {"Name": "PhoneNumber", "Value": 254799000001},
                ]
            }
        }
    }
}

FAILED_CALLBACK = {
    "Body": {
        "stkCallback": {
            "MerchantRequestID": "mrq_callback_test",
            "CheckoutRequestID": "ws_CO_callback_test",
            "ResultCode": 1032,
            "ResultDesc": "Request cancelled by user.",
        }
    }
}


class TestCallbackParsing:

    def test_parse_successful_callback(self, app):
        with app.app_context():
            parsed = DarajaService.parse_callback(SUCCESSFUL_CALLBACK)
            assert parsed["result_code"] == 0
            assert parsed["mpesa_receipt_number"] == "RCT12345ABC"
            assert parsed["amount"] == 250
            assert parsed["checkout_request_id"] == "ws_CO_callback_test"

    def test_parse_failed_callback(self, app):
        with app.app_context():
            parsed = DarajaService.parse_callback(FAILED_CALLBACK)
            assert parsed["result_code"] == 1032
            assert parsed["mpesa_receipt_number"] is None

    def test_parse_invalid_payload_raises(self, app):
        with app.app_context():
            with pytest.raises(ValueError):
                DarajaService.parse_callback({"invalid": "structure"})


class TestCallbackEndpoint:

    def test_successful_callback_updates_donation(self, client, app):
        resp = client.post("/api/daraja/callback", json=SUCCESSFUL_CALLBACK)
        assert resp.status_code == 200
        assert resp.get_json()["ResultCode"] == 0

        with app.app_context():
            donation = Donation.query.filter_by(checkout_request_id="ws_CO_callback_test").first()
            assert donation.payment_status == "completed"
            assert donation.mpesa_receipt_number == "RCT12345ABC"

    def test_empty_payload_returns_200(self, client):
        # Daraja must always get 200 — never cause retry loops
        resp = client.post("/api/daraja/callback", json={})
        assert resp.status_code == 200

    def test_malformed_payload_returns_200(self, client):
        resp = client.post("/api/daraja/callback", json={"garbage": True})
        assert resp.status_code == 200
