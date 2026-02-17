"""Custom exceptions and logging setup."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from pylearn.core.constants import DATA_DIR


class PyLearnError(Exception):
    """Base exception for PyLearn."""


class PDFParseError(PyLearnError):
    """Error during PDF parsing."""


class BookNotFoundError(PyLearnError):
    """Book PDF file not found."""


class CacheError(PyLearnError):
    """Error reading/writing cache."""


class ExecutionError(PyLearnError):
    """Error executing user code."""


class ExecutionTimeoutError(ExecutionError):
    """Code execution exceeded timeout."""


def setup_logging(debug: bool = False) -> logging.Logger:
    """Configure application logging."""
    logger = logging.getLogger("pylearn")
    # Guard against duplicate handlers on repeated calls
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG if debug else logging.INFO)

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG if debug else logging.INFO)
    console.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    ))
    logger.addHandler(console)

    # File handler with rotation (5 MB max, 3 backups)
    from logging.handlers import RotatingFileHandler
    log_dir = DATA_DIR
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_dir / "pylearn.log", maxBytes=5 * 1024 * 1024,
        backupCount=3, encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    ))
    logger.addHandler(file_handler)

    return logger
