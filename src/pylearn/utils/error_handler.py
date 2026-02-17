# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Custom exceptions, logging setup, and crash-safe UI helpers."""

from __future__ import annotations

import functools
import logging
import sys
import traceback
from pathlib import Path
from types import TracebackType
from typing import Any, Callable, TypeVar

from pylearn.core.constants import DATA_DIR

F = TypeVar("F", bound=Callable[..., Any])


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


def install_global_exception_handler() -> None:
    """Install sys.excepthook so unhandled exceptions show a dialog instead of silently crashing.

    PyQt6 calls qFatal() on unhandled exceptions in slots, which terminates the
    process with no user feedback. This hook intercepts those exceptions, logs them,
    and shows an error dialog.
    """
    logger = logging.getLogger("pylearn")

    def _handle_exception(
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_tb: TracebackType | None,
    ) -> None:
        # Let KeyboardInterrupt pass through normally
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return

        logger.critical(
            "Unhandled exception", exc_info=(exc_type, exc_value, exc_tb),
        )

        # Show error dialog (import here to avoid circular imports at module level)
        try:
            from PyQt6.QtWidgets import QMessageBox
            tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
            dialog = QMessageBox()
            dialog.setIcon(QMessageBox.Icon.Critical)
            dialog.setWindowTitle("PyLearn — Unexpected Error")
            dialog.setText(f"{exc_type.__name__}: {exc_value}")
            dialog.setDetailedText(tb_text)
            dialog.exec()
        except Exception:
            # If the dialog itself fails, at least print to stderr
            traceback.print_exception(exc_type, exc_value, exc_tb)

    sys.excepthook = _handle_exception


def safe_slot(func: F) -> F:
    """Decorator for Qt slot methods — catches exceptions and shows an error dialog.

    Use on any method connected to a Qt signal (menu actions, button clicks, etc.)
    so that a bug in one handler doesn't silently kill the app.
    """
    @functools.wraps(func)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            return func(self, *args, **kwargs)
        except Exception as exc:
            _logger = logging.getLogger("pylearn.ui")
            _logger.exception("Error in %s", func.__name__)
            try:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self, "Error",
                    f"An error occurred in {func.__name__}:\n\n"
                    f"{type(exc).__name__}: {exc}",
                )
            except Exception:
                pass  # Last resort — already logged above
    return wrapper  # type: ignore[return-value]
