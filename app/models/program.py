"""
Program Model
--------------
Represents a single program (Education, Healthcare, Feeding, etc.)
shown on the public Programs page. Unlike Gallery/ImpactStory, this
is fully admin-managed — title, description, icon, color, and an
arbitrary list of metrics are all editable, not just the photo.
"""

import uuid
from datetime import datetime, timezone
from app.extensions import db

# Icons the admin can choose from. Kept as a fixed set (rather than
# free text) so the frontend can safely map a string to a known
# lucide-react component without any risk of an arbitrary/invalid value.
VALID_ICONS = {
    "BookOpen", "Stethoscope", "Utensils", "Home", "Users",
    "GraduationCap", "Shield", "Heart", "Sparkles", "HandHeart",
}

# Brand colors only — matches the four theme colors defined in
# tailwind.config.js, keeping the public page visually consistent.
VALID_COLORS = {"forest", "terracotta", "amber", "sage"}


class Program(db.Model):
    __tablename__ = "programs"

    id = db.Column(
        db.String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)

    icon = db.Column(db.String(50), nullable=False, default="Heart")
    color = db.Column(db.String(20), nullable=False, default="forest")

    # List of {"label": str, "value": str} dicts. Stored as JSON since
    # the admin can add/remove metric rows freely — no fixed count.
    metrics = db.Column(db.JSON, nullable=False, default=list)

    # Cloudinary (optional — public page falls back to an icon-on-gradient
    # treatment when no photo is set, same as today's hardcoded version)
    cloudinary_url = db.Column(db.String(500), nullable=True)
    cloudinary_public_id = db.Column(db.String(255), nullable=True)

    display_order = db.Column(db.Integer, nullable=False, default=0, index=True)
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
            "title": self.title,
            "description": self.description,
            "icon": self.icon,
            "color": self.color,
            "metrics": self.metrics or [],
            "image": self.cloudinary_url,
            "display_order": self.display_order,
            "is_published": self.is_published,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def __repr__(self) -> str:
        return f"<Program {self.id} | {self.title}>"
