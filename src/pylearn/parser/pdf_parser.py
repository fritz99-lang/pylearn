"""PDF text extraction using PyMuPDF with font metadata."""

from __future__ import annotations

import logging
from pathlib import Path

import fitz  # PyMuPDF

from pylearn.core.models import FontSpan
from pylearn.parser.book_profiles import BookProfile
from pylearn.utils.text_utils import clean_text

logger = logging.getLogger("pylearn.parser")


class PDFParser:
    """Extract text spans with font metadata from a PDF file."""

    def __init__(self, pdf_path: str | Path, profile: BookProfile) -> None:
        self.pdf_path = Path(pdf_path)
        self.profile = profile
        self._doc: fitz.Document | None = None

    def open(self) -> None:
        self._doc = fitz.open(str(self.pdf_path))

    def close(self) -> None:
        if self._doc:
            self._doc.close()
            self._doc = None

    @property
    def total_pages(self) -> int:
        if self._doc is None:
            self.open()
        return len(self._doc)

    def extract_page_spans(self, page_num: int) -> list[FontSpan]:
        """Extract all text spans from a single page with font metadata."""
        if self._doc is None:
            self.open()

        if page_num < 0 or page_num >= len(self._doc):
            return []

        page = self._doc[page_num]
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
        spans = []

        for block in blocks:
            if block.get("type") != 0:  # text block
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = clean_text(span.get("text", ""))
                    if not text.strip():
                        continue

                    font_name = span.get("font", "")
                    font_size = span.get("size", 0.0)
                    flags = span.get("flags", 0)
                    color = span.get("color", 0)
                    bbox = span.get("bbox", (0, 0, 0, 0))

                    # Skip if outside content margins
                    if bbox[1] < self.profile.margin_top or bbox[3] > page.rect.height - self.profile.margin_bottom:
                        continue

                    is_bold = bool(flags & 2 ** 4)  # bit 4 = bold
                    is_italic = bool(flags & 2 ** 1)  # bit 1 = italic
                    is_mono = self.profile.is_monospace(font_name)

                    spans.append(FontSpan(
                        text=text,
                        font_name=font_name,
                        font_size=round(font_size, 1),
                        is_bold=is_bold,
                        is_italic=is_italic,
                        is_monospace=is_mono,
                        color=color,
                        page_num=page_num,
                        x0=bbox[0],
                        y0=bbox[1],
                        x1=bbox[2],
                        y1=bbox[3],
                    ))

        return spans

    def extract_pages(self, start_page: int, end_page: int) -> list[list[FontSpan]]:
        """Extract spans from a range of pages."""
        if self._doc is None:
            self.open()

        pages = []
        end = min(end_page, len(self._doc))
        for page_num in range(start_page, end):
            try:
                spans = self.extract_page_spans(page_num)
                pages.append(spans)
            except Exception as e:
                logger.warning(f"Error extracting page {page_num}: {e}")
                pages.append([])
        return pages

    def extract_all(self) -> list[list[FontSpan]]:
        """Extract spans from all content pages (skipping front/back matter)."""
        if self._doc is None:
            self.open()

        start = self.profile.skip_pages_start
        end = len(self._doc) - self.profile.skip_pages_end
        return self.extract_pages(start, end)

    def get_font_statistics(self) -> dict[str, dict]:
        """Analyze font usage across the document for profiling."""
        if self._doc is None:
            self.open()

        font_stats: dict[str, dict] = {}
        sample_pages = list(range(0, len(self._doc), max(1, len(self._doc) // 20)))

        for page_num in sample_pages:
            page = self._doc[page_num]
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        font = span.get("font", "unknown")
                        size = round(span.get("size", 0), 1)
                        flags = span.get("flags", 0)
                        key = f"{font}|{size}|{flags}"
                        if key not in font_stats:
                            font_stats[key] = {
                                "font": font,
                                "size": size,
                                "flags": flags,
                                "is_bold": bool(flags & 16),
                                "is_italic": bool(flags & 2),
                                "count": 0,
                                "sample": "",
                            }
                        font_stats[key]["count"] += 1
                        if not font_stats[key]["sample"]:
                            text = span.get("text", "").strip()
                            if text:
                                font_stats[key]["sample"] = text[:80]

        return font_stats
