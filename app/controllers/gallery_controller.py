"""
Gallery Controller
------------------
Handles HTTP layer for gallery image endpoints.
Public: list published images (no auth).
Admin: create, update, delete (requires JWT).
"""

from flask import request
from app.services.gallery_service import GalleryService
from app.middleware.auth_middleware import get_current_user_id
from app.utils.error_handlers import error_response, success_response
from app.utils.logger import get_logger

logger = get_logger(__name__)


class GalleryController:

    @staticmethod
    def list_public():
        """
        GET /api/gallery
        Optional query param: category
        """
        try:
            category = request.args.get("category")
            images = GalleryService.list_public_images(category=category)
            return success_response(data={"images": images})
        except Exception as e:
            logger.error("Failed to fetch public gallery", extra={"extra": {"error": str(e)}})
            return error_response("Failed to retrieve gallery images.", "SERVER_ERROR", 500)

    @staticmethod
    def list_admin():
        """
        GET /api/admin/gallery
        Paginated listing for the admin dashboard.
        """
        try:
            page = request.args.get("page", 1, type=int)
            per_page = min(request.args.get("per_page", 24, type=int), 100)
            result = GalleryService.list_admin_images(page=page, per_page=per_page)
            return success_response(data=result)
        except Exception as e:
            logger.error("Failed to fetch admin gallery", extra={"extra": {"error": str(e)}})
            return error_response("Failed to retrieve gallery images.", "SERVER_ERROR", 500)

    @staticmethod
    def create():
        """
        POST /api/admin/gallery
        multipart/form-data: image (file), title (optional), category, display_order (optional)
        """
        file_storage = request.files.get("image")
        title = request.form.get("title") or None
        category = request.form.get("category", "general")
        display_order = request.form.get("display_order", 0, type=int)

        try:
            image = GalleryService.create_image(
                file_storage=file_storage,
                title=title,
                category=category,
                display_order=display_order,
                admin_id=get_current_user_id(),
                ip_address=request.remote_addr,
            )
            return success_response(
                data=image.to_dict(),
                message="Image uploaded successfully.",
                status_code=201,
            )

        except ValueError as e:
            return error_response(str(e), "VALIDATION_ERROR", 400)

        except RuntimeError as e:
            return error_response(str(e), "UPLOAD_ERROR", 502)

        except Exception as e:
            logger.error("Gallery image creation failed", extra={"extra": {"error": str(e)}})
            return error_response("Failed to create gallery image.", "SERVER_ERROR", 500)

    @staticmethod
    def update(image_id: str):
        """
        PUT /api/admin/gallery/<image_id>
        JSON body: title (optional), category (optional), display_order (optional)
        Metadata only — does not replace the image itself.
        """
        data = request.get_json(silent=True) or {}

        try:
            image = GalleryService.update_image(
                image_id=image_id,
                admin_id=get_current_user_id(),
                ip_address=request.remote_addr,
                title=data.get("title"),
                category=data.get("category"),
                display_order=data.get("display_order"),
            )
            return success_response(data=image.to_dict(), message="Image updated successfully.")

        except ValueError as e:
            return error_response(str(e), "NOT_FOUND" if "not found" in str(e).lower() else "VALIDATION_ERROR", 404 if "not found" in str(e).lower() else 400)

        except Exception as e:
            logger.error("Gallery image update failed", extra={"extra": {"error": str(e)}})
            return error_response("Failed to update gallery image.", "SERVER_ERROR", 500)

    @staticmethod
    def delete(image_id: str):
        """
        DELETE /api/admin/gallery/<image_id>
        Removes both the Cloudinary asset and the DB record.
        """
        try:
            GalleryService.delete_image(
                image_id=image_id,
                admin_id=get_current_user_id(),
                ip_address=request.remote_addr,
            )
            return success_response(message="Image deleted successfully.")

        except ValueError as e:
            return error_response(str(e), "NOT_FOUND", 404)

        except Exception as e:
            logger.error("Gallery image deletion failed", extra={"extra": {"error": str(e)}})
            return error_response("Failed to delete gallery image.", "SERVER_ERROR", 500)
