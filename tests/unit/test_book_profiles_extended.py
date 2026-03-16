"""Extended tests for book_profiles — get_profile, get_auto_profile, profile definitions."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from pylearn.parser.book_profiles import (
    CPP_GENERIC,
    CPP_PRIMER,
    EFFECTIVE_CPP,
    LEARNING_PYTHON,
    PROFILES,
    PROGRAMMING_PYTHON,
    PYTHON_COOKBOOK,
    BookProfile,
    get_auto_profile,
    get_profile,
)

# ===========================================================================
# get_profile
# ===========================================================================


class TestGetProfile:
    def test_known_profile(self):
        p = get_profile("learning_python")
        assert p is LEARNING_PYTHON
        assert p.name == "learning_python"

    def test_unknown_profile_returns_default(self):
        p = get_profile("nonexistent_book")
        assert p.name == "nonexistent_book"
        assert p.heading1_min_size == 18.0  # default value

    def test_all_profiles_in_dict(self):
        assert "learning_python" in PROFILES
        assert "python_cookbook" in PROFILES
        assert "programming_python" in PROFILES
        assert "cpp_generic" in PROFILES
        assert "cpp_primer" in PROFILES
        assert "effective_cpp" in PROFILES


# ===========================================================================
# get_auto_profile
# ===========================================================================


class TestGetAutoProfile:
    @patch("pylearn.parser.font_analyzer.FontAnalyzer")
    def test_delegates_to_font_analyzer(self, MockAnalyzer):
        mock_instance = MockAnalyzer.return_value
        expected = BookProfile(name="auto_detected")
        mock_instance.build_profile.return_value = expected

        result = get_auto_profile("/path/to/book.pdf", language="cpp")

        MockAnalyzer.assert_called_once_with("/path/to/book.pdf")
        mock_instance.build_profile.assert_called_once_with("cpp")
        assert result is expected


# ===========================================================================
# Profile definitions validation
# ===========================================================================


class TestProfileDefinitions:
    @pytest.mark.parametrize(
        "profile",
        [LEARNING_PYTHON, PYTHON_COOKBOOK, PROGRAMMING_PYTHON, CPP_GENERIC, CPP_PRIMER, EFFECTIVE_CPP],
        ids=lambda p: p.name,
    )
    def test_heading_thresholds_ordered(self, profile):
        assert profile.heading1_min_size >= profile.heading2_min_size >= profile.heading3_min_size

    @pytest.mark.parametrize(
        "profile",
        [LEARNING_PYTHON, PYTHON_COOKBOOK, PROGRAMMING_PYTHON, CPP_GENERIC, CPP_PRIMER, EFFECTIVE_CPP],
        ids=lambda p: p.name,
    )
    def test_body_smaller_than_heading3(self, profile):
        assert profile.body_size < profile.heading3_min_size

    def test_cpp_profiles_have_cpp_language(self):
        assert CPP_GENERIC.language == "cpp"
        assert CPP_PRIMER.language == "cpp"
        assert EFFECTIVE_CPP.language == "cpp"

    def test_python_profiles_have_python_language(self):
        assert LEARNING_PYTHON.language == "python"
        assert PYTHON_COOKBOOK.language == "python"
        assert PROGRAMMING_PYTHON.language == "python"

    def test_effective_cpp_matches_item_pattern(self):
        import re

        assert re.match(EFFECTIVE_CPP.chapter_pattern, "Item 3: Use const whenever possible")

    def test_all_profiles_have_monospace_fonts(self):
        for name, profile in PROFILES.items():
            assert len(profile.monospace_fonts) > 0, f"{name} has no monospace fonts"


# ===========================================================================
# BookProfile __post_init__ edge cases
# ===========================================================================


class TestBookProfilePostInit:
    def test_reversed_thresholds_auto_fixed(self):
        p = BookProfile(
            name="reversed",
            heading1_min_size=10.0,
            heading2_min_size=15.0,
            heading3_min_size=20.0,
        )
        assert p.heading1_min_size == 20.0
        assert p.heading2_min_size == 15.0
        assert p.heading3_min_size == 10.0

    def test_equal_thresholds_ok(self):
        p = BookProfile(name="equal", heading1_min_size=14.0, heading2_min_size=14.0, heading3_min_size=14.0)
        assert p.heading1_min_size == 14.0

    def test_monospace_fonts_lowered(self):
        p = BookProfile(name="test", monospace_fonts=["Courier", "CONSOLAS", "DejaVuSansMono"])
        assert p._mono_lower == ["courier", "consolas", "dejavusansmono"]

    def test_is_monospace_caching(self):
        p = BookProfile(name="test")
        # First call populates cache
        result1 = p.is_monospace("CourierNew")
        # Second call should hit cache
        result2 = p.is_monospace("CourierNew")
        assert result1 is True
        assert result2 is True
        assert "CourierNew" in p._mono_cache

    def test_empty_font_name_not_monospace(self):
        p = BookProfile(name="test")
        assert p.is_monospace("") is False
