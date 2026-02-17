"""Reader display theme configuration.

Colors are derived from the centralized ThemePalette in theme_registry.py.
"""

from __future__ import annotations

from dataclasses import dataclass

from pylearn.ui.theme_registry import get_palette, ThemePalette


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


def _theme_from_palette(p: ThemePalette) -> ReaderTheme:
    """Generate a ReaderTheme from a centralized palette."""
    return ReaderTheme(
        bg_color=p.bg, text_color=p.text,
        h1_color=p.h1, h2_color=p.h2, h3_color=p.h3,
        code_bg=p.code_bg, code_text=p.code_text, code_border=p.code_border,
        note_bg=p.note_bg, note_border=p.note_border,
        warning_bg=p.warning_bg, warning_border=p.warning_border,
        tip_bg=p.tip_bg, tip_border=p.tip_border,
        button_bg=p.accent, button_text=p.accent_text, button_hover=p.accent_hover,
    )


def get_theme(name: str = "light") -> ReaderTheme:
    """Get a reader theme by name, derived from the centralized palette."""
    return _theme_from_palette(get_palette(name))
