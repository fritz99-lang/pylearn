# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Comprehensive unit tests for OutputHandler.

Tests cover format_result with every combination of stdout, stderr,
timed_out, killed, and empty output.  Also tests format_status with
valid/invalid colors and HTML escaping, plus format_separator.
"""

from __future__ import annotations

import pytest

from pylearn.executor.output_handler import OutputHandler
from pylearn.executor.sandbox import ExecutionResult

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def handler() -> OutputHandler:
    """A fresh OutputHandler instance."""
    return OutputHandler()


# ---------------------------------------------------------------------------
# format_result — stdout only
# ---------------------------------------------------------------------------


class TestFormatResultStdout:
    def test_stdout_only(self, handler: OutputHandler) -> None:
        result = ExecutionResult(stdout="Hello, world!", return_code=0)
        output = handler.format_result(result)
        assert "Hello, world!" in output
        assert "<pre" in output

    def test_stdout_uses_monospace_font(self, handler: OutputHandler) -> None:
        result = ExecutionResult(stdout="output", return_code=0)
        output = handler.format_result(result)
        assert "Consolas" in output

    def test_stdout_html_is_escaped(self, handler: OutputHandler) -> None:
        result = ExecutionResult(
            stdout="<script>alert('xss')</script>",
            return_code=0,
        )
        output = handler.format_result(result)
        assert "<script>" not in output
        assert "&lt;script&gt;" in output

    def test_stdout_preserves_whitespace_via_pre(self, handler: OutputHandler) -> None:
        result = ExecutionResult(stdout="line1\n  line2\n    line3", return_code=0)
        output = handler.format_result(result)
        assert "pre-wrap" in output


# ---------------------------------------------------------------------------
# format_result — stderr
# ---------------------------------------------------------------------------


class TestFormatResultStderr:
    def test_stderr_only_with_error_code(self, handler: OutputHandler) -> None:
        result = ExecutionResult(stderr="NameError: x", return_code=1)
        output = handler.format_result(result)
        assert "NameError: x" in output
        assert "#ff6b6b" in output  # error red color

    def test_stderr_with_zero_return_code(self, handler: OutputHandler) -> None:
        """stderr with return_code=0 uses the lighter warning color."""
        result = ExecutionResult(stderr="DeprecationWarning: ...", return_code=0)
        output = handler.format_result(result)
        assert "#ffa07a" in output  # light salmon (warning, not error)

    def test_stderr_escapes_html(self, handler: OutputHandler) -> None:
        result = ExecutionResult(
            stderr="TypeError: unsupported operand type(s) for <: 'str' and 'int'",
            return_code=1,
        )
        output = handler.format_result(result)
        # The < should be escaped
        assert "&lt;" in output


# ---------------------------------------------------------------------------
# format_result — both stdout and stderr
# ---------------------------------------------------------------------------


class TestFormatResultBoth:
    def test_both_stdout_and_stderr(self, handler: OutputHandler) -> None:
        result = ExecutionResult(
            stdout="partial output",
            stderr="then it crashed",
            return_code=1,
        )
        output = handler.format_result(result)
        assert "partial output" in output
        assert "then it crashed" in output

    def test_stdout_appears_before_stderr(self, handler: OutputHandler) -> None:
        result = ExecutionResult(
            stdout="FIRST",
            stderr="SECOND",
            return_code=1,
        )
        output = handler.format_result(result)
        first_pos = output.index("FIRST")
        second_pos = output.index("SECOND")
        assert first_pos < second_pos


# ---------------------------------------------------------------------------
# format_result — timed_out
# ---------------------------------------------------------------------------


class TestFormatResultTimeout:
    def test_timed_out_message(self, handler: OutputHandler) -> None:
        result = ExecutionResult(timed_out=True, return_code=-1)
        output = handler.format_result(result)
        assert "timed out" in output.lower()
        assert "font-weight:bold" in output

    def test_timed_out_with_partial_stdout(self, handler: OutputHandler) -> None:
        result = ExecutionResult(
            stdout="partial",
            timed_out=True,
            return_code=-1,
        )
        output = handler.format_result(result)
        assert "partial" in output
        assert "timed out" in output.lower()


# ---------------------------------------------------------------------------
# format_result — killed
# ---------------------------------------------------------------------------


class TestFormatResultKilled:
    def test_killed_message(self, handler: OutputHandler) -> None:
        result = ExecutionResult(killed=True, return_code=-1)
        output = handler.format_result(result)
        assert "stopped by user" in output.lower()
        assert "#ffa500" in output  # orange color

    def test_killed_with_partial_stdout(self, handler: OutputHandler) -> None:
        result = ExecutionResult(
            stdout="running...",
            killed=True,
            return_code=-1,
        )
        output = handler.format_result(result)
        assert "running..." in output
        assert "stopped by user" in output.lower()


# ---------------------------------------------------------------------------
# format_result — no output
# ---------------------------------------------------------------------------


class TestFormatResultEmpty:
    def test_no_output_at_all(self, handler: OutputHandler) -> None:
        result = ExecutionResult(return_code=0)
        output = handler.format_result(result)
        assert "(No output)" in output
        assert "font-style:italic" in output

    def test_no_output_uses_muted_color(self, handler: OutputHandler) -> None:
        result = ExecutionResult(return_code=0)
        output = handler.format_result(result)
        assert "#888" in output


# ---------------------------------------------------------------------------
# format_status
# ---------------------------------------------------------------------------


class TestFormatStatus:
    def test_basic_status_message(self, handler: OutputHandler) -> None:
        output = handler.format_status("Running...")
        assert "Running..." in output
        assert "<p" in output

    def test_status_with_valid_hex_color(self, handler: OutputHandler) -> None:
        output = handler.format_status("OK", color="#00ff00")
        assert "#00ff00" in output

    def test_status_with_valid_named_color(self, handler: OutputHandler) -> None:
        output = handler.format_status("OK", color="green")
        assert "green" in output

    def test_status_with_invalid_color_falls_back(self, handler: OutputHandler) -> None:
        output = handler.format_status("Bad color", color="not-a-color!")
        assert "#888" in output
        assert "not-a-color!" not in output

    def test_status_with_script_injection_color(self, handler: OutputHandler) -> None:
        """A color value containing special chars should be rejected."""
        output = handler.format_status("msg", color='"><script>alert(1)</script>')
        assert "#888" in output
        assert "<script>" not in output

    def test_status_escapes_html_in_message(self, handler: OutputHandler) -> None:
        output = handler.format_status("<b>bold</b> & stuff")
        assert "&lt;b&gt;" in output
        assert "&amp;" in output
        assert "<b>bold</b>" not in output

    def test_status_default_color(self, handler: OutputHandler) -> None:
        output = handler.format_status("info")
        assert "#888" in output

    def test_status_italic_style(self, handler: OutputHandler) -> None:
        output = handler.format_status("info")
        assert "font-style:italic" in output


# ---------------------------------------------------------------------------
# format_separator
# ---------------------------------------------------------------------------


class TestFormatSeparator:
    def test_separator_is_hr(self, handler: OutputHandler) -> None:
        output = handler.format_separator()
        assert "<hr" in output

    def test_separator_has_border_style(self, handler: OutputHandler) -> None:
        output = handler.format_separator()
        assert "border-top" in output
