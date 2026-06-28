"""
Error Handlers
--------------
Centralized error response formatting.
All API errors return a consistent JSON structure:
{
    "success": false,
    "error": {
        "code": "ERROR_CODE",
        "message": "Human-readable message"
    }
}
"""

from flask import jsonify
from app.utils.logger import get_logger

logger = get_logger(__name__)


def error_response(message: str, code: str, status_code: int) -> tuple:
    """Build a standardized error JSON response."""
    return jsonify({
        "success": False,
        "error": {
            "code": code,
            "message": message,
        }
    }), status_code


def success_response(data: dict | list | None = None, message: str = "Success", status_code: int = 200) -> tuple:
    """Build a standardized success JSON response."""
    response = {
        "success": True,
        "message": message,
    }
    if data is not None:
        response["data"] = data
    return jsonify(response), status_code


def register_error_handlers(app):
    """
    Register global Flask error handlers.
    Called once during app factory initialization.
    """

    @app.errorhandler(400)
    def bad_request(e):
        return error_response("Bad request.", "BAD_REQUEST", 400)

    @app.errorhandler(401)
    def unauthorized(e):
        return error_response("Authentication required.", "UNAUTHORIZED", 401)

    @app.errorhandler(403)
    def forbidden(e):
        return error_response("You do not have permission to access this resource.", "FORBIDDEN", 403)

    @app.errorhandler(404)
    def not_found(e):
        return error_response("The requested resource was not found.", "NOT_FOUND", 404)

    @app.errorhandler(405)
    def method_not_allowed(e):
        return error_response("Method not allowed.", "METHOD_NOT_ALLOWED", 405)

    @app.errorhandler(429)
    def too_many_requests(e):
        return error_response("Too many requests. Please slow down.", "RATE_LIMIT_EXCEEDED", 429)

    @app.errorhandler(500)
    def internal_server_error(e):
        logger.error("Internal server error", extra={"extra": {"error": str(e)}})
        return error_response("An internal server error occurred.", "INTERNAL_SERVER_ERROR", 500)
