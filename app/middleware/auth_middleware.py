"""
Auth Middleware
---------------
Decorators for protecting routes with JWT and role-based access.

Usage:
    @jwt_required_custom
    def protected_route():
        ...

    @require_role("super_admin")
    def super_admin_only():
        ...
"""

from functools import wraps
from flask import request
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt
from app.utils.error_handlers import error_response
from app.utils.logger import get_logger

logger = get_logger(__name__)


def jwt_required_custom(fn):
    """
    Verifies a valid JWT access token is present in the Authorization header.
    Returns 401 if missing or invalid.
    Returns 403 if the user account is inactive.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()

            # Check if the token has been explicitly revoked (via claims)
            claims = get_jwt()
            if claims.get("revoked", False):
                return error_response("Token has been revoked.", "TOKEN_REVOKED", 401)

            return fn(*args, **kwargs)

        except Exception as e:
            logger.warning(
                "JWT verification failed",
                extra={"extra": {"error": str(e), "ip": request.remote_addr}}
            )
            return error_response("Authentication required.", "UNAUTHORIZED", 401)

    return wrapper


def require_role(*roles: str):
    """
    Restricts endpoint access to specific roles.
    Must be used AFTER @jwt_required_custom.

    Usage:
        @jwt_required_custom
        @require_role("super_admin")
        def admin_only_view():
            ...
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                verify_jwt_in_request()
                claims = get_jwt()
                user_role = claims.get("role")

                if user_role not in roles:
                    logger.warning(
                        "Unauthorized role access attempt",
                        extra={"extra": {
                            "required_roles": roles,
                            "user_role": user_role,
                            "ip": request.remote_addr,
                        }}
                    )
                    return error_response(
                        "You do not have permission to perform this action.",
                        "FORBIDDEN",
                        403
                    )

                return fn(*args, **kwargs)

            except Exception as e:
                return error_response("Authentication required.", "UNAUTHORIZED", 401)

        return wrapper
    return decorator


def get_current_user_id() -> str | None:
    """Helper to safely extract the current user's ID from JWT identity."""
    try:
        return get_jwt_identity()
    except Exception:
        return None
