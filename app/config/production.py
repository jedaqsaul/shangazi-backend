import os
from .base import BaseConfig


class ProductionConfig(BaseConfig):
    """
    Production environment configuration.
    PostgreSQL database. Strict rate limits.
    No debug output exposed.
    """

    DEBUG = False
    TESTING = False

    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")

    # PostgreSQL connection pool tuning for production
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_size": 10,
        "max_overflow": 20,
    }

    # Strict rate limits for production
    RATELIMIT_DEFAULT = "200 per day;50 per hour"

    DARAJA_ENV = "production"
