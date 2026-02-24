# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Tests for FontAnalyzer and BookProfile.is_monospace caching."""

from __future__ import annotations

from collections import Counter
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from pylearn.parser.book_profiles import BookProfile
from pylearn.parser.font_analyzer import FontAnalyzer, _is_mono

# ---------------------------------------------------------------------------
# Helpers for building mock PDF data
# ---------------------------------------------------------------------------


def _make_span(
    text: str,
    font: str = "Serif",
    size: float = 10.0,
    flags: int = 0,
    bbox: tuple[float, float, float, float] = (54, 100, 400, 112),
) -> dict[str, Any]:
    """Create a single PyMuPDF-style span dict."""
    return {"text": text, "font": font, "size": size, "flags": flags, "bbox": bbox}


def _make_page_dict(spans: list[dict[str, Any]]) -> dict[str, Any]:
    """Wrap a list of spans into the PyMuPDF 'dict' text extraction format."""
    lines = [{"spans": [s]} for s in spans]
    return {"blocks": [{"type": 0, "lines": lines}]}


def _build_mock_doc(
    pages: list[dict[str, Any]],
    page_height: float = 792.0,
    front_texts: list[str] | None = None,
    back_texts: list[str] | None = None,
) -> MagicMock:
    """Build a mock fitz.Document with controlled page content.

    Args:
        pages: list of page dicts (from _make_page_dict) for sampled content pages.
        page_height: simulated page height.
        front_texts: optional full-page texts for skip-page detection (first N pages).
        back_texts: optional full-page texts for skip-page detection (last N pages).
    """
    doc = MagicMock()
    total = len(pages)
    if front_texts:
        total = max(total, len(front_texts))
    if back_texts:
        total = max(total, 50)  # ensure we have "back" pages

    doc.__len__ = MagicMock(return_value=total)

    def _getitem(idx: int) -> MagicMock:
        page = MagicMock()
        # Provide page.rect.height
        page.rect.height = page_height

        # get_text("dict", ...) — used by _analyze histogram building
        if idx < len(pages):
            page.get_text = MagicMock(side_effect=lambda fmt="text", **kw: pages[idx] if fmt == "dict" else "")
        else:
            page.get_text = MagicMock(return_value="" if True else {})

        # get_text() with no args — used by _detect_skip_pages for keyword scanning
        if front_texts and idx < len(front_texts):
            page.get_text = MagicMock(
                side_effect=lambda fmt="text", **kw: pages[idx] if fmt == "dict" else front_texts[idx]
            )
        elif back_texts and idx >= total - len(back_texts):
            offset = idx - (total - len(back_texts))
            page.get_text = MagicMock(side_effect=lambda fmt="text", **kw: {} if fmt == "dict" else back_texts[offset])

        return page

    doc.__getitem__ = MagicMock(side_effect=_getitem)
    return doc


# ---------------------------------------------------------------------------
# _is_mono module-level helper
# ---------------------------------------------------------------------------


class TestIsMono:
    """Tests for the _is_mono() free function."""

    @pytest.mark.parametrize(
        "font_name",
        [
            "Courier",
            "CourierNew",
            "DejaVuSansMono",
            "Consolas",
            "Menlo-Regular",
            "SourceCodePro-Bold",
            "Inconsolata",
            "FiraCode-Retina",
            "UbuntuMono",
            "RobotoMono-Medium",
            "LiberationMono",
            "DroidSansMono",
        ],
    )
    def test_monospace_fonts_detected(self, font_name: str) -> None:
        assert _is_mono(font_name) is True

    @pytest.mark.parametrize(
        "font_name",
        [
            "TimesNewRoman",
            "Helvetica",
            "Arial",
            "Georgia",
            "Palatino",
            "Garamond",
            "Cambria",
        ],
    )
    def test_proportional_fonts_rejected(self, font_name: str) -> None:
        assert _is_mono(font_name) is False

    def test_empty_string(self) -> None:
        assert _is_mono("") is False

    def test_case_insensitive(self) -> None:
        assert _is_mono("COURIER") is True
        assert _is_mono("courier") is True


# ---------------------------------------------------------------------------
# BookProfile.is_monospace — caching behavior
# ---------------------------------------------------------------------------


class TestBookProfileIsMonospace:
    """Tests for BookProfile.is_monospace() and its internal cache."""

    def test_known_monospace_fonts_return_true(self) -> None:
        profile = BookProfile(name="test")
        assert profile.is_monospace("Courier") is True
        assert profile.is_monospace("Consolas-Bold") is True
        assert profile.is_monospace("DejaVuSansMono") is True
        assert profile.is_monospace("Ubuntu Mono") is True

    def test_known_proportional_fonts_return_false(self) -> None:
        profile = BookProfile(name="test")
        assert profile.is_monospace("TimesNewRoman") is False
        assert profile.is_monospace("Helvetica") is False
        assert profile.is_monospace("Arial") is False

    def test_empty_font_name_returns_false(self) -> None:
        profile = BookProfile(name="test")
        assert profile.is_monospace("") is False

    def test_cache_returns_same_result(self) -> None:
        """Second call for the same font should use cache (same result)."""
        profile = BookProfile(name="test")
        first = profile.is_monospace("Courier")
        second = profile.is_monospace("Courier")
        assert first is second is True

    def test_cache_populated_after_first_call(self) -> None:
        profile = BookProfile(name="test")
        assert "SomeRareFont" not in profile._mono_cache
        profile.is_monospace("SomeRareFont")
        assert "SomeRareFont" in profile._mono_cache

    def test_different_fonts_cached_independently(self) -> None:
        profile = BookProfile(name="test")
        profile.is_monospace("Courier")
        profile.is_monospace("Helvetica")
        assert profile._mono_cache["Courier"] is True
        assert profile._mono_cache["Helvetica"] is False

    def test_custom_monospace_fonts_list(self) -> None:
        """A custom monospace_fonts list should be honored."""
        profile = BookProfile(name="test", monospace_fonts=["MyCustomMono"])
        assert profile.is_monospace("MyCustomMono-Regular") is True
        assert profile.is_monospace("Courier") is False  # not in custom list


# ---------------------------------------------------------------------------
# FontAnalyzer._pick_sample_pages
# ---------------------------------------------------------------------------


class TestPickSamplePages:
    """Tests for the static _pick_sample_pages method."""

    def test_small_document_returns_all(self) -> None:
        result = FontAnalyzer._pick_sample_pages(10, target=40)
        assert result == list(range(10))

    def test_exact_target(self) -> None:
        result = FontAnalyzer._pick_sample_pages(40, target=40)
        assert result == list(range(40))

    def test_large_document_returns_target_count(self) -> None:
        result = FontAnalyzer._pick_sample_pages(400, target=40)
        assert len(result) <= 40
        # Evenly distributed
        assert result[0] == 0
        assert result[-1] < 400

    def test_zero_pages(self) -> None:
        result = FontAnalyzer._pick_sample_pages(0, target=40)
        assert result == []

    def test_one_page(self) -> None:
        result = FontAnalyzer._pick_sample_pages(1, target=40)
        assert result == [0]


# ---------------------------------------------------------------------------
# FontAnalyzer._find_body_font
# ---------------------------------------------------------------------------


class TestFindBodyFont:
    """Tests for the static _find_body_font method."""

    def test_most_frequent_non_mono(self) -> None:
        histogram: Counter[tuple[str, float, bool, bool]] = Counter()
        histogram[("Serif", 10.0, False, False)] = 5000
        histogram[("Courier", 9.0, False, True)] = 2000
        histogram[("Serif", 14.0, True, False)] = 500
        font, size = FontAnalyzer._find_body_font(histogram)
        assert font == "Serif"
        assert size == 10.0

    def test_fallback_to_mono_when_no_non_mono(self) -> None:
        """If only monospace fonts exist, fall back to the most common one."""
        histogram: Counter[tuple[str, float, bool, bool]] = Counter()
        histogram[("Courier", 10.0, False, True)] = 3000
        histogram[("Menlo", 9.0, False, True)] = 1000
        font, size = FontAnalyzer._find_body_font(histogram)
        assert font == "Courier"
        assert size == 10.0

    def test_empty_histogram(self) -> None:
        histogram: Counter[tuple[str, float, bool, bool]] = Counter()
        font, size = FontAnalyzer._find_body_font(histogram)
        assert font == "unknown"
        assert size == 10.0


# ---------------------------------------------------------------------------
# FontAnalyzer._find_code_size
# ---------------------------------------------------------------------------


class TestFindCodeSize:
    """Tests for the static _find_code_size method."""

    def test_most_frequent_mono_size(self) -> None:
        histogram: Counter[tuple[str, float, bool, bool]] = Counter()
        histogram[("Courier", 8.5, False, True)] = 3000
        histogram[("Courier", 7.0, False, True)] = 500
        histogram[("Serif", 10.0, False, False)] = 5000
        result = FontAnalyzer._find_code_size(histogram, body_size=10.0)
        assert result == 8.5

    def test_no_mono_fallback(self) -> None:
        """When no monospace fonts exist, guess body_size - 1.5."""
        histogram: Counter[tuple[str, float, bool, bool]] = Counter()
        histogram[("Serif", 10.0, False, False)] = 5000
        result = FontAnalyzer._find_code_size(histogram, body_size=10.0)
        assert result == 8.5

    def test_no_mono_fallback_minimum(self) -> None:
        """Fallback should not go below 6.0."""
        histogram: Counter[tuple[str, float, bool, bool]] = Counter()
        histogram[("Serif", 7.0, False, False)] = 5000
        result = FontAnalyzer._find_code_size(histogram, body_size=7.0)
        assert result == 6.0


# ---------------------------------------------------------------------------
# FontAnalyzer._compute_heading_thresholds
# ---------------------------------------------------------------------------


class TestComputeHeadingThresholds:
    """Tests for the static heading threshold computation."""

    def test_three_tiers(self) -> None:
        """Three distinct heading sizes produce three tiers."""
        histogram: Counter[tuple[str, float, bool, bool]] = Counter()
        histogram[("Serif", 10.0, False, False)] = 5000  # body
        histogram[("Serif", 24.0, True, False)] = 200  # h1
        histogram[("Serif", 16.0, True, False)] = 400  # h2
        histogram[("Serif", 13.0, True, False)] = 300  # h3
        h1_min, h2_min, h3_min = FontAnalyzer._compute_heading_thresholds(histogram, 10.0)
        # h1 threshold between 24 and 16
        assert 16.0 < h1_min < 24.0
        # h2 threshold between 16 and 13
        assert 13.0 < h2_min < 16.0
        # h3 threshold between 13 and body(10)
        assert 10.0 < h3_min < 13.0
        # Ordering: h1 > h2 > h3
        assert h1_min > h2_min > h3_min

    def test_two_tiers(self) -> None:
        histogram: Counter[tuple[str, float, bool, bool]] = Counter()
        histogram[("Serif", 10.0, False, False)] = 5000
        histogram[("Serif", 20.0, True, False)] = 200
        histogram[("Serif", 14.0, True, False)] = 300
        h1_min, h2_min, h3_min = FontAnalyzer._compute_heading_thresholds(histogram, 10.0)
        assert h1_min > h2_min > h3_min
        assert h1_min > 14.0
        assert h3_min == 11.0  # body + 1

    def test_one_tier(self) -> None:
        histogram: Counter[tuple[str, float, bool, bool]] = Counter()
        histogram[("Serif", 10.0, False, False)] = 5000
        histogram[("Serif", 18.0, True, False)] = 200
        h1_min, h2_min, h3_min = FontAnalyzer._compute_heading_thresholds(histogram, 10.0)
        assert h1_min > h2_min > h3_min
        assert h2_min == 12.0  # body + 2
        assert h3_min == 11.0  # body + 1

    def test_no_large_sizes_defaults(self) -> None:
        """When there are no sizes larger than body, use defaults."""
        histogram: Counter[tuple[str, float, bool, bool]] = Counter()
        histogram[("Serif", 10.0, False, False)] = 5000
        h1_min, h2_min, h3_min = FontAnalyzer._compute_heading_thresholds(histogram, 10.0)
        assert h1_min == 18.0  # body + 8
        assert h2_min == 14.0  # body + 4
        assert h3_min == 12.0  # body + 2

    def test_rare_sizes_filtered(self) -> None:
        """Sizes with < 50 chars are filtered as decorative artifacts."""
        histogram: Counter[tuple[str, float, bool, bool]] = Counter()
        histogram[("Serif", 10.0, False, False)] = 5000
        histogram[("Serif", 30.0, True, False)] = 20  # rare, should be filtered
        histogram[("Serif", 16.0, True, False)] = 200  # real heading
        h1_min, _h2_min, _h3_min = FontAnalyzer._compute_heading_thresholds(histogram, 10.0)
        # Only one real tier (16.0), size 30 was filtered.
        # With one tier: h1_min = (16 + 10) / 2 = 13.0
        assert h1_min == 13.0

    def test_close_sizes_merged(self) -> None:
        """Sizes within 1pt of each other are merged into one tier."""
        histogram: Counter[tuple[str, float, bool, bool]] = Counter()
        histogram[("Serif", 10.0, False, False)] = 5000
        histogram[("Serif", 16.0, True, False)] = 200
        histogram[("Serif", 15.5, False, False)] = 200  # within 1pt of 16.0
        h1_min, _h2_min, _h3_min = FontAnalyzer._compute_heading_thresholds(histogram, 10.0)
        # Should be treated as a single tier
        assert h1_min == 13.0  # (16 + 10) / 2


# ---------------------------------------------------------------------------
# FontAnalyzer._detect_margins
# ---------------------------------------------------------------------------


class TestDetectMargins:
    """Tests for the static _detect_margins method."""

    def test_empty_y_positions(self) -> None:
        doc = MagicMock()
        result = FontAnalyzer._detect_margins([], doc, [])
        assert result == (50.0, 50.0)

    def test_no_header_footer_text(self) -> None:
        """When text only appears in the middle of the page, defaults apply."""
        doc = MagicMock()
        page = MagicMock()
        page.rect.height = 792.0
        doc.__getitem__ = MagicMock(return_value=page)

        # Y positions in the middle of the page (not in top/bottom 15%)
        # top_zone = 792 * 0.15 = 118.8, bottom_zone = 792 * 0.85 = 673.2
        y_positions = [[200.0, 300.0, 400.0, 500.0]] * 5
        result = FontAnalyzer._detect_margins(y_positions, doc, [0])
        assert result == (50.0, 50.0)

    def test_consistent_header_detected(self) -> None:
        """Text appearing at the top of 50%+ pages should increase margin_top."""
        doc = MagicMock()
        page = MagicMock()
        page.rect.height = 792.0
        doc.__getitem__ = MagicMock(return_value=page)

        # Y=30 is in the top zone (< 118.8), appearing on all 10 pages
        y_positions = [[30.0, 200.0, 400.0]] * 10
        result = FontAnalyzer._detect_margins(y_positions, doc, [0])
        margin_top, margin_bottom = result
        # bin = 30 // 5 = 6, candidate = (6+1)*5 + 5 = 40
        assert margin_top >= 40.0
        assert margin_bottom == 50.0

    def test_margins_capped_at_90(self) -> None:
        """Margins should not exceed 90."""
        doc = MagicMock()
        page = MagicMock()
        page.rect.height = 792.0
        doc.__getitem__ = MagicMock(return_value=page)

        # Y=100 in top zone, many pages
        y_positions = [[100.0]] * 20
        result = FontAnalyzer._detect_margins(y_positions, doc, [0])
        margin_top, _ = result
        assert margin_top <= 90.0


# ---------------------------------------------------------------------------
# FontAnalyzer._detect_skip_pages
# ---------------------------------------------------------------------------


class TestDetectSkipPages:
    """Tests for the static _detect_skip_pages method."""

    def test_no_keywords(self) -> None:
        """No front/back matter keywords should yield (0, 0)."""
        doc = MagicMock()
        doc.__len__ = MagicMock(return_value=100)

        page = MagicMock()
        page.get_text = MagicMock(return_value="some random content")
        doc.__getitem__ = MagicMock(return_value=page)

        skip_start, skip_end = FontAnalyzer._detect_skip_pages(doc)
        assert skip_start == 0
        assert skip_end == 0

    def test_front_matter_detected(self) -> None:
        doc = MagicMock()
        doc.__len__ = MagicMock(return_value=200)

        def _getitem(idx: int) -> MagicMock:
            page = MagicMock()
            if idx == 0:
                page.get_text = MagicMock(return_value="Copyright 2026")
            elif idx == 1:
                page.get_text = MagicMock(return_value="Table of Contents")
            elif idx == 3:
                page.get_text = MagicMock(return_value="Preface and acknowledgments")
            else:
                page.get_text = MagicMock(return_value="regular content")
            return page

        doc.__getitem__ = MagicMock(side_effect=_getitem)

        skip_start, skip_end = FontAnalyzer._detect_skip_pages(doc)
        # Page 3 has "preface" -> skip_start = max(pg+1) = 4
        # But capped at max(2, 200//15) = max(2, 13) = 13
        assert skip_start == 4
        assert skip_end == 0

    def test_back_matter_detected(self) -> None:
        doc = MagicMock()
        total = 100
        doc.__len__ = MagicMock(return_value=total)

        def _getitem(idx: int) -> MagicMock:
            page = MagicMock()
            if idx == 95:
                page.get_text = MagicMock(return_value="Appendix A: Reference")
            elif idx == 98:
                page.get_text = MagicMock(return_value="Index of terms")
            else:
                page.get_text = MagicMock(return_value="content")
            return page

        doc.__getitem__ = MagicMock(side_effect=_getitem)

        skip_start, skip_end = FontAnalyzer._detect_skip_pages(doc)
        assert skip_start == 0
        # Page 95 has "appendix" -> skip_end = total - 95 = 5
        # Page 98 has "index" -> skip_end = max(5, total - 98) = max(5, 2) = 5
        assert skip_end == 5

    def test_skip_start_capped(self) -> None:
        """skip_start is capped at ~7% of total pages."""
        doc = MagicMock()
        doc.__len__ = MagicMock(return_value=50)

        def _getitem(idx: int) -> MagicMock:
            page = MagicMock()
            if idx == 14:
                # Page 14 has "preface" -> would set skip_start=15
                page.get_text = MagicMock(return_value="Preface text here")
            else:
                page.get_text = MagicMock(return_value="content")
            return page

        doc.__getitem__ = MagicMock(side_effect=_getitem)

        skip_start, _ = FontAnalyzer._detect_skip_pages(doc)
        # Cap = max(2, 50//15) = max(2, 3) = 3
        assert skip_start <= 3


# ---------------------------------------------------------------------------
# FontAnalyzer.build_profile — integration with mocked fitz
# ---------------------------------------------------------------------------


class TestBuildProfile:
    """Tests for the full build_profile flow with mocked PDF."""

    @patch("pylearn.parser.font_analyzer.fitz")
    def test_returns_profile_with_detected_values(self, mock_fitz: MagicMock) -> None:
        """A well-formed mock PDF should produce a profile with auto-detected values."""
        # Build page data: body text in Serif 10pt, code in Courier 8.5pt, heading in Serif 18pt
        body_span = _make_span("x" * 200, font="Serif", size=10.0)
        code_span = _make_span("y" * 80, font="CourierNew", size=8.5)
        heading_span = _make_span("Chapter Title" * 5, font="Serif", size=18.0, flags=16)

        page_data = _make_page_dict([body_span, code_span, heading_span])

        # Build mock document
        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=5)
        mock_doc.close = MagicMock()

        def _getitem(idx: int) -> MagicMock:
            page = MagicMock()
            page.rect.height = 792.0
            page.get_text = MagicMock(
                side_effect=lambda fmt="text", **kw: page_data if fmt == "dict" else "regular content"
            )
            return page

        mock_doc.__getitem__ = MagicMock(side_effect=_getitem)
        mock_fitz.open = MagicMock(return_value=mock_doc)
        mock_fitz.TEXT_PRESERVE_WHITESPACE = 1

        analyzer = FontAnalyzer("/fake/book.pdf")
        profile = analyzer.build_profile(language="python")

        assert profile.name == "auto"
        assert profile.language == "python"
        assert profile.body_size == 10.0
        assert profile.code_size == 8.5
        # Heading thresholds should be between body and heading sizes
        assert profile.heading1_min_size > 10.0

    @patch("pylearn.parser.font_analyzer.fitz")
    def test_analysis_failure_returns_default(self, mock_fitz: MagicMock) -> None:
        """When _analyze raises an exception, build_profile returns a default profile."""
        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(side_effect=RuntimeError("corrupt PDF"))
        mock_doc.close = MagicMock()
        mock_fitz.open = MagicMock(return_value=mock_doc)

        analyzer = FontAnalyzer("/fake/broken.pdf")
        profile = analyzer.build_profile(language="cpp")

        assert profile.name == "auto"
        assert profile.language == "cpp"
        # Should be default values
        assert profile.heading1_min_size == 18.0

    @patch("pylearn.parser.font_analyzer.fitz")
    def test_empty_pdf_returns_default(self, mock_fitz: MagicMock) -> None:
        """A PDF with no text on any page should return the default profile."""
        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=3)
        mock_doc.close = MagicMock()

        def _getitem(idx: int) -> MagicMock:
            page = MagicMock()
            page.rect.height = 792.0
            empty_page = {"blocks": []}
            page.get_text = MagicMock(side_effect=lambda fmt="text", **kw: empty_page if fmt == "dict" else "")
            return page

        mock_doc.__getitem__ = MagicMock(side_effect=_getitem)
        mock_fitz.open = MagicMock(return_value=mock_doc)
        mock_fitz.TEXT_PRESERVE_WHITESPACE = 1

        analyzer = FontAnalyzer("/fake/empty.pdf")
        profile = analyzer.build_profile()

        assert profile.name == "auto"
        assert profile.body_size == 10.0  # default

    @patch("pylearn.parser.font_analyzer.fitz")
    def test_doc_closed_after_success(self, mock_fitz: MagicMock) -> None:
        """The document should be closed even on success."""
        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=1)
        mock_doc.close = MagicMock()

        body_span = _make_span("x" * 200, font="Serif", size=10.0)
        page_data = _make_page_dict([body_span])

        def _getitem(idx: int) -> MagicMock:
            page = MagicMock()
            page.rect.height = 792.0
            page.get_text = MagicMock(side_effect=lambda fmt="text", **kw: page_data if fmt == "dict" else "content")
            return page

        mock_doc.__getitem__ = MagicMock(side_effect=_getitem)
        mock_fitz.open = MagicMock(return_value=mock_doc)
        mock_fitz.TEXT_PRESERVE_WHITESPACE = 1

        analyzer = FontAnalyzer("/fake/book.pdf")
        analyzer.build_profile()

        mock_doc.close.assert_called_once()

    @patch("pylearn.parser.font_analyzer.fitz")
    def test_doc_closed_after_failure(self, mock_fitz: MagicMock) -> None:
        """The document should be closed even when _analyze fails."""
        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(side_effect=RuntimeError("boom"))
        mock_doc.close = MagicMock()
        mock_fitz.open = MagicMock(return_value=mock_doc)

        analyzer = FontAnalyzer("/fake/book.pdf")
        analyzer.build_profile()

        mock_doc.close.assert_called_once()


# ---------------------------------------------------------------------------
# BookProfile.__post_init__ — threshold reordering
# ---------------------------------------------------------------------------


class TestBookProfilePostInit:
    """Tests for BookProfile's __post_init__ validation."""

    def test_reversed_thresholds_auto_fixed(self) -> None:
        """If heading thresholds are provided out of order, they are sorted."""
        profile = BookProfile(
            name="test",
            heading1_min_size=10.0,
            heading2_min_size=14.0,
            heading3_min_size=18.0,
        )
        assert profile.heading1_min_size == 18.0
        assert profile.heading2_min_size == 14.0
        assert profile.heading3_min_size == 10.0

    def test_correct_order_unchanged(self) -> None:
        profile = BookProfile(
            name="test",
            heading1_min_size=20.0,
            heading2_min_size=14.0,
            heading3_min_size=12.0,
        )
        assert profile.heading1_min_size == 20.0
        assert profile.heading2_min_size == 14.0
        assert profile.heading3_min_size == 12.0
