"""Tests for PDFParser — PDF text extraction with font metadata.

Mocks fitz (PyMuPDF) to test extraction logic without real PDF files.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from pylearn.parser.book_profiles import BookProfile
from pylearn.parser.pdf_parser import _MAX_IMAGES_PER_BOOK, PDFParser

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_profile(**overrides) -> BookProfile:
    defaults = dict(
        name="test",
        heading1_min_size=20.0,
        heading2_min_size=14.0,
        heading3_min_size=12.0,
        body_size=10.0,
        code_size=8.5,
        margin_top=72.0,
        margin_bottom=72.0,
        skip_pages_start=0,
        skip_pages_end=0,
    )
    defaults.update(overrides)
    return BookProfile(**defaults)


def _make_span(text="Hello", font="Serif", size=10.0, flags=0, color=0, bbox=(100, 200, 300, 250)):
    """Build a fitz-style span dict."""
    return {"text": text, "font": font, "size": size, "flags": flags, "color": color, "bbox": bbox}


def _make_page_dict(spans_data):
    """Build a fitz page.get_text('dict') result from span dicts."""
    lines = [{"spans": spans_data}]
    return {"blocks": [{"type": 0, "lines": lines}]}


def _mock_page(page_dict=None, height=792.0, images=None):
    """Create a mock fitz Page."""
    page = MagicMock()
    page.rect = SimpleNamespace(height=height)
    page.get_text.return_value = page_dict or {"blocks": []}
    page.get_images.return_value = images or []
    page.get_image_rects.return_value = [SimpleNamespace(y0=100.0)]
    return page


def _mock_doc(pages, total=None):
    """Create a mock fitz Document with the given pages."""
    doc = MagicMock()
    total = total or len(pages)
    doc.__len__ = MagicMock(return_value=total)
    doc.__getitem__ = MagicMock(side_effect=lambda i: pages[i])
    doc.close = MagicMock()
    doc.extract_image = MagicMock(return_value=None)
    return doc


# ===========================================================================
# Open / Close / Context Manager
# ===========================================================================


class TestPDFParserLifecycle:
    def test_open_missing_file_raises(self, tmp_path):
        parser = PDFParser(tmp_path / "missing.pdf", _make_profile())
        with pytest.raises(FileNotFoundError, match="PDF not found"):
            parser.open()

    @patch("pylearn.parser.pdf_parser.fitz")
    def test_open_bad_pdf_raises_runtime(self, mock_fitz, tmp_path):
        pdf = tmp_path / "bad.pdf"
        pdf.write_bytes(b"not a pdf")
        mock_fitz.open.side_effect = Exception("corrupt")
        parser = PDFParser(pdf, _make_profile())
        with pytest.raises(RuntimeError, match="Failed to open PDF"):
            parser.open()

    @patch("pylearn.parser.pdf_parser.fitz")
    def test_context_manager(self, mock_fitz, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        doc = _mock_doc([_mock_page()])
        mock_fitz.open.return_value = doc

        with PDFParser(pdf, _make_profile()) as parser:
            assert parser._doc is not None
        doc.close.assert_called_once()

    @patch("pylearn.parser.pdf_parser.fitz")
    def test_close_sets_doc_none(self, mock_fitz, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        doc = _mock_doc([_mock_page()])
        mock_fitz.open.return_value = doc

        parser = PDFParser(pdf, _make_profile())
        parser.open()
        parser.close()
        assert parser._doc is None

    def test_close_when_not_opened_is_noop(self, tmp_path):
        parser = PDFParser(tmp_path / "x.pdf", _make_profile())
        parser.close()  # should not raise

    def test_get_doc_without_open_raises(self, tmp_path):
        parser = PDFParser(tmp_path / "x.pdf", _make_profile())
        with pytest.raises(RuntimeError, match="not opened"):
            parser._get_doc()


# ===========================================================================
# Properties
# ===========================================================================


class TestPDFParserProperties:
    @patch("pylearn.parser.pdf_parser.fitz")
    def test_total_pages(self, mock_fitz, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        pages = [_mock_page() for _ in range(5)]
        mock_fitz.open.return_value = _mock_doc(pages)

        with PDFParser(pdf, _make_profile()) as parser:
            assert parser.total_pages == 5

    @patch("pylearn.parser.pdf_parser.fitz")
    def test_page_height(self, mock_fitz, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        pages = [_mock_page(height=842.0), _mock_page(height=595.0)]
        mock_fitz.open.return_value = _mock_doc(pages)

        with PDFParser(pdf, _make_profile()) as parser:
            assert parser.page_height == 842.0

    @patch("pylearn.parser.pdf_parser.fitz")
    def test_page_height_with_skip_pages(self, mock_fitz, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        pages = [_mock_page(height=100.0), _mock_page(height=200.0), _mock_page(height=842.0)]
        mock_fitz.open.return_value = _mock_doc(pages)

        profile = _make_profile(skip_pages_start=2)
        with PDFParser(pdf, profile) as parser:
            assert parser.page_height == 842.0


# ===========================================================================
# extract_page_spans
# ===========================================================================


class TestExtractPageSpans:
    @patch("pylearn.parser.pdf_parser.fitz")
    def test_basic_span_extraction(self, mock_fitz, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4")

        span = _make_span("Hello World", "Serif", 10.0, flags=0, bbox=(100, 200, 300, 250))
        page = _mock_page(_make_page_dict([span]))
        mock_fitz.open.return_value = _mock_doc([page])
        mock_fitz.TEXT_PRESERVE_WHITESPACE = 1

        with PDFParser(pdf, _make_profile()) as parser:
            spans = parser.extract_page_spans(0)
            assert len(spans) == 1
            assert spans[0].text == "Hello World"
            assert spans[0].font_size == 10.0

    @patch("pylearn.parser.pdf_parser.fitz")
    def test_out_of_range_page_returns_empty(self, mock_fitz, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        mock_fitz.open.return_value = _mock_doc([_mock_page()])

        with PDFParser(pdf, _make_profile()) as parser:
            assert parser.extract_page_spans(-1) == []
            assert parser.extract_page_spans(99) == []

    @patch("pylearn.parser.pdf_parser.fitz")
    def test_empty_text_spans_skipped(self, mock_fitz, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4")

        span = _make_span("   ", "Serif", 10.0, bbox=(100, 200, 300, 250))
        page = _mock_page(_make_page_dict([span]))
        mock_fitz.open.return_value = _mock_doc([page])
        mock_fitz.TEXT_PRESERVE_WHITESPACE = 1

        with PDFParser(pdf, _make_profile()) as parser:
            assert parser.extract_page_spans(0) == []

    @patch("pylearn.parser.pdf_parser.fitz")
    def test_zero_font_size_skipped(self, mock_fitz, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4")

        span = _make_span("Text", "Serif", 0.0, bbox=(100, 200, 300, 250))
        page = _mock_page(_make_page_dict([span]))
        mock_fitz.open.return_value = _mock_doc([page])
        mock_fitz.TEXT_PRESERVE_WHITESPACE = 1

        with PDFParser(pdf, _make_profile()) as parser:
            assert parser.extract_page_spans(0) == []

    @patch("pylearn.parser.pdf_parser.fitz")
    def test_invalid_bbox_skipped(self, mock_fitz, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4")

        # x0 > x1 = invalid
        span = _make_span("Text", "Serif", 10.0, bbox=(300, 200, 100, 250))
        page = _mock_page(_make_page_dict([span]))
        mock_fitz.open.return_value = _mock_doc([page])
        mock_fitz.TEXT_PRESERVE_WHITESPACE = 1

        with PDFParser(pdf, _make_profile()) as parser:
            assert parser.extract_page_spans(0) == []

    @patch("pylearn.parser.pdf_parser.fitz")
    def test_margin_filtering(self, mock_fitz, tmp_path):
        """Spans in the header/footer margin area should be filtered out."""
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4")

        # In top margin (y0=30 < margin_top=72)
        header_span = _make_span("Header", "Serif", 10.0, bbox=(100, 30, 200, 50))
        # In bottom margin (y1=770 > 792-72=720)
        footer_span = _make_span("Footer", "Serif", 10.0, bbox=(100, 750, 200, 770))
        # In content area
        body_span = _make_span("Body text", "Serif", 10.0, bbox=(100, 200, 300, 220))

        page = _mock_page(_make_page_dict([header_span, footer_span, body_span]))
        mock_fitz.open.return_value = _mock_doc([page])
        mock_fitz.TEXT_PRESERVE_WHITESPACE = 1

        with PDFParser(pdf, _make_profile()) as parser:
            spans = parser.extract_page_spans(0)
            assert len(spans) == 1
            assert spans[0].text == "Body text"

    @patch("pylearn.parser.pdf_parser.fitz")
    def test_heading_exempt_from_margin_filter(self, mock_fitz, tmp_path):
        """Large heading-sized text in the margin area should NOT be filtered."""
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4")

        # In top margin but heading-sized (>= heading2_min_size=14)
        heading_span = _make_span("Chapter 1", "Serif", 22.0, flags=16, bbox=(100, 30, 300, 60))
        page = _mock_page(_make_page_dict([heading_span]))
        mock_fitz.open.return_value = _mock_doc([page])
        mock_fitz.TEXT_PRESERVE_WHITESPACE = 1

        with PDFParser(pdf, _make_profile()) as parser:
            spans = parser.extract_page_spans(0)
            assert len(spans) == 1
            assert spans[0].text == "Chapter 1"

    @patch("pylearn.parser.pdf_parser.fitz")
    def test_bold_italic_detection(self, mock_fitz, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4")

        # flags: bit 4 (16) = bold, bit 1 (2) = italic
        bold_span = _make_span("Bold", "Serif", 10.0, flags=16, bbox=(100, 200, 200, 220))
        italic_span = _make_span("Italic", "Serif", 10.0, flags=2, bbox=(100, 230, 200, 250))
        bold_italic_span = _make_span("Both", "Serif", 10.0, flags=18, bbox=(100, 260, 200, 280))

        page = _mock_page(_make_page_dict([bold_span, italic_span, bold_italic_span]))
        mock_fitz.open.return_value = _mock_doc([page])
        mock_fitz.TEXT_PRESERVE_WHITESPACE = 1

        with PDFParser(pdf, _make_profile()) as parser:
            spans = parser.extract_page_spans(0)
            assert len(spans) == 3
            assert spans[0].is_bold is True and spans[0].is_italic is False
            assert spans[1].is_bold is False and spans[1].is_italic is True
            assert spans[2].is_bold is True and spans[2].is_italic is True

    @patch("pylearn.parser.pdf_parser.fitz")
    def test_monospace_detection(self, mock_fitz, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4")

        mono_span = _make_span("code()", "Courier", 9.0, bbox=(100, 200, 300, 220))
        body_span = _make_span("text", "Serif", 10.0, bbox=(100, 230, 300, 250))

        page = _mock_page(_make_page_dict([mono_span, body_span]))
        mock_fitz.open.return_value = _mock_doc([page])
        mock_fitz.TEXT_PRESERVE_WHITESPACE = 1

        with PDFParser(pdf, _make_profile()) as parser:
            spans = parser.extract_page_spans(0)
            assert spans[0].is_monospace is True
            assert spans[1].is_monospace is False

    @patch("pylearn.parser.pdf_parser.fitz")
    def test_non_text_blocks_ignored(self, mock_fitz, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4")

        page_dict = {
            "blocks": [
                {"type": 1, "lines": []},  # image block, not text
                {"type": 0, "lines": [{"spans": [_make_span("Real text", bbox=(100, 200, 300, 220))]}]},
            ]
        }
        page = _mock_page(page_dict)
        mock_fitz.open.return_value = _mock_doc([page])
        mock_fitz.TEXT_PRESERVE_WHITESPACE = 1

        with PDFParser(pdf, _make_profile()) as parser:
            spans = parser.extract_page_spans(0)
            assert len(spans) == 1

    @patch("pylearn.parser.pdf_parser.fitz")
    def test_font_size_rounded(self, mock_fitz, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4")

        span = _make_span("Text", "Serif", 10.123456, bbox=(100, 200, 300, 220))
        page = _mock_page(_make_page_dict([span]))
        mock_fitz.open.return_value = _mock_doc([page])
        mock_fitz.TEXT_PRESERVE_WHITESPACE = 1

        with PDFParser(pdf, _make_profile()) as parser:
            spans = parser.extract_page_spans(0)
            assert spans[0].font_size == 10.1

    @patch("pylearn.parser.pdf_parser.fitz")
    def test_page_extraction_error_returns_empty(self, mock_fitz, tmp_path):
        """If get_text raises, the page should return empty spans."""
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4")

        page = _mock_page()
        page.get_text.side_effect = Exception("decode error")
        mock_fitz.open.return_value = _mock_doc([page])
        mock_fitz.TEXT_PRESERVE_WHITESPACE = 1

        with PDFParser(pdf, _make_profile()) as parser:
            spans = parser.extract_page_spans(0)
            assert spans == []

    @patch("pylearn.parser.pdf_parser.fitz")
    def test_auto_open_on_extract(self, mock_fitz, tmp_path):
        """extract_page_spans should auto-open if not already opened."""
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4")

        page = _mock_page(_make_page_dict([_make_span("Auto", bbox=(100, 200, 300, 220))]))
        mock_fitz.open.return_value = _mock_doc([page])
        mock_fitz.TEXT_PRESERVE_WHITESPACE = 1

        parser = PDFParser(pdf, _make_profile())
        # Don't call parser.open() — should auto-open
        spans = parser.extract_page_spans(0)
        assert len(spans) == 1
        parser.close()


# ===========================================================================
# extract_page_images
# ===========================================================================


class TestExtractPageImages:
    @patch("pylearn.parser.pdf_parser.fitz")
    def test_basic_image_extraction(self, mock_fitz, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        save_dir = tmp_path / "images"

        page = _mock_page(images=[(42, 0, 0, 0, 0, 0, 0, 0, 0, 0)])
        doc = _mock_doc([page])
        doc.extract_image.return_value = {
            "image": b"\x89PNG fake image data",
            "width": 200,
            "height": 150,
            "ext": "png",
        }
        mock_fitz.open.return_value = doc

        with PDFParser(pdf, _make_profile()) as parser:
            images = parser.extract_page_images(0, save_dir)
            assert len(images) == 1
            assert images[0]["width"] == 200
            assert images[0]["height"] == 150
            assert images[0]["page_num"] == 0
            assert save_dir.exists()

    @patch("pylearn.parser.pdf_parser.fitz")
    def test_small_images_filtered(self, mock_fitz, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        save_dir = tmp_path / "images"

        page = _mock_page(images=[(42, 0, 0, 0, 0, 0, 0, 0, 0, 0)])
        doc = _mock_doc([page])
        doc.extract_image.return_value = {
            "image": b"tiny",
            "width": 10,
            "height": 10,
            "ext": "png",
        }
        mock_fitz.open.return_value = doc

        with PDFParser(pdf, _make_profile()) as parser:
            images = parser.extract_page_images(0, save_dir)
            assert len(images) == 0

    @patch("pylearn.parser.pdf_parser.fitz")
    def test_out_of_range_page_returns_empty(self, mock_fitz, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        mock_fitz.open.return_value = _mock_doc([_mock_page()])

        with PDFParser(pdf, _make_profile()) as parser:
            assert parser.extract_page_images(99, tmp_path / "img") == []

    @patch("pylearn.parser.pdf_parser.fitz")
    def test_invalid_extension_defaults_to_png(self, mock_fitz, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        save_dir = tmp_path / "images"

        page = _mock_page(images=[(42, 0, 0, 0, 0, 0, 0, 0, 0, 0)])
        doc = _mock_doc([page])
        doc.extract_image.return_value = {
            "image": b"data",
            "width": 200,
            "height": 150,
            "ext": "webp",  # not in _VALID_IMAGE_EXTENSIONS
        }
        mock_fitz.open.return_value = doc

        with PDFParser(pdf, _make_profile()) as parser:
            images = parser.extract_page_images(0, save_dir)
            assert len(images) == 1
            assert images[0]["filename"].endswith(".png")

    @patch("pylearn.parser.pdf_parser.fitz")
    def test_image_cap_enforced(self, mock_fitz, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        save_dir = tmp_path / "images"

        page = _mock_page(images=[(i, 0, 0, 0, 0, 0, 0, 0, 0, 0) for i in range(10)])
        doc = _mock_doc([page])
        doc.extract_image.return_value = {
            "image": b"data",
            "width": 200,
            "height": 150,
            "ext": "png",
        }
        mock_fitz.open.return_value = doc

        with PDFParser(pdf, _make_profile()) as parser:
            # Pass image_count near the cap
            images = parser.extract_page_images(0, save_dir, image_count=_MAX_IMAGES_PER_BOOK - 2)
            assert len(images) == 2


# ===========================================================================
# extract_pages / extract_all
# ===========================================================================


class TestExtractPages:
    @patch("pylearn.parser.pdf_parser.fitz")
    def test_extract_pages_range(self, mock_fitz, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4")

        pages = []
        for i in range(5):
            span = _make_span(f"Page {i}", bbox=(100, 200, 300, 220))
            pages.append(_mock_page(_make_page_dict([span])))
        mock_fitz.open.return_value = _mock_doc(pages)
        mock_fitz.TEXT_PRESERVE_WHITESPACE = 1

        with PDFParser(pdf, _make_profile()) as parser:
            result = parser.extract_pages(1, 3)
            assert len(result) == 2

    @patch("pylearn.parser.pdf_parser.fitz")
    def test_extract_all_respects_skip(self, mock_fitz, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4")

        pages = [_mock_page(_make_page_dict([_make_span(f"P{i}", bbox=(100, 200, 300, 220))])) for i in range(10)]
        mock_fitz.open.return_value = _mock_doc(pages)
        mock_fitz.TEXT_PRESERVE_WHITESPACE = 1

        profile = _make_profile(skip_pages_start=2, skip_pages_end=3)
        with PDFParser(pdf, profile) as parser:
            result = parser.extract_all()
            # 10 pages, skip first 2 and last 3 = pages 2..6 = 5 pages
            assert len(result) == 5

    @patch("pylearn.parser.pdf_parser.fitz")
    def test_extract_all_warns_when_no_pages(self, mock_fitz, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4")

        pages = [_mock_page() for _ in range(3)]
        mock_fitz.open.return_value = _mock_doc(pages)

        profile = _make_profile(skip_pages_start=10, skip_pages_end=10)
        with PDFParser(pdf, profile) as parser:
            result = parser.extract_all()
            assert result == []


# ===========================================================================
# get_font_statistics
# ===========================================================================


class TestGetFontStatistics:
    @patch("pylearn.parser.pdf_parser.fitz")
    def test_basic_statistics(self, mock_fitz, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4")

        span1 = _make_span("Hello", "Serif", 10.0, flags=0)
        span2 = _make_span("World", "Courier", 9.0, flags=0)
        page_dict = {"blocks": [{"type": 0, "lines": [{"spans": [span1, span2]}]}]}
        page = MagicMock()
        page.get_text.return_value = page_dict
        mock_fitz.open.return_value = _mock_doc([page])

        with PDFParser(pdf, _make_profile()) as parser:
            stats = parser.get_font_statistics()
            assert len(stats) == 2
            keys = list(stats.keys())
            assert any("Serif" in k for k in keys)
            assert any("Courier" in k for k in keys)

    @patch("pylearn.parser.pdf_parser.fitz")
    def test_statistics_sample_text(self, mock_fitz, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4")

        span = _make_span("Sample text here", "Serif", 10.0, flags=0)
        page_dict = {"blocks": [{"type": 0, "lines": [{"spans": [span]}]}]}
        page = MagicMock()
        page.get_text.return_value = page_dict
        mock_fitz.open.return_value = _mock_doc([page])

        with PDFParser(pdf, _make_profile()) as parser:
            stats = parser.get_font_statistics()
            key = next(iter(stats.keys()))
            assert stats[key]["sample"] == "Sample text here"
            assert stats[key]["count"] == 1
