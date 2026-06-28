import os
from .base import BaseConfig


class DevelopmentConfig(BaseConfig):
    """
    Development environment configuration.
    Uses SQLite for zero-setup local development.
    Debug mode enabled. Relaxed rate limits.
    """

    DEBUG = True
    TESTING = False

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///shangazi_dev.db"
    )

    # Relaxed rate limits for development/testing
    RATELIMIT_DEFAULT = "1000 per day;500 per hour"

    # Allow localhost callback during sandbox testing
    DARAJA_ENV = "sandbox"
