# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Format execution output for the console panel."""

from __future__ import annotations

import html
import re as _re

from pylearn.executor.sandbox import ExecutionResult

_COLOR_RE = _re.compile(r'^#[0-9a-fA-F]{3,8}$|^[a-zA-Z]+$')


class OutputHandler:
    """Format stdout/stderr for display in the console panel."""

    def __init__(self) -> None:
        self._stdout_color = "#d4d4d4"

    def set_theme(self, theme_name: str) -> None:
        """Update output colors to match the active theme."""
        from pylearn.ui.theme_registry import get_palette
        p = get_palette(theme_name)
        self._stdout_color = p.text

    def format_result(self, result: ExecutionResult) -> str:
        """Format an execution result as styled HTML for the console."""
        parts = []

        if result.stdout:
            escaped = html.escape(result.stdout)
            parts.append(
                f'<pre style="color:{self._stdout_color}; margin:0; white-space:pre-wrap; '
                f'font-family:Consolas, monospace;">{escaped}</pre>'
            )

        if result.stderr:
            escaped = html.escape(result.stderr)
            color = "#ff6b6b" if result.return_code != 0 else "#ffa07a"
            parts.append(
                f'<pre style="color:{color}; margin:0; white-space:pre-wrap; '
                f'font-family:Consolas, monospace;">{escaped}</pre>'
            )

        if result.timed_out:
            parts.append(
                '<p style="color:#ff6b6b; font-family:Consolas, monospace; '
                'font-weight:bold;">Execution timed out.</p>'
            )

        if result.killed:
            parts.append(
                '<p style="color:#ffa500; font-family:Consolas, monospace; '
                'font-weight:bold;">Execution stopped by user.</p>'
            )

        if not parts:
            parts.append(
                '<p style="color:#888; font-family:Consolas, monospace; '
                'font-style:italic;">(No output)</p>'
            )

        return "\n".join(parts)

    def format_status(self, message: str, color: str = "#888") -> str:
        """Format a status message."""
        if not _COLOR_RE.match(color):
            color = "#888"  # fallback to default
        escaped = html.escape(message)
        return (
            f'<p style="color:{color}; font-family:Consolas, monospace; '
            f'font-style:italic; margin:4px 0;">{escaped}</p>'
        )

    def format_separator(self) -> str:
        """Format a visual separator between runs."""
        return '<hr style="border:none; border-top:1px solid #444; margin:8px 0;">'
