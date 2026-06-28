"""
Auth Service
------------
All authentication business logic lives here.
Controllers call these functions — they never touch the DB directly.
"""

from datetime import datetime, timezone
from flask_jwt_extended import create_access_token, create_refresh_token
from app.extensions import db
from app.models.user import User
from app.models.audit_log import AuditLog
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AuthService:

    @staticmethod
    def login(email: str, password: str, ip_address: str, user_agent: str) -> dict:
        """
        Authenticate an admin user.
        Returns access + refresh tokens on success.
        Raises ValueError on invalid credentials or inactive account.
        """
        user = User.query.filter_by(email=email.lower().strip()).first()

        if not user or not user.check_password(password):
            # Log failed attempt — do NOT reveal whether email exists
            logger.warning(
                "Failed login attempt",
                extra={"extra": {"email": email, "ip": ip_address}}
            )
            AuditLog.log(
                action="LOGIN_FAILED",
                ip_address=ip_address,
                user_agent=user_agent,
                details={"email": email}
            )
            db.session.commit()
            raise ValueError("Invalid email or password.")

        if not user.is_active:
            logger.warning(
                "Login attempt on inactive account",
                extra={"extra": {"user_id": user.id, "ip": ip_address}}
            )
            raise ValueError("This account has been deactivated. Contact your administrator.")

        # Generate tokens with role embedded in claims
        additional_claims = {"role": user.role, "username": user.username}
        access_token = create_access_token(
            identity=user.id,
            additional_claims=additional_claims
        )
        refresh_token = create_refresh_token(
            identity=user.id,
            additional_claims=additional_claims
        )

        # Update last login timestamp
        user.update_last_login()

        AuditLog.log(
            action="LOGIN_SUCCESS",
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"username": user.username, "role": user.role}
        )
        db.session.commit()

        logger.info(
            "Admin login successful",
            extra={"extra": {"user_id": user.id, "ip": ip_address}}
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": user.to_dict(),
        }

    @staticmethod
    def refresh_token(user_id: str) -> dict:
        """
        Issue a new access token using a valid refresh token.
        The refresh token is verified by the route decorator.
        """
        user = User.query.get(user_id)
        if not user or not user.is_active:
            raise ValueError("User not found or inactive.")

        additional_claims = {"role": user.role, "username": user.username}
        access_token = create_access_token(
            identity=user.id,
            additional_claims=additional_claims
        )

        logger.info(
            "Access token refreshed",
            extra={"extra": {"user_id": user_id}}
        )

        return {"access_token": access_token}

    @staticmethod
    def create_user(
        username: str,
        email: str,
        password: str,
        role: str,
        created_by_id: str,
        ip_address: str,
    ) -> User:
        """
        Create a new admin user. Only callable by super_admin.
        Raises ValueError if email/username already exists.
        """
        if User.query.filter_by(email=email.lower()).first():
            raise ValueError(f"A user with email '{email}' already exists.")

        if User.query.filter_by(username=username).first():
            raise ValueError(f"Username '{username}' is already taken.")

        user = User(
            username=username,
            email=email.lower().strip(),
            role=role,
        )
        user.set_password(password)

        db.session.add(user)

        AuditLog.log(
            action="USER_CREATED",
            user_id=created_by_id,
            resource="users",
            ip_address=ip_address,
            details={"new_user_email": email, "role": role}
        )
        db.session.commit()

        logger.info(
            "New admin user created",
            extra={"extra": {"new_user_id": user.id, "created_by": created_by_id}}
        )

        return user

    @staticmethod
    def seed_super_admin(username: str, email: str, password: str) -> User | None:
        """
        Create the initial super admin if none exists.
        Called by the Flask CLI seed command — not an API endpoint.
        """
        if User.query.filter_by(role="super_admin").first():
            logger.info("Super admin already exists. Skipping seed.")
            return None

        user = User(username=username, email=email.lower(), role="super_admin")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        logger.info(
            "Super admin seeded",
            extra={"extra": {"user_id": user.id}}
        )
        return user

    @staticmethod
    def get_profile(user_id: str) -> User:
        """Fetch the logged-in admin's own profile. Raises ValueError if not found."""
        user = User.query.get(user_id)
        if not user:
            raise ValueError("User not found.")
        return user

    @staticmethod
    def change_password(
        user_id: str,
        current_password: str,
        new_password: str,
        ip_address: str,
    ) -> None:
        """
        Change the logged-in admin's own password.
        Raises ValueError if the current password is wrong or the new
        password doesn't meet minimum requirements.
        """
        user = User.query.get(user_id)
        if not user:
            raise ValueError("User not found.")

        if not user.check_password(current_password):
            AuditLog.log(
                action="PASSWORD_CHANGE_FAILED",
                user_id=user.id,
                ip_address=ip_address,
                details={"reason": "incorrect_current_password"}
            )
            db.session.commit()
            raise ValueError("Current password is incorrect.")

        if len(new_password) < 8:
            raise ValueError("New password must be at least 8 characters long.")

        if current_password == new_password:
            raise ValueError("New password must be different from the current password.")

        user.set_password(new_password)

        AuditLog.log(
            action="PASSWORD_CHANGED",
            user_id=user.id,
            ip_address=ip_address,
        )
        db.session.commit()

        logger.info(
            "Admin changed their own password",
            extra={"extra": {"user_id": user.id}}
        )

    @staticmethod
    def update_avatar(user_id: str, file_storage, ip_address: str) -> User:
        """
        Upload and set a new profile photo for the logged-in admin.
        Replaces (and cleans up) any previous avatar on Cloudinary.
        Raises ValueError for invalid input, RuntimeError if the upload itself fails.
        """
        from app.services.cloudinary_service import CloudinaryService

        user = User.query.get(user_id)
        if not user:
            raise ValueError("User not found.")

        CloudinaryService.validate_image(file_storage)
        upload_result = CloudinaryService.upload_image(file_storage, folder="avatars")

        old_public_id = user.avatar_public_id
        user.avatar_url = upload_result["url"]
        user.avatar_public_id = upload_result["public_id"]

        if old_public_id:
            CloudinaryService.delete_image(old_public_id)

        AuditLog.log(
            action="AVATAR_UPDATED",
            user_id=user.id,
            ip_address=ip_address,
        )
        db.session.commit()

        logger.info(
            "Admin updated their profile photo",
            extra={"extra": {"user_id": user.id}}
        )

        return user
