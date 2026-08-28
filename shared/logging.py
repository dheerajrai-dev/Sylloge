"""Structured air-gapped logging for SAT-SA."""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class JSONFormatter(logging.Formatter):
    """Custom JSON log formatter for structured offline logging."""

    def __init__(self, service_name: str = "sat-sa"):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": self.service_name,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }

        if hasattr(record, "props") and isinstance(record.props, dict):  # type: ignore[attr-defined]
            log_obj.update(record.props)  # type: ignore[attr-defined]

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj)


def setup_logger(
    service_name: str = "sat-sa",
    log_level: Optional[str] = None,
) -> logging.Logger:
    """Configures and returns a structured JSON logger."""
    level_name = log_level or os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    logger = logging.getLogger(service_name)
    logger.setLevel(level)

    # Avoid duplicate handlers if already configured
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter(service_name=service_name))
        logger.addHandler(handler)
        logger.propagate = False

    return logger


# Default global root logger
logger = setup_logger("sat-sa")
