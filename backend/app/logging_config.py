"""Structured logging configuration with JSON and text format support.

Toggle via LOG_FORMAT env var: "json" (default in production) or "text" (default in debug).
Uses contextvars to propagate request_id through log records.
"""

import contextvars
import logging
from typing import Any

from pythonjsonlogger.json import JsonFormatter

# Context variable for request-scoped data
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """Inject request_id from contextvars into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get("-")  # type: ignore[attr-defined]
        return True


class StructuredJsonFormatter(JsonFormatter):
    """JSON formatter that includes timestamp, level, logger, request_id, and message."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            fmt="%(asctime)s %(levelname)s %(name)s %(request_id)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
            **kwargs,
        )

    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        super().add_fields(log_record, record, message_dict)
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["request_id"] = getattr(record, "request_id", "-")


def build_log_config(*, debug: bool = False, log_format: str = "auto") -> dict:
    """Build a logging.config.dictConfig-compatible dict.

    Args:
        debug: If True, set root level to DEBUG.
        log_format: "json", "text", or "auto" (json unless debug).
    """
    use_json = log_format == "json" or (log_format == "auto" and not debug)

    formatter_config: dict[str, Any]
    if use_json:
        formatter_config = {
            "()": "app.logging_config.StructuredJsonFormatter",
        }
    else:
        formatter_config = {
            "format": "%(asctime)s [%(levelname)s] %(name)s [%(request_id)s]: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        }

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "request_id": {
                "()": "app.logging_config.RequestIdFilter",
            },
        },
        "formatters": {
            "standard": formatter_config,
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "filters": ["request_id"],
                "stream": "ext://sys.stdout",
            },
        },
        "root": {
            "level": "DEBUG" if debug else "INFO",
            "handlers": ["console"],
        },
        "loggers": {
            "uvicorn": {"level": "INFO"},
            "sqlalchemy.engine": {"level": "WARNING"},
            "httpx": {"level": "WARNING"},
            "apscheduler": {"level": "INFO"},
            "py4j": {"level": "ERROR"},
            "pyspark": {"level": "WARNING"},
        },
    }
