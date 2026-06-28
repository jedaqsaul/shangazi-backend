"""
Program Controller
--------------------
Handles HTTP layer for program endpoints.
Public: list published programs (no auth).
Admin: create, update, delete (requires JWT).

Metrics arrive as a JSON-encoded string within the multipart form
(there's no clean native way to send a list of objects as plain
form fields), so we parse it here before handing off to the service.
"""

import json
from flask import request
from app.services.program_service import ProgramService
from app.middleware.auth_middleware import get_current_user_id
from app.utils.error_handlers import error_response, success_response
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _parse_bool(value, default=None):
    if value is None:
        return default
    return str(value).strip().lower() in ("true", "1", "yes")


def _parse_metrics(raw_value):
    """
    Parse the 'metrics' form field, which is expected to be a JSON
    string like '[{"label": "...", "value": "..."}]'.
    Returns None if not provided (caller decides default behavior),
    raises ValueError if provided but not valid JSON.
    """
    if raw_value is None or raw_value == "":
        return None
    try:
        parsed = json.loads(raw_value)
    except (TypeError, json.JSONDecodeError):
        raise ValueError("Metrics must be valid JSON, e.g. [{\"label\": \"...\", \"value\": \"...\"}].")
    return parsed


class ProgramController:

    @staticmethod
    def list_public():
        """GET /api/programs"""
        try:
            programs = ProgramService.list_public_programs()
            return success_response(data={"programs": programs})
        except Exception as e:
            logger.error("Failed to fetch public programs", extra={"extra": {"error": str(e)}})
            return error_response("Failed to retrieve programs.", "SERVER_ERROR", 500)

    @staticmethod
    def list_admin():
        """GET /api/admin/programs"""
        try:
            page = request.args.get("page", 1, type=int)
            per_page = min(request.args.get("per_page", 24, type=int), 100)
            result = ProgramService.list_admin_programs(page=page, per_page=per_page)
            return success_response(data=result)
        except Exception as e:
            logger.error("Failed to fetch admin programs", extra={"extra": {"error": str(e)}})
            return error_response("Failed to retrieve programs.", "SERVER_ERROR", 500)

    @staticmethod
    def create():
        """
        POST /api/admin/programs
        multipart/form-data: title, description, icon, color,
        metrics (JSON string, optional), photo (optional file),
        display_order (optional), is_published (optional, default true)
        """
        file_storage = request.files.get("photo")
        title = request.form.get("title", "")
        description = request.form.get("description", "")
        icon = request.form.get("icon", "Heart")
        color = request.form.get("color", "forest")
        display_order = request.form.get("display_order", 0, type=int)
        is_published = _parse_bool(request.form.get("is_published"), default=True)

        try:
            metrics = _parse_metrics(request.form.get("metrics"))

            program = ProgramService.create_program(
                title=title,
                description=description,
                icon=icon,
                color=color,
                metrics=metrics,
                file_storage=file_storage,
                display_order=display_order,
                is_published=is_published,
                admin_id=get_current_user_id(),
                ip_address=request.remote_addr,
            )
            return success_response(
                data=program.to_dict(),
                message="Program created successfully.",
                status_code=201,
            )

        except ValueError as e:
            return error_response(str(e), "VALIDATION_ERROR", 400)

        except RuntimeError as e:
            return error_response(str(e), "UPLOAD_ERROR", 502)

        except Exception as e:
            logger.error("Program creation failed", extra={"extra": {"error": str(e)}})
            return error_response("Failed to create program.", "SERVER_ERROR", 500)

    @staticmethod
    def update(program_id: str):
        """
        PUT /api/admin/programs/<program_id>
        multipart/form-data, all fields optional: title, description,
        icon, color, metrics (JSON string), photo (file),
        display_order, is_published
        """
        file_storage = request.files.get("photo")
        title = request.form.get("title")
        description = request.form.get("description")
        icon = request.form.get("icon")
        color = request.form.get("color")
        display_order = request.form.get("display_order", type=int)
        is_published = _parse_bool(request.form.get("is_published"), default=None)

        try:
            metrics = _parse_metrics(request.form.get("metrics"))

            program = ProgramService.update_program(
                program_id=program_id,
                admin_id=get_current_user_id(),
                ip_address=request.remote_addr,
                title=title,
                description=description,
                icon=icon,
                color=color,
                metrics=metrics,
                display_order=display_order,
                is_published=is_published,
                file_storage=file_storage,
            )
            return success_response(data=program.to_dict(), message="Program updated successfully.")

        except ValueError as e:
            not_found = "not found" in str(e).lower()
            return error_response(str(e), "NOT_FOUND" if not_found else "VALIDATION_ERROR", 404 if not_found else 400)

        except RuntimeError as e:
            return error_response(str(e), "UPLOAD_ERROR", 502)

        except Exception as e:
            logger.error("Program update failed", extra={"extra": {"error": str(e)}})
            return error_response("Failed to update program.", "SERVER_ERROR", 500)

    @staticmethod
    def delete(program_id: str):
        """DELETE /api/admin/programs/<program_id>"""
        try:
            ProgramService.delete_program(
                program_id=program_id,
                admin_id=get_current_user_id(),
                ip_address=request.remote_addr,
            )
            return success_response(message="Program deleted successfully.")

        except ValueError as e:
            return error_response(str(e), "NOT_FOUND", 404)

        except Exception as e:
            logger.error("Program deletion failed", extra={"extra": {"error": str(e)}})
            return error_response("Failed to delete program.", "SERVER_ERROR", 500)
