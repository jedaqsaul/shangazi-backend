"""
Impact Story Routes
---------------------
Public:
  GET    /api/impact-stories

Admin (requires JWT):
  GET    /api/admin/impact-stories
  POST   /api/admin/impact-stories            (multipart/form-data, photo optional)
  PUT    /api/admin/impact-stories/<id>       (multipart/form-data, all fields optional)
  DELETE /api/admin/impact-stories/<id>
"""

from flask import Blueprint
from app.controllers.impact_story_controller import ImpactStoryController
from app.middleware.auth_middleware import jwt_required_custom
from app.extensions import limiter

impact_story_bp = Blueprint("impact_stories", __name__, url_prefix="/api/impact-stories")
admin_impact_story_bp = Blueprint("admin_impact_stories", __name__, url_prefix="/api/admin/impact-stories")


@impact_story_bp.get("")
@limiter.limit("60 per minute")
def list_public():
    return ImpactStoryController.list_public()


@admin_impact_story_bp.get("")
@jwt_required_custom
def list_admin():
    return ImpactStoryController.list_admin()


@admin_impact_story_bp.post("")
@jwt_required_custom
@limiter.limit("30 per hour")
def create():
    return ImpactStoryController.create()


@admin_impact_story_bp.put("/<string:story_id>")
@jwt_required_custom
def update(story_id: str):
    return ImpactStoryController.update(story_id)


@admin_impact_story_bp.delete("/<string:story_id>")
@jwt_required_custom
def delete(story_id: str):
    return ImpactStoryController.delete(story_id)
