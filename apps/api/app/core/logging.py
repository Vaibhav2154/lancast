import json
import logging
from datetime import UTC, datetime
from typing import Any

REDACTED_KEYS = frozenset({"password", "password_hash", "token", "authorization", "answer", "secret"})


class StructuredJsonFormatter(logging.Formatter):
    """Structured JSON logger that redacts sensitive fields (FR-OBS-03)."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        extra = getattr(record, "structured", None)
        if isinstance(extra, dict):
            payload["context"] = {
                k: ("[REDACTED]" if k.lower() in REDACTED_KEYS else v)
                for k, v in extra.items()
            }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredJsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
