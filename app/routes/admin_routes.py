"""
Admin Routes
------------
All routes require valid JWT.
Audit log route requires super_admin role.
GET  /api/admin/donations
GET  /api/admin/donations/<id>
GET  /api/admin/stats
GET  /api/admin/export
GET  /api/admin/audit-logs
POST /api/admin/users
"""

from flask import Blueprint
from app.controllers.admin_controller import AdminController
from app.controllers.auth_controller import AuthController
from app.middleware.auth_middleware import jwt_required_custom, require_role
from app.extensions import limiter

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@admin_bp.get("/donations")
@jwt_required_custom
def get_donations():
    return AdminController.get_donations()


@admin_bp.get("/donations/<string:donation_id>")
@jwt_required_custom
def get_donation(donation_id: str):
    return AdminController.get_donation(donation_id)


@admin_bp.get("/stats")
@jwt_required_custom
def get_stats():
    return AdminController.get_stats()


@admin_bp.get("/export")
@jwt_required_custom
@limiter.limit("10 per hour")
def export_report():
    return AdminController.export_report()


@admin_bp.get("/audit-logs")
@jwt_required_custom
@require_role("super_admin")
def get_audit_logs():
    return AdminController.get_audit_logs()


@admin_bp.post("/users")
@jwt_required_custom
@require_role("super_admin")
def create_user():
    return AuthController.create_user()
