"""
User Model
----------
Represents administrative users who can access the dashboard.
Two roles: super_admin (full access) and admin (read + export).
Passwords are always stored hashed — never plain text.
"""

import uuid
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(
        db.Enum("super_admin", "admin", name="user_roles"),
        nullable=False,
        default="admin"
    )
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    last_login = db.Column(db.DateTime(timezone=True), nullable=True)

    # Profile photo (optional, uploaded via the admin profile page)
    avatar_url = db.Column(db.String(500), nullable=True)
    avatar_public_id = db.Column(db.String(255), nullable=True)

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    audit_logs = db.relationship("AuditLog", back_populates="user", lazy="dynamic")

    def set_password(self, password: str) -> None:
        """Hash and store password. Never call with plain text storage."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify a plain text password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    def update_last_login(self) -> None:
        """Record the timestamp of the most recent successful login."""
        self.last_login = datetime.now(timezone.utc)

    def is_super_admin(self) -> bool:
        return self.role == "super_admin"

    def to_dict(self) -> dict:
        """Safe serialization — password hash is never included."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "avatar_url": self.avatar_url,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat(),
        }

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.role})>"
