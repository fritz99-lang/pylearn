# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Consolidated theme system — single source of truth for all color values.

Each ThemePalette defines base colors that are used to generate:
- QSS stylesheets (for QMainWindow, menus, buttons, etc.)
- ReaderTheme (for HTML renderer)
- Editor colors (for QScintilla lexers)
- Console stylesheet
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ThemePalette:
    """Base color palette that all component themes derive from."""
    name: str

    # Core background/foreground
    bg: str
    bg_alt: str       # secondary bg (panels, inputs)
    text: str
    text_muted: str   # secondary text (status, comments)
    border: str

    # Accent colors
    accent: str       # primary accent (links, selections, highlights)
    accent_hover: str
    accent_text: str  # text on accent background

    # Headings
    h1: str
    h2: str
    h3: str

    # Code blocks (reader)
    code_bg: str
    code_text: str
    code_border: str

    # Callout boxes
    note_bg: str
    note_border: str
    warning_bg: str
    warning_border: str
    tip_bg: str
    tip_border: str

    # Syntax highlighting — shared across editor and reader
    syn_comment: str
    syn_keyword: str
    syn_number: str
    syn_string: str
    syn_class: str
    syn_func: str
    syn_decorator: str    # Python decorator / C++ preprocessor
    syn_operator: str


LIGHT = ThemePalette(
    name="light",
    bg="#ffffff", bg_alt="#f5f5f5", text="#333333", text_muted="#888888",
    border="#dddddd",
    accent="#3498db", accent_hover="#2980b9", accent_text="#ffffff",
    h1="#1a1a2e", h2="#16213e", h3="#0f3460",
    code_bg="#272822", code_text="#f8f8f2", code_border="#444444",
    note_bg="#e8f4f8", note_border="#3498db",
    warning_bg="#fdf2e9", warning_border="#e67e22",
    tip_bg="#eafaf1", tip_border="#27ae60",
    syn_comment="#008000", syn_keyword="#0000ff", syn_number="#ff0000",
    syn_string="#ba2121", syn_class="#0000ff", syn_func="#0000ff",
    syn_decorator="#aa22ff", syn_operator="#000000",
)

DARK = ThemePalette(
    name="dark",
    bg="#1e1e2e", bg_alt="#181825", text="#cdd6f4", text_muted="#6c7086",
    border="#45475a",
    accent="#b4befe", accent_hover="#94e2d5", accent_text="#1e1e2e",
    h1="#cba6f7", h2="#b4befe", h3="#94e2d5",
    code_bg="#181825", code_text="#cdd6f4", code_border="#45475a",
    note_bg="#1e1e2e", note_border="#b4befe",
    warning_bg="#1e1e2e", warning_border="#fab387",
    tip_bg="#1e1e2e", tip_border="#a6e3a1",
    syn_comment="#6c7086", syn_keyword="#a6e3a1", syn_number="#f38ba8",
    syn_string="#fab387", syn_class="#b4befe", syn_func="#b4befe",
    syn_decorator="#cba6f7", syn_operator="#94e2d5",
)

SEPIA = ThemePalette(
    name="sepia",
    bg="#f4ecd8", bg_alt="#efe6d0", text="#5b4636", text_muted="#9c8b74",
    border="#d4c5a9",
    accent="#7a5b10", accent_hover="#6b4e0d", accent_text="#faf6ee",
    h1="#6b3a2a", h2="#6b4422", h3="#7a5b10",
    code_bg="#efe6d0", code_text="#5b4636", code_border="#d4c5a9",
    note_bg="#eae1cb", note_border="#8b6914",
    warning_bg="#f0e0c0", warning_border="#b8860b",
    tip_bg="#e5e0c8", tip_border="#6b8e23",
    syn_comment="#9c8b74", syn_keyword="#8b6914", syn_number="#b85c3c",
    syn_string="#a0522d", syn_class="#6b3a2a", syn_func="#6b3a2a",
    syn_decorator="#7a5230", syn_operator="#5b4636",
)

PALETTES: dict[str, ThemePalette] = {
    "light": LIGHT,
    "dark": DARK,
    "sepia": SEPIA,
}


def get_palette(name: str = "light") -> ThemePalette:
    """Get a theme palette by name."""
    return PALETTES.get(name, LIGHT)
