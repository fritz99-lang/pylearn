"""Classify font spans into content block types."""

from __future__ import annotations

import logging

from pylearn.core.models import BlockType, ContentBlock, FontSpan
from pylearn.parser.book_profiles import BookProfile
from pylearn.utils.text_utils import is_page_header_or_footer, detect_repl_code

logger = logging.getLogger("pylearn.parser")


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

        # Post-process: detect REPL code vs regular code
        for block in blocks:
            if block.block_type == BlockType.CODE and detect_repl_code(block.text):
                block.block_type = BlockType.CODE_REPL

        return blocks

    def classify_all_pages(self, pages: list[list[FontSpan]],
                           start_page_offset: int = 0) -> list[ContentBlock]:
        """Classify spans from multiple pages into a flat list of content blocks."""
        all_blocks: list[ContentBlock] = []
        for i, page_spans in enumerate(pages):
            page_num = start_page_offset + i
            page_blocks = self.classify_page_spans(page_spans, page_num)
            all_blocks.extend(page_blocks)
        return all_blocks
