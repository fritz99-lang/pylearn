# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Classify font spans into content block types."""

from __future__ import annotations

import logging
import re

from pylearn.core.models import BlockType, ContentBlock, FontSpan
from pylearn.parser.book_profiles import BookProfile
from pylearn.utils.text_utils import is_page_header_or_footer, detect_repl_code

logger = logging.getLogger("pylearn.parser")


_LIST_BULLET_RE = re.compile(r"^[\s]*[•●○■▪\u2022\u2023\u25E6\u2043\-\*]\s")
_LIST_NUMBER_RE = re.compile(r"^[\s]*\d{1,3}[.)]\s")
_NOTE_RE = re.compile(r"^Note\b[:\.\s]*", re.IGNORECASE)
_WARNING_RE = re.compile(r"^(?:Warning|Caution)\b[:\.\s]*", re.IGNORECASE)
_TIP_RE = re.compile(r"^Tip\b[:\.\s]*", re.IGNORECASE)


class ContentClassifier:
    """Classify sequences of FontSpans into ContentBlocks."""

    def __init__(self, profile: BookProfile) -> None:
        self.profile = profile

    def classify_span(self, span: FontSpan) -> BlockType:
        """Determine the block type for a single span based on font properties."""
        # Monospace = code
        if span.is_monospace:
            return BlockType.CODE

        # Large bold = heading
        if span.font_size >= self.profile.heading1_min_size:
            return BlockType.HEADING1
        if span.font_size >= self.profile.heading2_min_size:
            if span.is_bold:
                return BlockType.HEADING2
        if span.font_size >= self.profile.heading3_min_size:
            if span.is_bold:
                return BlockType.HEADING3

        return BlockType.BODY

    def classify_page_spans(self, spans: list[FontSpan], page_num: int = 0) -> list[ContentBlock]:
        """Convert a page's spans into classified content blocks, merging adjacent same-type spans."""
        if not spans:
            return []

        blocks: list[ContentBlock] = []
        current_type: BlockType | None = None
        current_text_parts: list[str] = []
        current_font_size: float = 0.0
        current_is_bold: bool = False
        current_is_mono: bool = False

        def _flush() -> None:
            nonlocal current_type, current_text_parts, current_font_size
            if current_type is not None and current_text_parts:
                text = " ".join(current_text_parts)
                # Rejoin words hyphenated across PDF lines (e.g. "com- municate" → "communicate")
                # Only for prose blocks — the space after the hyphen distinguishes these from
                # real hyphens like "well-known" which have no space.
                if current_type not in (BlockType.CODE, BlockType.CODE_REPL):
                    text = re.sub(r"([a-z])-\s+([a-z])", r"\1\2", text)
                # Skip headers/footers
                if is_page_header_or_footer(text, page_num):
                    current_text_parts = []
                    current_type = None
                    return
                blocks.append(ContentBlock(
                    block_type=current_type,
                    text=text,
                    page_num=page_num,
                    font_size=current_font_size,
                    is_bold=current_is_bold,
                    is_monospace=current_is_mono,
                ))
            current_text_parts = []
            current_type = None

        for span in spans:
            span_type = self.classify_span(span)

            # For code, use newlines instead of spaces for joining
            if span_type == current_type and current_type == BlockType.CODE:
                current_text_parts.append(span.text)
                continue

            if span_type != current_type:
                _flush()
                current_type = span_type
                current_font_size = span.font_size
                current_is_bold = span.is_bold
                current_is_mono = span.is_monospace

            current_text_parts.append(span.text)

        _flush()

        # Post-process: detect special block types
        for block in blocks:
            if block.block_type == BlockType.CODE and detect_repl_code(block.text):
                block.block_type = BlockType.CODE_REPL
            elif block.block_type == BlockType.BODY:
                if _LIST_BULLET_RE.match(block.text) or _LIST_NUMBER_RE.match(block.text):
                    block.block_type = BlockType.LIST_ITEM
                elif _NOTE_RE.match(block.text):
                    block.block_type = BlockType.NOTE
                    block.text = _NOTE_RE.sub("", block.text, count=1)
                elif _WARNING_RE.match(block.text):
                    block.block_type = BlockType.WARNING
                    block.text = _WARNING_RE.sub("", block.text, count=1)
                elif _TIP_RE.match(block.text):
                    block.block_type = BlockType.TIP
                    block.text = _TIP_RE.sub("", block.text, count=1)

        return blocks

    def classify_all_pages(self, pages: list[list[FontSpan]],
                           start_page_offset: int = 0,
                           page_images: dict[int, list[dict]] | None = None) -> list[ContentBlock]:
        """Classify spans from multiple pages into a flat list of content blocks.

        Args:
            pages: List of per-page FontSpan lists.
            start_page_offset: PDF page number of the first page in the list.
            page_images: Optional dict mapping page_num → list of image metadata
                         dicts (from PDFParser.extract_page_images). Each dict
                         has keys: filename, y0, page_num, width, height.
        """
        all_blocks: list[ContentBlock] = []
        for i, page_spans in enumerate(pages):
            page_num = start_page_offset + i
            page_blocks = self.classify_page_spans(page_spans, page_num)

            # Interleave images by vertical position
            if page_images and page_num in page_images:
                page_blocks = self._interleave_images(page_blocks, page_images[page_num], page_num)

            all_blocks.extend(page_blocks)
        return all_blocks

    @staticmethod
    def _interleave_images(blocks: list[ContentBlock], images: list[dict],
                           page_num: int) -> list[ContentBlock]:
        """Insert FIGURE blocks among text blocks based on y-position."""
        if not images:
            return blocks

        # Build image blocks sorted by vertical position
        img_blocks = []
        for img in sorted(images, key=lambda x: x.get("y0", 0)):
            img_blocks.append((
                img.get("y0", 0),
                ContentBlock(
                    block_type=BlockType.FIGURE,
                    text=img["filename"],
                    page_num=page_num,
                ),
            ))

        # Merge: walk text blocks (which have no y0 — use insertion order as proxy)
        # Insert images between blocks, grouping at end if no good position found
        result: list[ContentBlock] = []
        img_idx = 0
        # Estimate text block positions as evenly spaced on page
        n = len(blocks) or 1
        for i, block in enumerate(blocks):
            # Insert any images whose y0 is before this block's estimated position
            est_y = (i / n) * 800  # rough page height proxy
            while img_idx < len(img_blocks) and img_blocks[img_idx][0] <= est_y:
                result.append(img_blocks[img_idx][1])
                img_idx += 1
            result.append(block)

        # Append remaining images at end
        while img_idx < len(img_blocks):
            result.append(img_blocks[img_idx][1])
            img_idx += 1

        return result
