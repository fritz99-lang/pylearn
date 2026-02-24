# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Tests for error_handler.py — logging setup, global exception hook, and safe_slot decorator."""

from __future__ import annotations

import logging
import sys
from unittest.mock import MagicMock, patch

import pytest

from pylearn.utils.error_handler import (
    BookNotFoundError,
    CacheError,
    ExecutionError,
    ExecutionTimeoutError,
    PDFParseError,
    PyLearnError,
    install_global_exception_handler,
    safe_slot,
    setup_logging,
)

# ---------------------------------------------------------------------------
# Custom exception hierarchy
# ---------------------------------------------------------------------------


class TestExceptionHierarchy:
    """Verify the custom exception classes inherit correctly."""

    def test_pylearn_error_is_exception(self):
        assert issubclass(PyLearnError, Exception)

    def test_pdf_parse_error_is_pylearn_error(self):
        assert issubclass(PDFParseError, PyLearnError)

    def test_book_not_found_error_is_pylearn_error(self):
        assert issubclass(BookNotFoundError, PyLearnError)

    def test_cache_error_is_pylearn_error(self):
        assert issubclass(CacheError, PyLearnError)

    def test_execution_error_is_pylearn_error(self):
        assert issubclass(ExecutionError, PyLearnError)

    def test_execution_timeout_is_execution_error(self):
        assert issubclass(ExecutionTimeoutError, ExecutionError)

    def test_can_catch_specific(self):
        with pytest.raises(PDFParseError):
            raise PDFParseError("bad pdf")

    def test_can_catch_via_base(self):
        with pytest.raises(PyLearnError):
            raise CacheError("cache broken")


# ---------------------------------------------------------------------------
# setup_logging()
# ---------------------------------------------------------------------------


class TestSetupLogging:
    """Test the logging configuration function."""

    @pytest.fixture(autouse=True)
    def _clean_logger(self):
        """Remove all handlers from the pylearn logger before and after each test."""
        logger = logging.getLogger("pylearn")
        logger.handlers.clear()
        yield
        logger.handlers.clear()

    def test_returns_logger_instance(self, tmp_path):
        with patch("pylearn.utils.error_handler.DATA_DIR", tmp_path):
            logger = setup_logging()
        assert isinstance(logger, logging.Logger)

    def test_logger_name_is_pylearn(self, tmp_path):
        with patch("pylearn.utils.error_handler.DATA_DIR", tmp_path):
            logger = setup_logging()
        assert logger.name == "pylearn"

    def test_debug_true_sets_debug_level(self, tmp_path):
        with patch("pylearn.utils.error_handler.DATA_DIR", tmp_path):
            logger = setup_logging(debug=True)
        assert logger.level == logging.DEBUG

    def test_debug_false_sets_info_level(self, tmp_path):
        with patch("pylearn.utils.error_handler.DATA_DIR", tmp_path):
            logger = setup_logging(debug=False)
        assert logger.level == logging.INFO

    def test_adds_console_and_file_handlers(self, tmp_path):
        with patch("pylearn.utils.error_handler.DATA_DIR", tmp_path):
            logger = setup_logging()
        # Should have exactly 2 handlers: StreamHandler + RotatingFileHandler
        assert len(logger.handlers) == 2
        handler_types = {type(h).__name__ for h in logger.handlers}
        assert "StreamHandler" in handler_types
        assert "RotatingFileHandler" in handler_types

    def test_duplicate_handler_guard(self, tmp_path):
        """Calling setup_logging twice should not duplicate handlers."""
        with patch("pylearn.utils.error_handler.DATA_DIR", tmp_path):
            logger1 = setup_logging()
            handler_count = len(logger1.handlers)
            logger2 = setup_logging()
        assert logger1 is logger2
        assert len(logger2.handlers) == handler_count

    def test_log_file_created(self, tmp_path):
        with patch("pylearn.utils.error_handler.DATA_DIR", tmp_path):
            setup_logging()
        log_file = tmp_path / "pylearn.log"
        assert log_file.exists()

    def test_log_directory_created_if_missing(self, tmp_path):
        log_dir = tmp_path / "subdir" / "logs"
        with patch("pylearn.utils.error_handler.DATA_DIR", log_dir):
            setup_logging()
        assert log_dir.exists()


# ---------------------------------------------------------------------------
# install_global_exception_handler()
# ---------------------------------------------------------------------------


class TestInstallGlobalExceptionHandler:
    """Test the sys.excepthook replacement."""

    @pytest.fixture(autouse=True)
    def _restore_excepthook(self):
        """Restore the original excepthook after each test."""
        original = sys.excepthook
        yield
        sys.excepthook = original

    def test_replaces_sys_excepthook(self):
        original = sys.excepthook
        install_global_exception_handler()
        assert sys.excepthook is not original

    def test_hook_is_not_default(self):
        install_global_exception_handler()
        assert sys.excepthook is not sys.__excepthook__

    def test_keyboard_interrupt_passed_through(self):
        """KeyboardInterrupt should be forwarded to sys.__excepthook__."""
        install_global_exception_handler()
        with patch.object(sys, "__excepthook__") as mock_default:
            try:
                raise KeyboardInterrupt()
            except KeyboardInterrupt:
                exc_type, exc_value, exc_tb = sys.exc_info()
                sys.excepthook(exc_type, exc_value, exc_tb)

            mock_default.assert_called_once()
            args = mock_default.call_args[0]
            assert args[0] is KeyboardInterrupt

    def test_other_exception_is_logged(self):
        """Non-KeyboardInterrupt exceptions should be logged as critical."""
        install_global_exception_handler()
        mock_logger = MagicMock()
        with patch("logging.getLogger", return_value=mock_logger):
            # Re-install so the new mock logger is captured
            install_global_exception_handler()
            with patch("pylearn.utils.error_handler.QMessageBox", create=True):
                try:
                    raise ValueError("test error")
                except ValueError:
                    exc_type, exc_value, exc_tb = sys.exc_info()
                    # Patch QMessageBox import inside the handler
                    with patch.dict("sys.modules", {"PyQt6.QtWidgets": MagicMock()}):
                        sys.excepthook(exc_type, exc_value, exc_tb)

            mock_logger.critical.assert_called_once()

    def test_qmessagebox_shown_for_non_keyboard_interrupt(self):
        """A QMessageBox should be shown for unhandled exceptions."""
        install_global_exception_handler()
        mock_qmb = MagicMock()
        mock_dialog = MagicMock()
        mock_qmb.return_value = mock_dialog
        # Patch the import that happens inside the handler
        mock_widgets = MagicMock()
        mock_widgets.QMessageBox = mock_qmb
        with patch.dict("sys.modules", {"PyQt6": MagicMock(), "PyQt6.QtWidgets": mock_widgets}):
            try:
                raise RuntimeError("crash")
            except RuntimeError:
                exc_type, exc_value, exc_tb = sys.exc_info()
                sys.excepthook(exc_type, exc_value, exc_tb)

        mock_dialog.exec.assert_called_once()

    def test_dialog_failure_falls_back_to_print(self):
        """If QMessageBox fails, the exception should be printed to stderr."""
        install_global_exception_handler()
        mock_widgets = MagicMock()
        mock_widgets.QMessageBox.side_effect = RuntimeError("no display")
        with patch.dict("sys.modules", {"PyQt6": MagicMock(), "PyQt6.QtWidgets": mock_widgets}):
            with patch("pylearn.utils.error_handler.traceback") as mock_tb:
                # format_exception still needs to work for the handler's try block
                mock_tb.format_exception.side_effect = RuntimeError("format fail too")
                mock_tb.print_exception = MagicMock()
                try:
                    raise TypeError("boom")
                except TypeError:
                    exc_type, exc_value, exc_tb = sys.exc_info()
                    sys.excepthook(exc_type, exc_value, exc_tb)

            # The fallback path calls traceback.print_exception with the exc info
            mock_tb.print_exception.assert_called_once_with(exc_type, exc_value, exc_tb)


# ---------------------------------------------------------------------------
# safe_slot()
# ---------------------------------------------------------------------------


class FakeWidget:
    """Minimal stand-in for a QWidget to test safe_slot."""

    def __init__(self) -> None:
        self.result: int | None = None

    @safe_slot
    def working_method(self) -> int:
        """A method that succeeds."""
        self.result = 42
        return self.result

    @safe_slot
    def failing_method(self) -> None:
        """A method that raises."""
        raise ValueError("test error")

    @safe_slot
    def method_with_args(self, x: int, y: int) -> int:
        """A method that takes args."""
        return x + y


class TestSafeSlot:
    """Test the safe_slot decorator."""

    def test_normal_execution_returns_value(self):
        widget = FakeWidget()
        result = widget.working_method()
        assert result == 42

    def test_normal_execution_sets_attribute(self):
        widget = FakeWidget()
        widget.working_method()
        assert widget.result == 42

    def test_exception_does_not_propagate(self):
        widget = FakeWidget()
        mock_widgets = MagicMock()
        with patch.dict("sys.modules", {"PyQt6": MagicMock(), "PyQt6.QtWidgets": mock_widgets}):
            # Should NOT raise
            result = widget.failing_method()
        assert result is None

    def test_exception_is_logged(self):
        widget = FakeWidget()
        mock_logger = MagicMock()
        mock_widgets = MagicMock()
        with patch("logging.getLogger", return_value=mock_logger):
            with patch.dict("sys.modules", {"PyQt6": MagicMock(), "PyQt6.QtWidgets": mock_widgets}):
                widget.failing_method()
        mock_logger.exception.assert_called_once()
        # Check the log message contains the function name
        log_args = mock_logger.exception.call_args
        assert "failing_method" in str(log_args)

    def test_qmessagebox_warning_called_on_exception(self):
        widget = FakeWidget()
        mock_qmb = MagicMock()
        mock_widgets = MagicMock()
        mock_widgets.QMessageBox = mock_qmb
        with patch.dict("sys.modules", {"PyQt6": MagicMock(), "PyQt6.QtWidgets": mock_widgets}):
            widget.failing_method()
        mock_qmb.warning.assert_called_once()
        warning_args = mock_qmb.warning.call_args[0]
        assert warning_args[0] is widget  # parent widget
        assert "Error" in warning_args[1]  # title
        assert "failing_method" in warning_args[2]  # message contains method name
        assert "ValueError" in warning_args[2]  # message contains exception type

    def test_preserves_function_name(self):
        assert FakeWidget.working_method.__name__ == "working_method"

    def test_preserves_function_doc(self):
        assert FakeWidget.working_method.__doc__ == "A method that succeeds."

    def test_preserves_failing_method_name(self):
        assert FakeWidget.failing_method.__name__ == "failing_method"

    def test_args_passed_through(self):
        widget = FakeWidget()
        result = widget.method_with_args(3, 7)
        assert result == 10

    def test_qmessagebox_failure_is_swallowed(self):
        """If QMessageBox itself fails, the decorator should still not propagate."""
        widget = FakeWidget()
        mock_widgets = MagicMock()
        mock_widgets.QMessageBox.warning.side_effect = RuntimeError("no display")
        with patch.dict("sys.modules", {"PyQt6": MagicMock(), "PyQt6.QtWidgets": mock_widgets}):
            # Should NOT raise even though QMessageBox.warning fails
            result = widget.failing_method()
        assert result is None
