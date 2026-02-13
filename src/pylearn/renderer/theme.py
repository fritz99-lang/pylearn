"""Reader display theme configuration."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ReaderTheme:
    """Theme settings for the reader panel HTML rendering."""
    # Background
    bg_color: str = "#ffffff"
    text_color: str = "#333333"

    # Headings
    h1_color: str = "#1a1a2e"
    h2_color: str = "#16213e"
    h3_color: str = "#0f3460"

    # Code blocks
    code_bg: str = "#272822"
    code_text: str = "#f8f8f2"
    code_border: str = "#444444"

    # Notes/tips/warnings
    note_bg: str = "#e8f4f8"
    note_border: str = "#3498db"
    warning_bg: str = "#fdf2e9"
    warning_border: str = "#e67e22"
    tip_bg: str = "#eafaf1"
    tip_border: str = "#27ae60"

    # Fonts
    body_font: str = "Georgia, 'Times New Roman', serif"
    code_font: str = "'Consolas', 'Courier New', monospace"
    heading_font: str = "'Segoe UI', 'Helvetica Neue', Arial, sans-serif"

    # Sizes
    body_font_size: int = 16
    code_font_size: int = 14
    h1_font_size: int = 28
    h2_font_size: int = 22
    h3_font_size: int = 18
    line_height: float = 1.7

    # Button
    button_bg: str = "#3498db"
    button_text: str = "#ffffff"
    button_hover: str = "#2980b9"


LIGHT_THEME = ReaderTheme()

DARK_THEME = ReaderTheme(
    bg_color="#1e1e2e",
    text_color="#cdd6f4",
    h1_color="#cba6f7",
    h2_color="#89b4fa",
    h3_color="#74c7ec",
    code_bg="#181825",
    code_text="#cdd6f4",
    code_border="#45475a",
    note_bg="#1e1e2e",
    note_border="#89b4fa",
    warning_bg="#1e1e2e",
    warning_border="#fab387",
    tip_bg="#1e1e2e",
    tip_border="#a6e3a1",
    button_bg="#89b4fa",
    button_text="#1e1e2e",
    button_hover="#74c7ec",
)


def get_theme(name: str = "light") -> ReaderTheme:
    """Get a reader theme by name."""
    if name == "dark":
        return DARK_THEME
    return LIGHT_THEME
