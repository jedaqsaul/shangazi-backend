"""
Auth Tests
----------
Tests for login, logout, token refresh, and user creation.
Run with: pytest tests/test_auth.py -v
"""

import pytest
from app import create_app
from app.extensions import db
from app.models.user import User


@pytest.fixture
def app():
    app = create_app("development")
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "JWT_SECRET_KEY": "test-jwt-secret",
        "SECRET_KEY": "test-secret",
        "RATELIMIT_ENABLED": False,
    })
    with app.app_context():
        db.create_all()
        _seed_test_user()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _seed_test_user():
    user = User(username="testadmin", email="admin@test.com", role="super_admin", is_active=True)
    user.set_password("TestPassword123!")
    db.session.add(user)
    db.session.commit()


def _get_access_token(client) -> str:
    resp = client.post("/api/auth/login", json={"email": "admin@test.com", "password": "TestPassword123!"})
    return resp.get_json()["data"]["access_token"]


class TestLogin:

    def test_login_success(self, client):
        resp = client.post("/api/auth/login", json={"email": "admin@test.com", "password": "TestPassword123!"})
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["success"] is True
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]

    def test_login_wrong_password(self, client):
        resp = client.post("/api/auth/login", json={"email": "admin@test.com", "password": "Wrong!"})
        assert resp.status_code == 401

    def test_login_unknown_email(self, client):
        resp = client.post("/api/auth/login", json={"email": "nobody@test.com", "password": "Password123!"})
        assert resp.status_code == 401

    def test_login_missing_fields(self, client):
        resp = client.post("/api/auth/login", json={"email": "admin@test.com"})
        assert resp.status_code == 400

    def test_login_inactive_user(self, client, app):
        with app.app_context():
            user = User.query.filter_by(email="admin@test.com").first()
            user.is_active = False
            db.session.commit()
        resp = client.post("/api/auth/login", json={"email": "admin@test.com", "password": "TestPassword123!"})
        assert resp.status_code == 401


class TestTokens:

    def test_protected_route_with_valid_token(self, client):
        token = _get_access_token(client)
        resp = client.get("/api/admin/stats", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_protected_route_without_token(self, client):
        resp = client.get("/api/admin/stats")
        assert resp.status_code == 401

    def test_protected_route_with_invalid_token(self, client):
        resp = client.get("/api/admin/stats", headers={"Authorization": "Bearer invalid-token"})
        assert resp.status_code == 401


class TestCreateUser:

    def test_create_user_as_super_admin(self, client):
        token = _get_access_token(client)
        resp = client.post("/api/admin/users", json={
            "username": "newadmin", "email": "newadmin@test.com",
            "password": "NewAdmin123!", "role": "admin",
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 201

    def test_create_user_duplicate_email(self, client):
        token = _get_access_token(client)
        payload = {"username": "a1", "email": "dup@test.com", "password": "Admin123!A", "role": "admin"}
        client.post("/api/admin/users", json=payload, headers={"Authorization": f"Bearer {token}"})
        payload["username"] = "a2"
        resp = client.post("/api/admin/users", json=payload, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 409

    def test_create_user_weak_password(self, client):
        token = _get_access_token(client)
        resp = client.post("/api/admin/users", json={
            "username": "weak", "email": "weak@test.com", "password": "weak", "role": "admin",
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 400
