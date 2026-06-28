import os
from datetime import timedelta


class BaseConfig:
    """
    Base configuration shared across all environments.
    All environment-specific configs inherit from this class.
    """

    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY", "fallback-dev-key-change-in-prod")
    JSON_SORT_KEYS = False

    # SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    # JWT
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "fallback-jwt-key-change-in-prod")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        seconds=int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRES", 900))
    )
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        seconds=int(os.environ.get("JWT_REFRESH_TOKEN_EXPIRES", 604800))
    )
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"

    # CORS
    FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")

    # Rate Limiting
    RATELIMIT_STORAGE_URL = os.environ.get("RATELIMIT_STORAGE_URL", "memory://")
    RATELIMIT_DEFAULT = "200 per day;50 per hour"
    RATELIMIT_HEADERS_ENABLED = True

    # Daraja
    DARAJA_CONSUMER_KEY = os.environ.get("DARAJA_CONSUMER_KEY")
    DARAJA_CONSUMER_SECRET = os.environ.get("DARAJA_CONSUMER_SECRET")
    DARAJA_SHORTCODE = os.environ.get("DARAJA_SHORTCODE")
    DARAJA_PASSKEY = os.environ.get("DARAJA_PASSKEY")
    DARAJA_CALLBACK_URL = os.environ.get("DARAJA_CALLBACK_URL")
    DARAJA_ENV = os.environ.get("DARAJA_ENV", "sandbox")

    DARAJA_WHITELISTED_IPS = [
        ip.strip()
        for ip in os.environ.get(
            "DARAJA_WHITELISTED_IPS",
            "196.201.214.200,196.201.214.206,196.201.213.114,"
            "196.201.214.207,196.201.214.208,196.201.213.44,"
            "196.201.214.185,196.201.214.186,196.201.214.187,"
            "196.201.214.188,196.201.214.111,196.201.214.112",
        ).split(",")
    ]

    @property
    def DARAJA_BASE_URL(self):
        if self.DARAJA_ENV == "production":
            return "https://api.safaricom.co.ke"
        return "https://sandbox.safaricom.co.ke"

    # Cloudinary
    CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME")
    CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY")
    CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET")

    # Max upload size for content images, in bytes (default 5MB)
    MAX_IMAGE_UPLOAD_SIZE = int(os.environ.get("MAX_IMAGE_UPLOAD_SIZE", 5 * 1024 * 1024))
