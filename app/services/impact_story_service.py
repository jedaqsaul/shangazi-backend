"""
Impact Story Service
---------------------
Business logic for managing public impact stories/testimonials.
Controllers call these functions — they never touch the DB or
Cloudinary directly.

Unlike gallery images, a photo is optional here: the public page
falls back to initials when no photo is provided.
"""

from app.extensions import db
from app.models.impact_story import ImpactStory
from app.models.audit_log import AuditLog
from app.services.cloudinary_service import CloudinaryService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ImpactStoryService:

    @staticmethod
    def list_public_stories() -> list[dict]:
        """Return published impact stories for the public Impact page."""
        stories = ImpactStory.query.filter_by(is_published=True).order_by(
            ImpactStory.display_order.asc(),
            ImpactStory.created_at.desc()
        ).all()

        return [story.to_dict() for story in stories]

    @staticmethod
    def list_admin_stories(page: int = 1, per_page: int = 24) -> dict:
        """Paginated impact story listing for the admin dashboard (published + drafts)."""
        pagination = ImpactStory.query.order_by(
            ImpactStory.display_order.asc(),
            ImpactStory.created_at.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)

        return {
            "items": [story.to_dict() for story in pagination.items],
            "total": pagination.total,
            "page": page,
            "per_page": per_page,
            "pages": pagination.pages,
        }

    @staticmethod
    def create_story(
        name: str,
        quote: str,
        admin_id: str,
        ip_address: str,
        role: str | None = None,
        file_storage=None,
        display_order: int = 0,
        is_published: bool = True,
    ) -> ImpactStory:
        """
        Create a new impact story. Photo is optional — raises ValueError
        for invalid input, RuntimeError if a provided photo fails to upload.
        """
        if not name or not name.strip():
            raise ValueError("Name is required.")
        if not quote or not quote.strip():
            raise ValueError("Quote is required.")

        cloudinary_url = None
        cloudinary_public_id = None

        if file_storage is not None and file_storage.filename:
            CloudinaryService.validate_image(file_storage)
            upload_result = CloudinaryService.upload_image(file_storage, folder="impact_stories")
            cloudinary_url = upload_result["url"]
            cloudinary_public_id = upload_result["public_id"]

        story = ImpactStory(
            name=name.strip(),
            role=role.strip() if role else None,
            quote=quote.strip(),
            cloudinary_url=cloudinary_url,
            cloudinary_public_id=cloudinary_public_id,
            display_order=display_order,
            is_published=is_published,
        )
        db.session.add(story)

        AuditLog.log(
            action="IMPACT_STORY_CREATED",
            user_id=admin_id,
            resource="impact_stories",
            ip_address=ip_address,
            details={"name": name}
        )
        db.session.commit()

        logger.info(
            "Impact story created",
            extra={"extra": {"story_id": story.id, "name": name}}
        )

        return story

    @staticmethod
    def delete_story(story_id: str, admin_id: str, ip_address: str) -> None:
        """
        Delete an impact story — removes the Cloudinary asset (if any)
        and the DB record. Raises ValueError if the story doesn't exist.
        """
        story = ImpactStory.query.get(story_id)
        if not story:
            raise ValueError("Impact story not found.")

        if story.cloudinary_public_id:
            CloudinaryService.delete_image(story.cloudinary_public_id)

        db.session.delete(story)

        AuditLog.log(
            action="IMPACT_STORY_DELETED",
            user_id=admin_id,
            resource="impact_stories",
            ip_address=ip_address,
            details={"story_id": story_id, "name": story.name}
        )
        db.session.commit()

        logger.info(
            "Impact story deleted",
            extra={"extra": {"story_id": story_id}}
        )

    @staticmethod
    def update_story(
        story_id: str,
        admin_id: str,
        ip_address: str,
        name: str | None = None,
        role: str | None = None,
        quote: str | None = None,
        display_order: int | None = None,
        is_published: bool | None = None,
        file_storage=None,
    ) -> ImpactStory:
        """
        Update an existing impact story's metadata, and optionally
        replace its photo (deletes the old Cloudinary asset if so).
        """
        story = ImpactStory.query.get(story_id)
        if not story:
            raise ValueError("Impact story not found.")

        if name is not None:
            if not name.strip():
                raise ValueError("Name cannot be empty.")
            story.name = name.strip()

        if role is not None:
            story.role = role.strip() or None

        if quote is not None:
            if not quote.strip():
                raise ValueError("Quote cannot be empty.")
            story.quote = quote.strip()

        if display_order is not None:
            story.display_order = display_order

        if is_published is not None:
            story.is_published = is_published

        if file_storage is not None and file_storage.filename:
            CloudinaryService.validate_image(file_storage)
            upload_result = CloudinaryService.upload_image(file_storage, folder="impact_stories")

            old_public_id = story.cloudinary_public_id
            story.cloudinary_url = upload_result["url"]
            story.cloudinary_public_id = upload_result["public_id"]

            if old_public_id:
                CloudinaryService.delete_image(old_public_id)

        AuditLog.log(
            action="IMPACT_STORY_UPDATED",
            user_id=admin_id,
            resource="impact_stories",
            ip_address=ip_address,
            details={"story_id": story_id}
        )
        db.session.commit()

        return story
