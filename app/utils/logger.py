"""
Logger Utility
--------------
Structured JSON logging for all application events.
Sensitive fields (passwords, tokens, PINs) are never logged.
Log levels map to event severity:
  DEBUG   → internal flow tracing (dev only)
  INFO    → normal operational events
  WARNING → recoverable issues, suspicious activity
  ERROR   → failures requiring attention
"""

import logging
import json
import os
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """
    Formats log records as single-line JSON objects.
    Safe for ingestion by log aggregators (Datadog, CloudWatch, etc.)
    """

    SENSITIVE_KEYS = {
        "password", "password_hash", "token", "access_token",
        "refresh_token", "pin", "secret", "passkey",
        "consumer_secret", "authorization",
    }

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Attach any extra context passed to the logger
        if hasattr(record, "extra"):
            log_entry["context"] = self._sanitize(record.extra)

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)

    def _sanitize(self, data: dict) -> dict:
        """Remove sensitive keys from log context."""
        return {
            k: "***REDACTED***" if k.lower() in self.SENSITIVE_KEYS else v
            for k, v in data.items()
        }


def get_logger(name: str) -> logging.Logger:
    """
    Returns a named logger with JSON formatting.
    Usage:
        from app.utils.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Donation initiated", extra={"extra": {"amount": 500, "phone": "2547..."}})
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)

    level = logging.DEBUG if os.environ.get("FLASK_ENV") == "development" else logging.INFO
    logger.setLevel(level)
    logger.propagate = False

    return logger
