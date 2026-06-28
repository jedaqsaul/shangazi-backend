"""
Impact Story Model
-------------------
Represents a single testimonial/impact story shown on the public
Impact page. Each story has a name, role, short quote, and a photo
uploaded by an admin through the dashboard (stored in Cloudinary).
"""

import uuid
from datetime import datetime, timezone
from app.extensions import db


class ImpactStory(db.Model):
    __tablename__ = "impact_stories"

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    name = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(150), nullable=True)
    quote = db.Column(db.Text, nullable=False)

    # Cloudinary
    cloudinary_url = db.Column(db.String(500), nullable=True)
    cloudinary_public_id = db.Column(db.String(255), nullable=True)

    # Ordering on the public Impact page (lower = shown first)
    display_order = db.Column(db.Integer, nullable=False, default=0, index=True)

    # Allows an admin to draft a story before it appears publicly
    is_published = db.Column(db.Boolean, nullable=False, default=True, index=True)

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "quote": self.quote,
            "image": self.cloudinary_url,
            "display_order": self.display_order,
            "is_published": self.is_published,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def __repr__(self) -> str:
        return f"<ImpactStory {self.id} | {self.name}>"
