"""
Audit Log Model
---------------
Immutable record of significant admin actions.
Provides a tamper-evident trail for:
  - Authentication events (login, logout, failed attempts)
  - Data access (viewing donor records, exporting reports)
  - Administrative actions (creating users, changing roles)

Records are INSERT-only. Never updated or deleted.
"""

import uuid
from datetime import datetime, timezone
from app.extensions import db


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # Who performed the action (nullable for unauthenticated events)
    user_id = db.Column(
        db.String(36),
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # What happened
    action = db.Column(db.String(100), nullable=False, index=True)
    resource = db.Column(db.String(100), nullable=True)

    # Where from
    ip_address = db.Column(db.String(45), nullable=True)   # IPv6 max = 45 chars
    user_agent = db.Column(db.String(255), nullable=True)

    # Additional structured context (JSON)
    details = db.Column(db.JSON, nullable=True)

    # When
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    # Relationship
    user = db.relationship("User", back_populates="audit_logs")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action,
            "resource": self.resource,
            "ip_address": self.ip_address,
            "details": self.details,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def log(
        cls,
        action: str,
        user_id: str | None = None,
        resource: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        details: dict | None = None,
    ) -> "AuditLog":
        """
        Factory method for creating audit log entries.
        Usage:
            AuditLog.log(
                action="ADMIN_LOGIN",
                user_id=user.id,
                ip_address=request.remote_addr,
                details={"username": user.username}
            )
        """
        entry = cls(
            action=action,
            user_id=user_id,
            resource=resource,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
        )
        db.session.add(entry)
        return entry

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} by user={self.user_id} at {self.created_at}>"
