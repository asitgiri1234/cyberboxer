"""
app.utils.logger
----------------
Application-wide logging configuration.

Configures the root logger so that log records are emitted to BOTH:
* the console (stdout) — useful during development and in container logs, and
* a rotating file at `logs/app.log` — useful for persistence and debugging.

Defaults to INFO level and a format that includes a timestamp, the log level
and the message. Call `setup_logging()` once, early in application start-up.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

from app.config import settings

# Shared log format: "2026-07-04 11:20:00,123 | INFO | message"
_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging() -> logging.Logger:
    """Configure and return the application logger.

    Idempotent: repeated calls will not attach duplicate handlers, which
    matters under auto-reload where modules may be imported more than once.
    """
    # Ensure the directory for the log file exists (e.g. `logs/`).
    log_dir = os.path.dirname(settings.LOG_FILE)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    formatter = logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Guard against adding handlers twice (e.g. on reload).
    if not root_logger.handlers:
        # Console handler -> stdout.
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        # Rotating file handler -> logs/app.log (max 5 MB, keep 5 backups).
        file_handler = RotatingFileHandler(
            settings.LOG_FILE,
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Return a named logger for the application to use.
    return logging.getLogger(settings.APP_NAME)
