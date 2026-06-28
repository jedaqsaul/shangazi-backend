"""
Program Routes
----------------
Public:
  GET    /api/programs

Admin (requires JWT):
  GET    /api/admin/programs
  POST   /api/admin/programs            (multipart/form-data, photo optional)
  PUT    /api/admin/programs/<id>       (multipart/form-data, all fields optional)
  DELETE /api/admin/programs/<id>
"""

from flask import Blueprint
from app.controllers.program_controller import ProgramController
from app.middleware.auth_middleware import jwt_required_custom
from app.extensions import limiter

program_bp = Blueprint("programs", __name__, url_prefix="/api/programs")
admin_program_bp = Blueprint("admin_programs", __name__, url_prefix="/api/admin/programs")


@program_bp.get("")
@limiter.limit("60 per minute")
def list_public():
    return ProgramController.list_public()


@admin_program_bp.get("")
@jwt_required_custom
def list_admin():
    return ProgramController.list_admin()


@admin_program_bp.post("")
@jwt_required_custom
@limiter.limit("30 per hour")
def create():
    return ProgramController.create()


@admin_program_bp.put("/<string:program_id>")
@jwt_required_custom
def update(program_id: str):
    return ProgramController.update(program_id)


@admin_program_bp.delete("/<string:program_id>")
@jwt_required_custom
def delete(program_id: str):
    return ProgramController.delete(program_id)
