"""Structured logging helpers."""

from __future__ import annotations

import json
import logging
from typing import Any


class JsonFormatter(logging.Formatter):
    """Format log records as compact JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "time": self.formatTime(record, self.datefmt),
        }
        if hasattr(record, "extra"):
            payload.update(record.extra)
        return json.dumps(payload, sort_keys=True)


def configure_logging(level: str = "INFO", json_logs: bool = True) -> None:
    """Configure root logging for applications that want DAVE defaults."""
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter() if json_logs else logging.Formatter("%(levelname)s %(name)s %(message)s"))
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO), handlers=[handler], force=True)


def get_logger(name: str) -> logging.Logger:
    """Return a logger."""
    return logging.getLogger(name)
