"""Tests for theme_registry and styles — theme palettes and QSS generation.

ThemePalette and get_palette are pure Python (no Qt needed).
QSS generation tests verify correct color substitution.
"""

from __future__ import annotations

import pytest

from pylearn.ui.styles import _generate_qss, get_stylesheet
from pylearn.ui.theme_registry import DARK, LIGHT, PALETTES, SEPIA, get_palette

# ===========================================================================
# ThemePalette
# ===========================================================================


class TestThemePalette:
    def test_light_palette_exists(self):
        assert LIGHT.name == "light"
        assert LIGHT.bg.startswith("#")

    def test_dark_palette_exists(self):
        assert DARK.name == "dark"
        assert DARK.bg.startswith("#")

    def test_sepia_palette_exists(self):
        assert SEPIA.name == "sepia"
        assert SEPIA.bg.startswith("#")

    def test_palettes_are_frozen(self):
        with pytest.raises(AttributeError):
            LIGHT.bg = "#000000"

    def test_all_palettes_have_required_colors(self):
        required = [
            "bg",
            "bg_alt",
            "text",
            "text_muted",
            "border",
            "accent",
            "h1",
            "h2",
            "h3",
            "code_bg",
            "code_text",
            "syn_keyword",
        ]
        for name, palette in PALETTES.items():
            for field in required:
                val = getattr(palette, field)
                assert val, f"{name}.{field} is empty"

    def test_palettes_dict_complete(self):
        assert set(PALETTES.keys()) == {"light", "dark", "sepia"}


# ===========================================================================
# get_palette
# ===========================================================================


class TestGetPalette:
    def test_known_theme(self):
        assert get_palette("dark") is DARK
        assert get_palette("sepia") is SEPIA
        assert get_palette("light") is LIGHT

    def test_unknown_theme_defaults_to_light(self):
        assert get_palette("neon") is LIGHT

    def test_default_is_light(self):
        assert get_palette() is LIGHT


# ===========================================================================
# QSS Generation
# ===========================================================================


class TestQSSGeneration:
    def test_generate_qss_contains_colors(self):
        qss = _generate_qss(LIGHT)
        assert LIGHT.bg in qss
        assert LIGHT.text in qss
        assert LIGHT.border in qss
        assert LIGHT.accent in qss

    def test_generate_qss_contains_selectors(self):
        qss = _generate_qss(DARK)
        assert "QMainWindow" in qss
        assert "QTreeWidget" in qss
        assert "QPushButton" in qss
        assert "QMenuBar" in qss
        assert "QToolBar" in qss
        assert "QComboBox" in qss

    def test_get_stylesheet_light(self):
        qss = get_stylesheet("light")
        assert LIGHT.bg in qss

    def test_get_stylesheet_dark(self):
        qss = get_stylesheet("dark")
        assert DARK.bg in qss

    def test_get_stylesheet_sepia(self):
        qss = get_stylesheet("sepia")
        assert SEPIA.bg in qss

    def test_get_stylesheet_unknown_falls_back_to_light(self):
        qss = get_stylesheet("unknown")
        assert LIGHT.bg in qss

    def test_light_menu_uses_bg(self):
        """Light theme menubar uses bg (not bg_alt) — special case in code."""
        qss = _generate_qss(LIGHT)
        # The menubar background line should contain LIGHT.bg
        assert f"background-color: {LIGHT.bg}" in qss

    def test_dark_menu_uses_bg_alt(self):
        """Dark theme menubar uses bg_alt — special case in code."""
        qss = _generate_qss(DARK)
        assert f"background-color: {DARK.bg_alt}" in qss
