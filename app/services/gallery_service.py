"""
Gallery Service
---------------
Business logic for managing public gallery images.
Controllers call these functions — they never touch the DB or
Cloudinary directly.
"""

from app.extensions import db
from app.models.gallery_image import GalleryImage
from app.models.audit_log import AuditLog
from app.services.cloudinary_service import CloudinaryService
from app.utils.logger import get_logger

logger = get_logger(__name__)

VALID_CATEGORIES = {
    "education", "healthcare", "feeding", "shelter",
    "community", "events", "general",
}


class GalleryService:

    @staticmethod
    def list_public_images(category: str | None = None) -> list[dict]:
        """
        Return published gallery images for the public Gallery page,
        ordered for display. Optionally filtered by category.
        """
        query = GalleryImage.query
        if category and category != "all":
            query = query.filter_by(category=category)

        images = query.order_by(
            GalleryImage.display_order.asc(),
            GalleryImage.created_at.desc()
        ).all()

        return [image.to_dict() for image in images]

    @staticmethod
    def list_admin_images(page: int = 1, per_page: int = 24) -> dict:
        """Paginated gallery listing for the admin dashboard."""
        pagination = GalleryImage.query.order_by(
            GalleryImage.display_order.asc(),
            GalleryImage.created_at.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)

        return {
            "items": [image.to_dict() for image in pagination.items],
            "total": pagination.total,
            "page": page,
            "per_page": per_page,
            "pages": pagination.pages,
        }

    @staticmethod
    def create_image(
        file_storage,
        title: str | None,
        category: str,
        display_order: int,
        admin_id: str,
        ip_address: str,
    ) -> GalleryImage:
        """
        Upload an image to Cloudinary and create its gallery record.
        Raises ValueError for invalid input, RuntimeError if the
        Cloudinary upload itself fails.
        """
        if category not in VALID_CATEGORIES:
            raise ValueError(
                f"Invalid category '{category}'. "
                f"Must be one of: {', '.join(sorted(VALID_CATEGORIES))}."
            )

        CloudinaryService.validate_image(file_storage)
        upload_result = CloudinaryService.upload_image(file_storage, folder="gallery")

        image = GalleryImage(
            title=title,
            category=category,
            cloudinary_url=upload_result["url"],
            cloudinary_public_id=upload_result["public_id"],
            display_order=display_order,
        )
        db.session.add(image)

        AuditLog.log(
            action="GALLERY_IMAGE_CREATED",
            user_id=admin_id,
            resource="gallery_images",
            ip_address=ip_address,
            details={"category": category, "title": title}
        )
        db.session.commit()

        logger.info(
            "Gallery image created",
            extra={"extra": {"image_id": image.id, "category": category}}
        )

        return image

    @staticmethod
    def delete_image(image_id: str, admin_id: str, ip_address: str) -> None:
        """
        Delete a gallery image — removes both the Cloudinary asset and
        the DB record. Raises ValueError if the image doesn't exist.
        """
        image = GalleryImage.query.get(image_id)
        if not image:
            raise ValueError("Gallery image not found.")

        # Delete from Cloudinary first; if it fails we log and continue
        # rather than leaving an orphaned DB record with no way to retry.
        CloudinaryService.delete_image(image.cloudinary_public_id)

        db.session.delete(image)

        AuditLog.log(
            action="GALLERY_IMAGE_DELETED",
            user_id=admin_id,
            resource="gallery_images",
            ip_address=ip_address,
            details={"image_id": image_id, "category": image.category}
        )
        db.session.commit()

        logger.info(
            "Gallery image deleted",
            extra={"extra": {"image_id": image_id}}
        )

    @staticmethod
    def update_image(
        image_id: str,
        admin_id: str,
        ip_address: str,
        title: str | None = None,
        category: str | None = None,
        display_order: int | None = None,
    ) -> GalleryImage:
        """Update metadata on an existing gallery image (no re-upload)."""
        image = GalleryImage.query.get(image_id)
        if not image:
            raise ValueError("Gallery image not found.")

        if category is not None:
            if category not in VALID_CATEGORIES:
                raise ValueError(
                    f"Invalid category '{category}'. "
                    f"Must be one of: {', '.join(sorted(VALID_CATEGORIES))}."
                )
            image.category = category

        if title is not None:
            image.title = title

        if display_order is not None:
            image.display_order = display_order

        AuditLog.log(
            action="GALLERY_IMAGE_UPDATED",
            user_id=admin_id,
            resource="gallery_images",
            ip_address=ip_address,
            details={"image_id": image_id}
        )
        db.session.commit()

        return image
