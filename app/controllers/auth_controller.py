"""
Auth Controller
---------------
Handles HTTP request parsing and response formatting for auth endpoints.
Delegates all business logic to AuthService.
"""

from flask import request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from app.services.auth_service import AuthService
from app.middleware.validators import validate_request, LoginSchema, CreateUserSchema
from app.utils.error_handlers import error_response, success_response
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AuthController:

    @staticmethod
    def login():
        """
        POST /api/auth/login
        Authenticates admin and returns JWT tokens.
        """
        data, errors = validate_request(LoginSchema, request.get_json())
        if errors:
            return error_response(str(errors), "VALIDATION_ERROR", 400)

        try:
            result = AuthService.login(
                email=data["email"],
                password=data["password"],
                ip_address=request.remote_addr,
                user_agent=request.headers.get("User-Agent", ""),
            )
            return success_response(data=result, message="Login successful.")

        except ValueError as e:
            return error_response(str(e), "AUTH_ERROR", 401)

        except Exception as e:
            logger.error("Unexpected login error", extra={"extra": {"error": str(e)}})
            return error_response("An unexpected error occurred.", "SERVER_ERROR", 500)

    @staticmethod
    def logout():
        """
        POST /api/auth/logout
        Client-side logout — instructs frontend to discard tokens.
        For full server-side revocation a token blocklist would be needed
        (future enhancement using Redis).
        """
        return success_response(message="Logged out successfully.")

    @staticmethod
    def refresh():
        """
        POST /api/auth/refresh
        Issues a new access token using a valid refresh token.
        """
        try:
            verify_jwt_in_request(refresh=True)
            user_id = get_jwt_identity()
            result = AuthService.refresh_token(user_id)
            return success_response(data=result, message="Token refreshed.")

        except ValueError as e:
            return error_response(str(e), "AUTH_ERROR", 401)

        except Exception as e:
            return error_response("Token refresh failed.", "AUTH_ERROR", 401)

    @staticmethod
    def create_user():
        """
        POST /api/admin/users
        Creates a new admin user. Super admin only.
        """
        from flask_jwt_extended import get_jwt_identity
        data, errors = validate_request(CreateUserSchema, request.get_json())
        if errors:
            return error_response(str(errors), "VALIDATION_ERROR", 400)

        try:
            user = AuthService.create_user(
                username=data["username"],
                email=data["email"],
                password=data["password"],
                role=data["role"],
                created_by_id=get_jwt_identity(),
                ip_address=request.remote_addr,
            )
            return success_response(
                data=user.to_dict(),
                message="Admin user created successfully.",
                status_code=201,
            )

        except ValueError as e:
            return error_response(str(e), "CONFLICT", 409)

        except Exception as e:
            logger.error("User creation failed", extra={"extra": {"error": str(e)}})
            return error_response("Failed to create user.", "SERVER_ERROR", 500)

    @staticmethod
    def get_profile():
        """
        GET /api/auth/profile
        Returns the logged-in admin's own profile.
        """
        from app.middleware.auth_middleware import get_current_user_id

        try:
            user = AuthService.get_profile(get_current_user_id())
            return success_response(data=user.to_dict())

        except ValueError as e:
            return error_response(str(e), "NOT_FOUND", 404)

        except Exception as e:
            logger.error("Failed to fetch profile", extra={"extra": {"error": str(e)}})
            return error_response("Failed to retrieve profile.", "SERVER_ERROR", 500)

    @staticmethod
    def change_password():
        """
        POST /api/auth/change-password
        JSON body: current_password, new_password
        """
        from app.middleware.auth_middleware import get_current_user_id

        data = request.get_json(silent=True) or {}
        current_password = data.get("current_password", "")
        new_password = data.get("new_password", "")

        if not current_password or not new_password:
            return error_response("Current and new password are both required.", "VALIDATION_ERROR", 400)

        try:
            AuthService.change_password(
                user_id=get_current_user_id(),
                current_password=current_password,
                new_password=new_password,
                ip_address=request.remote_addr,
            )
            return success_response(message="Password changed successfully.")

        except ValueError as e:
            return error_response(str(e), "VALIDATION_ERROR", 400)

        except Exception as e:
            logger.error("Password change failed", extra={"extra": {"error": str(e)}})
            return error_response("Failed to change password.", "SERVER_ERROR", 500)

    @staticmethod
    def update_avatar():
        """
        POST /api/auth/avatar
        multipart/form-data: photo (file)
        """
        from app.middleware.auth_middleware import get_current_user_id

        file_storage = request.files.get("photo")
        if not file_storage or not file_storage.filename:
            return error_response("No photo was provided.", "VALIDATION_ERROR", 400)

        try:
            user = AuthService.update_avatar(
                user_id=get_current_user_id(),
                file_storage=file_storage,
                ip_address=request.remote_addr,
            )
            return success_response(data=user.to_dict(), message="Profile photo updated successfully.")

        except ValueError as e:
            return error_response(str(e), "VALIDATION_ERROR", 400)

        except RuntimeError as e:
            return error_response(str(e), "UPLOAD_ERROR", 502)

        except Exception as e:
            logger.error("Avatar update failed", extra={"extra": {"error": str(e)}})
            return error_response("Failed to update profile photo.", "SERVER_ERROR", 500)
