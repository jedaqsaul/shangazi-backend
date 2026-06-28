"""
Gallery Image Model
--------------------
Represents a single image in the public Gallery page.
Images are uploaded by an admin through the dashboard, stored in
Cloudinary, and referenced here by URL + public_id (public_id is
needed to delete the asset from Cloudinary later).
"""

import uuid
from datetime import datetime, timezone
from app.extensions import db


class GalleryImage(db.Model):
    __tablename__ = "gallery_images"

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    title = db.Column(db.String(150), nullable=True)
    category = db.Column(
        db.Enum(
            "education", "healthcare", "feeding", "shelter", "community",
            "events", "general",
            name="gallery_category"
        ),
        nullable=False,
        default="general",
        index=True
    )

    # Cloudinary
    cloudinary_url = db.Column(db.String(500), nullable=False)
    cloudinary_public_id = db.Column(db.String(255), nullable=False)

    # Ordering on the public gallery page (lower = shown first)
    display_order = db.Column(db.Integer, nullable=False, default=0, index=True)

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
            "title": self.title,
            "category": self.category,
            "url": self.cloudinary_url,
            "display_order": self.display_order,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def __repr__(self) -> str:
        return f"<GalleryImage {self.id} | {self.category} | {self.title}>"
