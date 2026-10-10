import json
import logging
from datetime import UTC, datetime
from typing import Any

from shared.logging.context import (
    component_context,
    correlation_id_context,
)

_STANDARD_LOG_RECORD_FIELDS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "taskName",
}


class JsonFormatter(logging.Formatter):
    """Small dependency-free JSON formatter for GeoNex services."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created,
                tz=UTC,
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        correlation_id = correlation_id_context.get()
        component = component_context.get()

        if correlation_id is not None:
            payload["correlation_id"] = correlation_id

        if component is not None:
            payload["component"] = component

        for key, value in record.__dict__.items():
            if key.startswith("_"):
                continue

            if key in _STANDARD_LOG_RECORD_FIELDS:
                continue

            payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(
            payload,
            default=str,
            separators=(",", ":"),
        )


def configure_logging(
    level: str = "INFO",
) -> None:
    """Configure process-wide GeoNex structured logging."""

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level.upper())


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)