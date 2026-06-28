"""
Auth Routes
-----------
Route registration only. No logic here.
POST /api/auth/login
POST /api/auth/logout
POST /api/auth/refresh
GET  /api/auth/profile
POST /api/auth/change-password
POST /api/auth/avatar
"""

from flask import Blueprint
from app.controllers.auth_controller import AuthController
from app.middleware.auth_middleware import jwt_required_custom
from app.extensions import limiter

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/login")
@limiter.limit("10 per minute")
def login():
    return AuthController.login()


@auth_bp.post("/logout")
@jwt_required_custom
def logout():
    return AuthController.logout()


@auth_bp.post("/refresh")
@limiter.limit("20 per minute")
def refresh():
    return AuthController.refresh()


@auth_bp.get("/profile")
@jwt_required_custom
def get_profile():
    return AuthController.get_profile()


@auth_bp.post("/change-password")
@jwt_required_custom
@limiter.limit("10 per hour")
def change_password():
    return AuthController.change_password()


@auth_bp.post("/avatar")
@jwt_required_custom
@limiter.limit("20 per hour")
def update_avatar():
    return AuthController.update_avatar()
