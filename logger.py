"""Centralized logging configuration.

Under `pythonw` (no console), all `print()` output is silently discarded.
This module sets up a rotating file handler so we still have a trail when
debugging issues users report after the fact.

Usage:
    from logger import get_logger
    log = get_logger(__name__)
    log.info("starting up")
"""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from constants import LOG_DIR, APP_NAME

_initialized = False


def setup_logging(level: int = logging.INFO) -> None:
    """Initialize root logger. Idempotent."""
    global _initialized
    if _initialized:
        return

    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(LOG_DIR, "app.log")

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Rotating file: 1 MB per file, keep 5 backups
    file_handler = RotatingFileHandler(
        log_file, maxBytes=1_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(level)

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(file_handler)

    # Also log to stderr if a console is attached (i.e. running via `python`, not `pythonw`).
    if sys.stderr and sys.stderr.isatty():
        stream_handler = logging.StreamHandler(sys.stderr)
        stream_handler.setFormatter(fmt)
        stream_handler.setLevel(level)
        root.addHandler(stream_handler)

    logging.getLogger(APP_NAME).info("Logging initialized -> %s", log_file)
    _initialized = True


def get_logger(name: str) -> logging.Logger:
    """Get a named logger. Lazily initializes the root logger on first call."""
    if not _initialized:
        setup_logging()
    return logging.getLogger(name)
