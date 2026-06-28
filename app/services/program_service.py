"""
Program Service
-----------------
Business logic for managing programs (Education, Healthcare, etc).
Unlike Gallery/ImpactStory, this supports full CRUD on every field —
title, description, icon, color, metrics — not just the photo.
"""

from app.extensions import db
from app.models.program import Program, VALID_ICONS, VALID_COLORS
from app.models.audit_log import AuditLog
from app.services.cloudinary_service import CloudinaryService
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _validate_metrics(metrics) -> list[dict]:
    """
    Validate the metrics list. Each entry must be a dict with
    non-empty 'label' and 'value' string fields. Returns a cleaned list.
    Raises ValueError on anything malformed.
    """
    if metrics is None:
        return []
    if not isinstance(metrics, list):
        raise ValueError("Metrics must be a list of {label, value} items.")

    cleaned = []
    for i, item in enumerate(metrics):
        if not isinstance(item, dict):
            raise ValueError(f"Metric #{i + 1} must be an object with 'label' and 'value'.")
        label = str(item.get("label", "")).strip()
        value = str(item.get("value", "")).strip()
        if not label or not value:
            raise ValueError(f"Metric #{i + 1} needs both a label and a value.")
        cleaned.append({"label": label, "value": value})

    return cleaned


def _validate_icon(icon: str) -> str:
    if icon not in VALID_ICONS:
        raise ValueError(f"Invalid icon '{icon}'. Must be one of: {', '.join(sorted(VALID_ICONS))}.")
    return icon


def _validate_color(color: str) -> str:
    if color not in VALID_COLORS:
        raise ValueError(f"Invalid color '{color}'. Must be one of: {', '.join(sorted(VALID_COLORS))}.")
    return color


class ProgramService:

    @staticmethod
    def list_public_programs() -> list[dict]:
        """Return published programs for the public Programs page."""
        programs = Program.query.filter_by(is_published=True).order_by(
            Program.display_order.asc(),
            Program.created_at.asc()
        ).all()
        return [p.to_dict() for p in programs]

    @staticmethod
    def list_admin_programs(page: int = 1, per_page: int = 24) -> dict:
        """Paginated program listing for the admin dashboard (published + drafts)."""
        pagination = Program.query.order_by(
            Program.display_order.asc(),
            Program.created_at.asc()
        ).paginate(page=page, per_page=per_page, error_out=False)

        return {
            "items": [p.to_dict() for p in pagination.items],
            "total": pagination.total,
            "page": page,
            "per_page": per_page,
            "pages": pagination.pages,
        }

    @staticmethod
    def create_program(
        title: str,
        description: str,
        icon: str,
        color: str,
        admin_id: str,
        ip_address: str,
        metrics: list | None = None,
        display_order: int = 0,
        is_published: bool = True,
        file_storage=None,
    ) -> Program:
        """
        Create a new program. Photo is optional.
        Raises ValueError for invalid input, RuntimeError if a provided
        photo fails to upload.
        """
        if not title or not title.strip():
            raise ValueError("Title is required.")
        if not description or not description.strip():
            raise ValueError("Description is required.")

        icon = _validate_icon(icon)
        color = _validate_color(color)
        clean_metrics = _validate_metrics(metrics)

        cloudinary_url = None
        cloudinary_public_id = None

        if file_storage is not None and file_storage.filename:
            CloudinaryService.validate_image(file_storage)
            upload_result = CloudinaryService.upload_image(file_storage, folder="programs")
            cloudinary_url = upload_result["url"]
            cloudinary_public_id = upload_result["public_id"]

        program = Program(
            title=title.strip(),
            description=description.strip(),
            icon=icon,
            color=color,
            metrics=clean_metrics,
            cloudinary_url=cloudinary_url,
            cloudinary_public_id=cloudinary_public_id,
            display_order=display_order,
            is_published=is_published,
        )
        db.session.add(program)

        AuditLog.log(
            action="PROGRAM_CREATED",
            user_id=admin_id,
            resource="programs",
            ip_address=ip_address,
            details={"title": title}
        )
        db.session.commit()

        logger.info("Program created", extra={"extra": {"program_id": program.id, "title": title}})

        return program

    @staticmethod
    def update_program(
        program_id: str,
        admin_id: str,
        ip_address: str,
        title: str | None = None,
        description: str | None = None,
        icon: str | None = None,
        color: str | None = None,
        metrics: list | None = None,
        display_order: int | None = None,
        is_published: bool | None = None,
        file_storage=None,
    ) -> Program:
        """Update an existing program. All fields optional; sending a new photo replaces the old one."""
        program = Program.query.get(program_id)
        if not program:
            raise ValueError("Program not found.")

        if title is not None:
            if not title.strip():
                raise ValueError("Title cannot be empty.")
            program.title = title.strip()

        if description is not None:
            if not description.strip():
                raise ValueError("Description cannot be empty.")
            program.description = description.strip()

        if icon is not None:
            program.icon = _validate_icon(icon)

        if color is not None:
            program.color = _validate_color(color)

        if metrics is not None:
            program.metrics = _validate_metrics(metrics)

        if display_order is not None:
            program.display_order = display_order

        if is_published is not None:
            program.is_published = is_published

        if file_storage is not None and file_storage.filename:
            CloudinaryService.validate_image(file_storage)
            upload_result = CloudinaryService.upload_image(file_storage, folder="programs")

            old_public_id = program.cloudinary_public_id
            program.cloudinary_url = upload_result["url"]
            program.cloudinary_public_id = upload_result["public_id"]

            if old_public_id:
                CloudinaryService.delete_image(old_public_id)

        AuditLog.log(
            action="PROGRAM_UPDATED",
            user_id=admin_id,
            resource="programs",
            ip_address=ip_address,
            details={"program_id": program_id}
        )
        db.session.commit()

        return program

    @staticmethod
    def delete_program(program_id: str, admin_id: str, ip_address: str) -> None:
        """Delete a program — removes the Cloudinary asset (if any) and the DB record."""
        program = Program.query.get(program_id)
        if not program:
            raise ValueError("Program not found.")

        if program.cloudinary_public_id:
            CloudinaryService.delete_image(program.cloudinary_public_id)

        db.session.delete(program)

        AuditLog.log(
            action="PROGRAM_DELETED",
            user_id=admin_id,
            resource="programs",
            ip_address=ip_address,
            details={"program_id": program_id, "title": program.title}
        )
        db.session.commit()

        logger.info("Program deleted", extra={"extra": {"program_id": program_id}})
