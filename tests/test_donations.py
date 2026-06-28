"""
Donation Tests
--------------
Tests for donation initiation, status polling, and admin queries.
Daraja calls are mocked — no real API calls in tests.
Run with: pytest tests/test_donations.py -v
"""

import pytest
from unittest.mock import patch, MagicMock
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.donation import Donation


@pytest.fixture
def app():
    app = create_app("development")
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "JWT_SECRET_KEY": "test-jwt-secret",
        "SECRET_KEY": "test-secret",
        "RATELIMIT_ENABLED": False,
        "DARAJA_CONSUMER_KEY": "test_key",
        "DARAJA_CONSUMER_SECRET": "test_secret",
        "DARAJA_SHORTCODE": "174379",
        "DARAJA_PASSKEY": "test_passkey",
        "DARAJA_CALLBACK_URL": "https://test.com/api/daraja/callback",
    })
    with app.app_context():
        db.create_all()
        _seed_data()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _seed_data():
    user = User(username="admin", email="admin@test.com", role="super_admin", is_active=True)
    user.set_password("Admin123!")
    db.session.add(user)

    donation = Donation(
        donor_name="Jane Doe",
        phone_number="254712345678",
        amount=500.00,
        checkout_request_id="ws_CO_test_123",
        merchant_request_id="mrq_test_123",
        payment_status="pending",
    )
    db.session.add(donation)
    db.session.commit()


def _get_token(client) -> str:
    resp = client.post("/api/auth/login", json={"email": "admin@test.com", "password": "Admin123!"})
    return resp.get_json()["data"]["access_token"]


MOCK_DARAJA_STK_RESPONSE = {
    "MerchantRequestID": "mrq_new_456",
    "CheckoutRequestID": "ws_CO_new_456",
    "ResponseCode": "0",
    "ResponseDescription": "Success. Request accepted for processing",
    "CustomerMessage": "Success. Request accepted for processing",
}

MOCK_DARAJA_TOKEN = "mock_access_token_abc"


class TestInitiateDonation:

    @patch("app.services.daraja_service.DarajaService.get_access_token", return_value=MOCK_DARAJA_TOKEN)
    @patch("app.services.daraja_service.requests.post")
    def test_initiate_success(self, mock_post, mock_token, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = MOCK_DARAJA_STK_RESPONSE
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        resp = client.post("/api/donations/initiate", json={
            "donor_name": "John Doe",
            "phone_number": "0712345678",
            "amount": 1000,
        })
        data = resp.get_json()
        assert resp.status_code == 201
        assert data["success"] is True
        assert "checkout_request_id" in data["data"]

    def test_initiate_invalid_phone(self, client):
        resp = client.post("/api/donations/initiate", json={
            "donor_name": "John Doe",
            "phone_number": "12345",
            "amount": 500,
        })
        assert resp.status_code == 400

    def test_initiate_amount_too_low(self, client):
        resp = client.post("/api/donations/initiate", json={
            "donor_name": "John Doe",
            "phone_number": "0712345678",
            "amount": 5,
        })
        assert resp.status_code == 400

    def test_initiate_missing_fields(self, client):
        resp = client.post("/api/donations/initiate", json={"donor_name": "John"})
        assert resp.status_code == 400


class TestDonationStatus:

    def test_status_pending(self, client):
        resp = client.get("/api/donations/status/ws_CO_test_123")
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["data"]["payment_status"] == "pending"

    def test_status_not_found(self, client):
        resp = client.get("/api/donations/status/nonexistent_id")
        assert resp.status_code == 404


class TestAdminDonations:

    def test_list_donations_authenticated(self, client):
        token = _get_token(client)
        resp = client.get("/api/admin/donations", headers={"Authorization": f"Bearer {token}"})
        data = resp.get_json()
        assert resp.status_code == 200
        assert "donations" in data["data"]

    def test_list_donations_unauthenticated(self, client):
        resp = client.get("/api/admin/donations")
        assert resp.status_code == 401

    def test_stats_returns_correct_keys(self, client):
        token = _get_token(client)
        resp = client.get("/api/admin/stats", headers={"Authorization": f"Bearer {token}"})
        data = resp.get_json()["data"]
        assert "total_donations" in data
        assert "completed_donations" in data
        assert "total_amount_collected" in data

    def test_filter_by_status(self, client):
        token = _get_token(client)
        resp = client.get("/api/admin/donations?status=pending", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        items = resp.get_json()["data"]["donations"]
        assert all(d["payment_status"] == "pending" for d in items)
