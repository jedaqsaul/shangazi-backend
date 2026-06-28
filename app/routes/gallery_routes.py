"""
Gallery Routes
--------------
Public:
  GET    /api/gallery                  (no auth, optional ?category=)

Admin (requires JWT):
  GET    /api/admin/gallery
  POST   /api/admin/gallery            (multipart/form-data, image upload)
  PUT    /api/admin/gallery/<id>       (metadata only)
  DELETE /api/admin/gallery/<id>
"""

from flask import Blueprint
from app.controllers.gallery_controller import GalleryController
from app.middleware.auth_middleware import jwt_required_custom
from app.extensions import limiter

gallery_bp = Blueprint("gallery", __name__, url_prefix="/api/gallery")
admin_gallery_bp = Blueprint("admin_gallery", __name__, url_prefix="/api/admin/gallery")


@gallery_bp.get("")
@limiter.limit("60 per minute")
def list_public():
    return GalleryController.list_public()


@admin_gallery_bp.get("")
@jwt_required_custom
def list_admin():
    return GalleryController.list_admin()


@admin_gallery_bp.post("")
@jwt_required_custom
@limiter.limit("30 per hour")
def create():
    return GalleryController.create()


@admin_gallery_bp.put("/<string:image_id>")
@jwt_required_custom
def update(image_id: str):
    return GalleryController.update(image_id)


@admin_gallery_bp.delete("/<string:image_id>")
@jwt_required_custom
def delete(image_id: str):
    return GalleryController.delete(image_id)
