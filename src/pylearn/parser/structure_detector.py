# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Detect chapter and section structure from content blocks."""

from __future__ import annotations

import re
import logging
from collections import Counter

from pylearn.core.models import BlockType, ContentBlock, Chapter, Section
from pylearn.parser.book_profiles import BookProfile

logger = logging.getLogger("pylearn.parser")


class StructureDetector:
    """Build a chapter/section tree from classified content blocks."""

    def __init__(self, profile: BookProfile) -> None:
        self.profile = profile
        try:
            self._chapter_re = re.compile(profile.chapter_pattern, re.IGNORECASE)
        except re.error as e:
            logger.warning("Invalid chapter_pattern %r: %s — using default",
                           profile.chapter_pattern, e)
            self._chapter_re = re.compile(r"^Chapter\s+(\d+)\s*[\.:]", re.IGNORECASE)

    def detect_chapters(self, blocks: list[ContentBlock]) -> list[Chapter]:
        """Split a flat list of blocks into chapters."""
        if not blocks:
            return []

        # Primary: font-size-based detection (works for any book)
        font_starts = self._detect_by_font_size(blocks)

        # Secondary: regex-based detection (gives cleaner titles/numbers)
        regex_starts = self._detect_by_regex(blocks)

        # Use regex result if it finds a similar count to font-size result
        # (within 3), since regex gives cleaner chapter titles and numbers.
        # Otherwise prefer font-size which is more universal.
        if regex_starts and font_starts:
            if abs(len(regex_starts) - len(font_starts)) <= 3:
                chapter_starts = regex_starts
                logger.info(
                    f"Using regex detection ({len(regex_starts)} chapters) — "
                    f"similar to font-size ({len(font_starts)})"
                )
            else:
                chapter_starts = font_starts
                logger.info(
                    f"Using font-size detection ({len(font_starts)} chapters) — "
                    f"regex found {len(regex_starts)}, too different"
                )
        elif regex_starts:
            chapter_starts = regex_starts
        else:
            chapter_starts = font_starts

        if not chapter_starts:
            logger.warning("No chapters detected, treating all content as Chapter 1")
            return [Chapter(
                chapter_num=1,
                title="Content",
                start_page=blocks[0].page_num if blocks else 0,
                end_page=blocks[-1].page_num if blocks else 0,
                content_blocks=blocks,
                sections=self._detect_sections(blocks),
            )]

        chapters: list[Chapter] = []
        for idx, (block_i, chapter_num, title) in enumerate(chapter_starts):
            if idx + 1 < len(chapter_starts):
                end_block_i = chapter_starts[idx + 1][0]
            else:
                end_block_i = len(blocks)

            chapter_blocks = blocks[block_i:end_block_i]
            start_page = chapter_blocks[0].page_num if chapter_blocks else 0
            end_page = chapter_blocks[-1].page_num if chapter_blocks else 0

            chapters.append(Chapter(
                chapter_num=chapter_num,
                title=title,
                start_page=start_page,
                end_page=end_page,
                content_blocks=chapter_blocks,
                sections=self._detect_sections(chapter_blocks),
            ))

        return chapters

    def _detect_by_regex(self, blocks: list[ContentBlock]) -> list[tuple[int, int, str]]:
        """Detect chapters using the profile's chapter_pattern regex."""
        starts = []

        for i, block in enumerate(blocks):
            if block.block_type in (BlockType.HEADING1, BlockType.HEADING2):
                match = self._chapter_re.match(block.text.strip())
                if match:
                    try:
                        chapter_num = int(match.group(1))
                    except (IndexError, ValueError):
                        continue
                    starts.append((i, chapter_num, block.text.strip()))

        return starts

    def _detect_by_font_size(self, blocks: list[ContentBlock]) -> list[tuple[int, int, str]]:
        """Detect chapters by finding the second-largest heading font size.

        Many O'Reilly books use:
          - Largest font = Part titles (Part I, Part II...)
          - Second-largest font = Chapter titles
          - Smaller headings = Sections within chapters

        If there's only one large heading size, use that as chapters.
        """
        heading_blocks = [
            (i, b) for i, b in enumerate(blocks)
            if b.block_type in (BlockType.HEADING1, BlockType.HEADING2)
            and b.font_size > 0
        ]

        if not heading_blocks:
            return []

        # Find distinct heading sizes (rounded to avoid float noise)
        size_counts: Counter[float] = Counter()
        for _, b in heading_blocks:
            size_counts[round(b.font_size, 0)] += 1

        # Sort sizes descending
        sizes = sorted(size_counts.keys(), reverse=True)

        if not sizes:
            return []

        # Pick the chapter-level size:
        # - If the largest size has very few instances (<=10), it's likely Part titles
        #   and the second-largest is chapters
        # - Otherwise the largest IS chapters
        if len(sizes) >= 2 and size_counts[sizes[0]] <= 10:
            chapter_size = sizes[1]
            logger.info(
                f"Using font size {chapter_size} as chapters "
                f"({size_counts[sizes[0]]} parts at size {sizes[0]}, "
                f"{size_counts[chapter_size]} chapters at size {chapter_size})"
            )
        else:
            chapter_size = sizes[0]
            logger.info(f"Using font size {chapter_size} as chapters ({size_counts[chapter_size]} found)")

        starts = []
        chapter_num = 1
        for i, b in heading_blocks:
            if round(b.font_size, 0) == chapter_size:
                starts.append((i, chapter_num, b.text.strip()))
                chapter_num += 1

        logger.info(f"Font-based detection found {len(starts)} chapters")
        return starts

    def _detect_sections(self, blocks: list[ContentBlock]) -> list[Section]:
        """Detect section hierarchy within a chapter's blocks."""
        sections: list[Section] = []
        section_stack: list[Section] = []

        for i, block in enumerate(blocks):
            if block.block_type == BlockType.HEADING1:
                section = Section(
                    title=block.text.strip(),
                    level=1,
                    page_num=block.page_num,
                    block_index=i,
                )
                sections.append(section)
                section_stack = [section]

            elif block.block_type == BlockType.HEADING2:
                section = Section(
                    title=block.text.strip(),
                    level=2,
                    page_num=block.page_num,
                    block_index=i,
                )
                while section_stack and section_stack[-1].level >= 2:
                    section_stack.pop()
                if section_stack:
                    section_stack[-1].children.append(section)
                else:
                    sections.append(section)
                section_stack.append(section)

            elif block.block_type == BlockType.HEADING3:
                section = Section(
                    title=block.text.strip(),
                    level=3,
                    page_num=block.page_num,
                    block_index=i,
                )
                while section_stack and section_stack[-1].level >= 3:
                    section_stack.pop()
                if section_stack:
                    section_stack[-1].children.append(section)
                else:
                    sections.append(section)
                section_stack.append(section)

        return sections
