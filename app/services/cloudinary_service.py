"""
Cloudinary Service
-------------------
Thin wrapper around the Cloudinary SDK, shared by every content type
that needs image uploads (gallery, impact stories, programs).

All uploads go through the backend (never direct-from-browser), so the
Cloudinary API secret never has to be exposed to the client.
"""

import cloudinary
import cloudinary.uploader
from flask import current_app
from app.utils.logger import get_logger

logger = get_logger(__name__)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

_configured = False


def _ensure_configured() -> None:
    """
    Configure the Cloudinary SDK from app config on first use.
    Cloudinary's SDK keeps its config as global module state, so this
    only needs to run once per process, not once per request.
    """
    global _configured
    if _configured:
        return

    cloudinary.config(
        cloud_name=current_app.config["CLOUDINARY_CLOUD_NAME"],
        api_key=current_app.config["CLOUDINARY_API_KEY"],
        api_secret=current_app.config["CLOUDINARY_API_SECRET"],
        secure=True,
    )
    _configured = True


class CloudinaryService:

    @staticmethod
    def validate_image(file_storage) -> None:
        """
        Validate an uploaded file before sending it to Cloudinary.
        Raises ValueError on anything invalid.
        """
        if file_storage is None or file_storage.filename == "":
            raise ValueError("No image file was provided.")

        filename = file_storage.filename
        extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if extension not in ALLOWED_EXTENSIONS:
            raise ValueError(
                f"Unsupported image type '.{extension}'. "
                f"Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
            )

        max_size = current_app.config.get("MAX_IMAGE_UPLOAD_SIZE", 5 * 1024 * 1024)

        # FileStorage doesn't expose size directly without reading the
        # stream, so seek to the end to measure, then rewind for upload.
        file_storage.stream.seek(0, 2)
        size = file_storage.stream.tell()
        file_storage.stream.seek(0)

        if size > max_size:
            max_mb = max_size / (1024 * 1024)
            raise ValueError(f"Image is too large. Maximum size is {max_mb:.0f}MB.")

    @staticmethod
    def upload_image(file_storage, folder: str) -> dict:
        """
        Upload an image to Cloudinary under the given folder.
        Returns {"url": secure_url, "public_id": public_id}.
        Raises RuntimeError if the upload itself fails (network, Cloudinary error).
        """
        _ensure_configured()

        try:
            result = cloudinary.uploader.upload(
                file_storage,
                folder=f"shangazi/{folder}",
                resource_type="image",
                overwrite=False,
            )
        except Exception as e:
            logger.error(
                "Cloudinary upload failed",
                extra={"extra": {"folder": folder, "error": str(e)}}
            )
            raise RuntimeError("Image upload failed. Please try again.") from e

        logger.info(
            "Image uploaded to Cloudinary",
            extra={"extra": {"public_id": result.get("public_id"), "folder": folder}}
        )

        return {
            "url": result["secure_url"],
            "public_id": result["public_id"],
        }

    @staticmethod
    def delete_image(public_id: str) -> None:
        """
        Delete an image from Cloudinary by its public_id.
        Logs a warning on failure but does not raise — a failed Cloudinary
        deletion should not block deleting the DB record that referenced it.
        """
        if not public_id:
            return

        _ensure_configured()

        try:
            cloudinary.uploader.destroy(public_id)
            logger.info(
                "Image deleted from Cloudinary",
                extra={"extra": {"public_id": public_id}}
            )
        except Exception as e:
            logger.warning(
                "Cloudinary deletion failed (continuing anyway)",
                extra={"extra": {"public_id": public_id, "error": str(e)}}
            )
