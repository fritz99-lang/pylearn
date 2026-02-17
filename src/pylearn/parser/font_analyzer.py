# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Auto-detect PDF font structure and build a BookProfile without manual tuning.

Samples pages from the PDF, builds a font histogram, and computes parsing
thresholds (heading sizes, code font, margins, skip pages) automatically.
"""

from __future__ import annotations

import logging
from collections import Counter
from pathlib import Path

import fitz  # PyMuPDF

from pylearn.parser.book_profiles import BookProfile
from pylearn.utils.text_utils import clean_text

logger = logging.getLogger("pylearn.parser")

# Common monospace font substrings
_MONO_HINTS = [
    "courier", "mono", "consolas", "menlo", "dejavusansmono",
    "lucidaconsole", "sourcecodepro", "inconsolata", "firacode",
    "droidsansmono", "robotomono", "ubuntumono", "liberationmono",
]

# Front-matter keywords (case-insensitive)
_FRONT_MATTER_KW = [
    "copyright", "table of contents", "preface",
    "foreword", "acknowledgment", "dedication", "about the author",
]

# Back-matter keywords (case-insensitive)
_BACK_MATTER_KW = [
    "index", "appendix", "glossary", "bibliography", "colophon",
]


def _is_mono(font_name: str) -> bool:
    """Heuristic: does font_name look monospace?"""
    lower = font_name.lower()
    return any(hint in lower for hint in _MONO_HINTS)


class FontAnalyzer:
    """Analyze a PDF and produce a BookProfile with auto-detected thresholds."""

    def __init__(self, pdf_path: str | Path) -> None:
        self.pdf_path = Path(pdf_path)

    def build_profile(self, language: str = "python") -> BookProfile:
        """Sample the PDF and return a fully populated BookProfile.

        If analysis fails partway through, returns a safe default profile
        rather than a half-populated one.
        """
        doc = fitz.open(str(self.pdf_path))
        try:
            return self._analyze(doc, language)
        except Exception as e:
            logger.error("Font analysis failed, returning default profile: %s", e)
            return BookProfile(name="auto", language=language)
        finally:
            doc.close()

    def _analyze(self, doc: fitz.Document, language: str) -> BookProfile:
        """Internal: perform the actual analysis (may raise)."""
        total = len(doc)
        sample_indices = self._pick_sample_pages(total)

        # --- 1. Build font histogram ---
        histogram: Counter[tuple[str, float, bool, bool]] = Counter()
        y_positions: list[list[float]] = []  # per-page list of y0 values

        for pg in sample_indices:
            page = doc[pg]
            page_ys: list[float] = []
            blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
            for block in blocks:
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = clean_text(span.get("text", "")).strip()
                        if not text:
                            continue
                        font = span.get("font", "")
                        size = round(span.get("size", 0.0), 1)
                        flags = span.get("flags", 0)
                        bold = bool(flags & 16)
                        mono = _is_mono(font)
                        # Weight by character count so body text dominates
                        histogram[(font, size, bold, mono)] += len(text)
                        bbox = span.get("bbox", (0, 0, 0, 0))
                        page_ys.append(bbox[1])
            y_positions.append(page_ys)

        if not histogram:
            logger.warning("No text found in sampled pages — returning default profile")
            return BookProfile(name="auto", language=language)

        # --- 2. Identify body font (most frequent non-mono) ---
        body_font, body_size = self._find_body_font(histogram)

        # --- 3. Identify code font (most frequent mono) ---
        code_size = self._find_code_size(histogram, body_size)

        # --- 4. Heading tiers ---
        h1_min, h2_min, h3_min = self._compute_heading_thresholds(
            histogram, body_size
        )

        # --- 5. Margin detection ---
        margin_top, margin_bottom = self._detect_margins(
            y_positions, doc, sample_indices
        )

        # --- 6. Skip pages ---
        skip_start, skip_end = self._detect_skip_pages(doc)

        logger.info(
            f"Auto-detect: body={body_size}, code={code_size}, "
            f"h1>={h1_min}, h2>={h2_min}, h3>={h3_min}, "
            f"margins=({margin_top:.0f}, {margin_bottom:.0f}), "
            f"skip=({skip_start}, {skip_end})"
        )

        return BookProfile(
            name="auto",
            language=language,
            heading1_min_size=h1_min,
            heading2_min_size=h2_min,
            heading3_min_size=h3_min,
            body_size=body_size,
            code_size=code_size,
            margin_top=margin_top,
            margin_bottom=margin_bottom,
            skip_pages_start=skip_start,
            skip_pages_end=skip_end,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _pick_sample_pages(total: int, target: int = 40) -> list[int]:
        """Pick ~target pages evenly distributed across the document."""
        if total <= target:
            return list(range(total))
        step = max(1, total // target)
        return list(range(0, total, step))[:target]

    @staticmethod
    def _find_body_font(
        histogram: Counter[tuple[str, float, bool, bool]],
    ) -> tuple[str, float]:
        """Return (font_name, size) of the most frequent non-monospace font."""
        non_mono: Counter[tuple[str, float]] = Counter()
        for (font, size, _bold, mono), count in histogram.items():
            if not mono:
                non_mono[(font, size)] += count
        if non_mono:
            (font, size), _ = non_mono.most_common(1)[0]
            return font, size
        # Fallback: just use the most common anything
        if histogram:
            (font, size, _, _), _ = histogram.most_common(1)[0]
            return font, size
        return ("unknown", 10.0)

    @staticmethod
    def _find_code_size(
        histogram: Counter[tuple[str, float, bool, bool]],
        body_size: float,
    ) -> float:
        """Return the size of the most frequent monospace font."""
        mono_sizes: Counter[float] = Counter()
        for (font, size, _bold, mono), count in histogram.items():
            if mono:
                mono_sizes[size] += count
        if mono_sizes:
            return mono_sizes.most_common(1)[0][0]
        # No monospace found — guess slightly smaller than body
        return max(body_size - 1.5, 6.0)

    @staticmethod
    def _compute_heading_thresholds(
        histogram: Counter[tuple[str, float, bool, bool]],
        body_size: float,
    ) -> tuple[float, float, float]:
        """Identify heading tiers and return (h1_min, h2_min, h3_min)."""
        # Collect non-mono sizes larger than body
        large_sizes: Counter[float] = Counter()
        for (font, size, _bold, mono), count in histogram.items():
            if not mono and size > body_size + 0.5:
                large_sizes[size] += count

        if not large_sizes:
            # No headings larger than body — use defaults
            return (body_size + 8, body_size + 4, body_size + 2)

        # Filter out cover/title page artifacts: sizes with very few total
        # characters are likely one-off decorative text, not real headings.
        # Real chapter headings have substantial total text across the book.
        min_chars = 50
        filtered = {s: c for s, c in large_sizes.items() if c >= min_chars}
        if not filtered and large_sizes:
            # All sizes are rare — relax to the most common one
            top = large_sizes.most_common(1)[0]
            filtered = {top[0]: top[1]}

        # Group sizes within 1pt to avoid bold/regular duplicates
        sorted_sizes = sorted(filtered.keys(), reverse=True)
        tiers: list[float] = []
        for s in sorted_sizes:
            if not tiers or abs(s - tiers[-1]) > 1.0:
                tiers.append(s)
            # else: merge into existing tier (keep the larger one already there)

        # Top 3 tiers become h1/h2/h3
        if len(tiers) >= 3:
            t1, t2, t3 = tiers[0], tiers[1], tiers[2]
            h1_min = (t1 + t2) / 2
            h2_min = (t2 + t3) / 2
            h3_min = (t3 + body_size) / 2
        elif len(tiers) == 2:
            t0, t1 = tiers[0], tiers[1]
            h1_min = (t0 + t1) / 2
            h2_min = (t1 + body_size) / 2
            h3_min = body_size + 1
        else:
            # Only one tier
            t0 = tiers[0]
            h1_min = (t0 + body_size) / 2
            h2_min = body_size + 2
            h3_min = body_size + 1

        return (round(h1_min, 1), round(h2_min, 1), round(h3_min, 1))

    @staticmethod
    def _detect_margins(
        y_positions: list[list[float]],
        doc: fitz.Document,
        sample_indices: list[int],
    ) -> tuple[float, float]:
        """Find y-positions with text on 50%+ of pages = headers/footers."""
        if not y_positions or not sample_indices:
            return (50.0, 50.0)

        n_pages = len(y_positions)
        threshold = n_pages * 0.5

        # Get page height from first sampled page
        page_height = doc[sample_indices[0]].rect.height

        # Bucket y-positions into 5pt bins
        top_bins: Counter[int] = Counter()     # bins in top 15% of page
        bottom_bins: Counter[int] = Counter()  # bins in bottom 15% of page

        top_zone = page_height * 0.15
        bottom_zone = page_height * 0.85

        for page_ys in y_positions:
            # Count unique bins per page (not multiple spans in same bin)
            seen_top: set[int] = set()
            seen_bottom: set[int] = set()
            for y in page_ys:
                b = int(y // 5)
                if y < top_zone and b not in seen_top:
                    top_bins[b] += 1
                    seen_top.add(b)
                elif y > bottom_zone and b not in seen_bottom:
                    bottom_bins[b] += 1
                    seen_bottom.add(b)

        # Find the lowest header y and highest footer y that appear on 50%+ pages
        margin_top = 50.0  # default
        for b, count in top_bins.items():
            if count >= threshold:
                candidate = (b + 1) * 5 + 5  # a bit below the bin
                margin_top = max(margin_top, candidate)

        margin_bottom = 50.0  # default
        for b, count in bottom_bins.items():
            if count >= threshold:
                candidate = page_height - (b * 5) + 5
                margin_bottom = max(margin_bottom, candidate)

        return (min(margin_top, 90.0), min(margin_bottom, 90.0))

    @staticmethod
    def _detect_skip_pages(doc: fitz.Document) -> tuple[int, int]:
        """Scan first/last pages for front/back matter keywords."""
        total = len(doc)

        # Front matter: scan first 15 pages (beyond that, keywords like
        # "table of contents" are real content, not front matter).
        skip_start = 0
        max_skip_start = max(2, total // 15)  # Cap at ~7% of book
        scan_front = min(15, total)
        for pg in range(scan_front):
            text = doc[pg].get_text().lower()
            for kw in _FRONT_MATTER_KW:
                if kw in text:
                    skip_start = max(skip_start, pg + 1)
        skip_start = min(skip_start, max_skip_start)

        # Back matter: scan last 40 pages
        skip_end = 0
        scan_back_start = max(0, total - 40)
        for pg in range(scan_back_start, total):
            text = doc[pg].get_text().lower()
            for kw in _BACK_MATTER_KW:
                if kw in text:
                    skip_end = max(skip_end, total - pg)
                    break  # one keyword is enough for this page

        return (skip_start, skip_end)
