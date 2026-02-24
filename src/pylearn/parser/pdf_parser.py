# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""PDF text extraction using PyMuPDF with font metadata."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF

from pylearn.core.models import FontSpan
from pylearn.parser.book_profiles import BookProfile
from pylearn.utils.text_utils import clean_text

logger = logging.getLogger("pylearn.parser")

# Allowed image file extensions from PyMuPDF extraction
_VALID_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "bmp", "gif", "tiff"}

# Maximum number of images to extract per book
_MAX_IMAGES_PER_BOOK = 500


class PDFParser:
    """Extract text spans with font metadata from a PDF file."""

    def __init__(self, pdf_path: str | Path, profile: BookProfile) -> None:
        self.pdf_path = Path(pdf_path)
        self.profile = profile
        self._doc: fitz.Document | None = None

    def open(self) -> None:
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {self.pdf_path}")
        try:
            self._doc = fitz.open(str(self.pdf_path))
        except Exception as e:
            raise RuntimeError(f"Failed to open PDF {self.pdf_path}: {e}") from e

    def close(self) -> None:
        if self._doc:
            self._doc.close()
            self._doc = None

    def __enter__(self) -> PDFParser:
        self.open()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _get_doc(self) -> fitz.Document:
        """Return the open document, raising if not opened."""
        if self._doc is None:
            raise RuntimeError("PDFParser not opened. Use 'with PDFParser(...) as p:' or call .open()")
        return self._doc

    @property
    def total_pages(self) -> int:
        return len(self._get_doc())

    def extract_page_spans(self, page_num: int) -> list[FontSpan]:
        """Extract all text spans from a single page with font metadata."""
        if self._doc is None:
            self.open()
        doc = self._get_doc()

        if page_num < 0 or page_num >= len(doc):
            return []

        page = doc[page_num]
        try:
            raw = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
        except Exception as e:
            logger.warning("Failed to extract text from page %d: %s", page_num, e)
            return []
        blocks = raw.get("blocks", [])
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
                    if font_size <= 0:
                        continue
                    flags = span.get("flags", 0)
                    color = span.get("color", 0)
                    bbox = span.get("bbox", (0, 0, 0, 0))
                    if len(bbox) < 4 or bbox[0] > bbox[2] or bbox[1] > bbox[3]:
                        continue  # invalid bounding box

                    # Skip if outside content margins — but exempt large text
                    # that is likely a chapter heading, not a running header.
                    is_heading_sized = font_size >= self.profile.heading2_min_size
                    if not is_heading_sized:
                        if bbox[1] < self.profile.margin_top or bbox[3] > page.rect.height - self.profile.margin_bottom:
                            continue

                    is_bold = bool(flags & 2**4)  # bit 4 = bold
                    is_italic = bool(flags & 2**1)  # bit 1 = italic
                    is_mono = self.profile.is_monospace(font_name)

                    spans.append(
                        FontSpan(
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
                        )
                    )

        return spans

    def extract_page_images(
        self, page_num: int, save_dir: Path, min_width: int = 50, min_height: int = 50, image_count: int = 0
    ) -> list[dict]:
        """Extract images from a page, save to disk, return metadata.

        Returns list of dicts with keys: filename, y0, page_num, width, height.
        Small images (icons, bullets) are skipped via min_width/min_height.
        image_count is the running total across pages; extraction stops at
        _MAX_IMAGES_PER_BOOK to prevent disk-fill from image-heavy PDFs.
        """
        if self._doc is None:
            self.open()
        doc = self._get_doc()
        if page_num < 0 or page_num >= len(doc):
            return []

        save_dir.mkdir(parents=True, exist_ok=True)
        page = doc[page_num]
        images: list[dict[str, Any]] = []

        for img_info in page.get_images(full=True):
            if image_count + len(images) >= _MAX_IMAGES_PER_BOOK:
                logger.warning("Image extraction cap (%d) reached", _MAX_IMAGES_PER_BOOK)
                break
            xref = img_info[0]
            try:
                base_image = doc.extract_image(xref)
                if not base_image or not base_image.get("image"):
                    continue

                width = base_image.get("width", 0)
                height = base_image.get("height", 0)
                if width < min_width or height < min_height:
                    continue

                ext = base_image.get("ext", "png")
                if ext not in _VALID_IMAGE_EXTENSIONS:
                    ext = "png"
                image_bytes = base_image["image"]

                # Deduplicate by content hash
                img_hash = hashlib.sha256(image_bytes).hexdigest()[:12]
                filename = f"p{page_num}_{img_hash}.{ext}"
                filepath = save_dir / filename

                if not filepath.exists():
                    filepath.write_bytes(image_bytes)

                # Get vertical position from image rect on page
                img_rects = page.get_image_rects(xref)
                y0 = img_rects[0].y0 if img_rects else 0.0

                images.append(
                    {
                        "filename": filename,
                        "y0": y0,
                        "page_num": page_num,
                        "width": width,
                        "height": height,
                    }
                )
            except Exception as e:
                logger.debug(f"Skipping image xref={xref} on page {page_num}: {e}")

        return images

    def extract_pages(self, start_page: int, end_page: int) -> list[list[FontSpan]]:
        """Extract spans from a range of pages."""
        if self._doc is None:
            self.open()
        doc = self._get_doc()

        pages = []
        end = min(end_page, len(doc))
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
        doc = self._get_doc()

        total = len(doc)
        start = min(self.profile.skip_pages_start, total)
        end = max(start, total - self.profile.skip_pages_end)
        if start >= end:
            logger.warning(
                "skip_pages (%d start, %d end) leaves no pages in a %d-page PDF",
                self.profile.skip_pages_start,
                self.profile.skip_pages_end,
                total,
            )
        return self.extract_pages(start, end)

    def get_font_statistics(self) -> dict[str, dict]:
        """Analyze font usage across the document for profiling."""
        if self._doc is None:
            self.open()
        doc = self._get_doc()

        font_stats: dict[str, dict[str, Any]] = {}
        sample_pages = list(range(0, len(doc), max(1, len(doc) // 20)))

        for page_num in sample_pages:
            page = doc[page_num]
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
