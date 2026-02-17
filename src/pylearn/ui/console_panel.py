"""Console panel: displays code execution output."""

from __future__ import annotations

from PyQt6.QtWidgets import QTextBrowser
from PyQt6.QtGui import QFont

from pylearn.ui.theme_registry import get_palette


class ConsolePanel(QTextBrowser):
    """Right-bottom panel: displays stdout/stderr from code execution."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setOpenLinks(False)
        self.setFont(QFont("Consolas", 11))

        self.show_ready()

    def append_html(self, html_content: str) -> None:
        """Append HTML content to the console."""
        self.append(html_content)
        # Scroll to bottom
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def show_ready(self) -> None:
        """Show the ready message."""
        self.setHtml(
            '<p style="color:#888; font-family:Consolas, monospace; '
            'font-style:italic;">Ready.</p>'
        )

    def show_running(self) -> None:
        """Show a running indicator."""
        self.append(
            '<p style="color:#89b4fa; font-family:Consolas, monospace;">'
            'Running...</p>'
        )

    def set_theme(self, theme_name: str) -> None:
        """Switch console theme, derived from the centralized palette."""
        p = get_palette(theme_name)
        self.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {p.bg};
                color: {p.text};
                border: 1px solid {p.border};
                padding: 8px;
            }}
        """)

    def clear_console(self) -> None:
        """Clear all output."""
        self.clear()
        self.show_ready()
