"""
Impact Story Controller
-------------------------
Handles HTTP layer for impact story endpoints.
Public: list published stories (no auth).
Admin: create, update, delete (requires JWT).
"""

from flask import request
from app.services.impact_story_service import ImpactStoryService
from app.middleware.auth_middleware import get_current_user_id
from app.utils.error_handlers import error_response, success_response
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _parse_bool(value, default=None):
    if value is None:
        return default
    return str(value).strip().lower() in ("true", "1", "yes")


class ImpactStoryController:

    @staticmethod
    def list_public():
        """GET /api/impact-stories"""
        try:
            stories = ImpactStoryService.list_public_stories()
            return success_response(data={"stories": stories})
        except Exception as e:
            logger.error("Failed to fetch public impact stories", extra={"extra": {"error": str(e)}})
            return error_response("Failed to retrieve impact stories.", "SERVER_ERROR", 500)

    @staticmethod
    def list_admin():
        """GET /api/admin/impact-stories"""
        try:
            page = request.args.get("page", 1, type=int)
            per_page = min(request.args.get("per_page", 24, type=int), 100)
            result = ImpactStoryService.list_admin_stories(page=page, per_page=per_page)
            return success_response(data=result)
        except Exception as e:
            logger.error("Failed to fetch admin impact stories", extra={"extra": {"error": str(e)}})
            return error_response("Failed to retrieve impact stories.", "SERVER_ERROR", 500)

    @staticmethod
    def create():
        """
        POST /api/admin/impact-stories
        multipart/form-data: name, quote, role (optional), photo (optional file),
        display_order (optional), is_published (optional, default true)
        """
        file_storage = request.files.get("photo")
        name = request.form.get("name", "")
        quote = request.form.get("quote", "")
        role = request.form.get("role") or None
        display_order = request.form.get("display_order", 0, type=int)
        is_published = _parse_bool(request.form.get("is_published"), default=True)

        try:
            story = ImpactStoryService.create_story(
                name=name,
                quote=quote,
                role=role,
                file_storage=file_storage,
                display_order=display_order,
                is_published=is_published,
                admin_id=get_current_user_id(),
                ip_address=request.remote_addr,
            )
            return success_response(
                data=story.to_dict(),
                message="Impact story created successfully.",
                status_code=201,
            )

        except ValueError as e:
            return error_response(str(e), "VALIDATION_ERROR", 400)

        except RuntimeError as e:
            return error_response(str(e), "UPLOAD_ERROR", 502)

        except Exception as e:
            logger.error("Impact story creation failed", extra={"extra": {"error": str(e)}})
            return error_response("Failed to create impact story.", "SERVER_ERROR", 500)

    @staticmethod
    def update(story_id: str):
        """
        PUT /api/admin/impact-stories/<story_id>
        multipart/form-data, all fields optional: name, quote, role,
        photo (file), display_order, is_published
        """
        file_storage = request.files.get("photo")
        name = request.form.get("name")
        quote = request.form.get("quote")
        role = request.form.get("role")
        display_order = request.form.get("display_order", type=int)
        is_published = _parse_bool(request.form.get("is_published"), default=None)

        try:
            story = ImpactStoryService.update_story(
                story_id=story_id,
                admin_id=get_current_user_id(),
                ip_address=request.remote_addr,
                name=name,
                role=role,
                quote=quote,
                display_order=display_order,
                is_published=is_published,
                file_storage=file_storage,
            )
            return success_response(data=story.to_dict(), message="Impact story updated successfully.")

        except ValueError as e:
            not_found = "not found" in str(e).lower()
            return error_response(str(e), "NOT_FOUND" if not_found else "VALIDATION_ERROR", 404 if not_found else 400)

        except RuntimeError as e:
            return error_response(str(e), "UPLOAD_ERROR", 502)

        except Exception as e:
            logger.error("Impact story update failed", extra={"extra": {"error": str(e)}})
            return error_response("Failed to update impact story.", "SERVER_ERROR", 500)

    @staticmethod
    def delete(story_id: str):
        """DELETE /api/admin/impact-stories/<story_id>"""
        try:
            ImpactStoryService.delete_story(
                story_id=story_id,
                admin_id=get_current_user_id(),
                ip_address=request.remote_addr,
            )
            return success_response(message="Impact story deleted successfully.")

        except ValueError as e:
            return error_response(str(e), "NOT_FOUND", 404)

        except Exception as e:
            logger.error("Impact story deletion failed", extra={"extra": {"error": str(e)}})
            return error_response("Failed to delete impact story.", "SERVER_ERROR", 500)
