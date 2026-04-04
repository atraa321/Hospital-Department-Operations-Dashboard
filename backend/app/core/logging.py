from __future__ import annotations

import logging
from logging.config import dictConfig
from pathlib import Path

from app.core.config import get_settings


def configure_logging() -> None:
    settings = get_settings()
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
                },
                "access": {
                    "format": "%(asctime)s %(levelname)s %(client_addr)s \"%(request_line)s\" %(status_code)s",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                    "level": "INFO",
                },
                "app_file": {
                    "class": "logging.handlers.TimedRotatingFileHandler",
                    "formatter": "standard",
                    "filename": str(log_dir / "app.log"),
                    "when": "midnight",
                    "backupCount": 14,
                    "encoding": "utf-8",
                    "level": "INFO",
                },
                "error_file": {
                    "class": "logging.handlers.TimedRotatingFileHandler",
                    "formatter": "standard",
                    "filename": str(log_dir / "error.log"),
                    "when": "midnight",
                    "backupCount": 14,
                    "encoding": "utf-8",
                    "level": "WARNING",
                },
                "access_file": {
                    "class": "logging.handlers.TimedRotatingFileHandler",
                    "formatter": "access",
                    "filename": str(log_dir / "access.log"),
                    "when": "midnight",
                    "backupCount": 14,
                    "encoding": "utf-8",
                    "level": "INFO",
                },
            },
            "root": {
                "handlers": ["console", "app_file", "error_file"],
                "level": "INFO",
            },
            "loggers": {
                "uvicorn.error": {
                    "handlers": ["console", "app_file", "error_file"],
                    "level": "INFO",
                    "propagate": False,
                },
                "uvicorn.access": {
                    "handlers": ["access_file"],
                    "level": "INFO",
                    "propagate": False,
                },
            },
        }
    )
    logging.getLogger(__name__).info("logging configured")
