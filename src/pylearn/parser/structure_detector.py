"""Detect chapter and section structure from content blocks."""

from __future__ import annotations

import re
import logging

from pylearn.core.models import BlockType, ContentBlock, Chapter, Section
from pylearn.parser.book_profiles import BookProfile

logger = logging.getLogger("pylearn.parser")


class StructureDetector:
    """Build a chapter/section tree from classified content blocks."""

    def __init__(self, profile: BookProfile) -> None:
        self.profile = profile

    def detect_chapters(self, blocks: list[ContentBlock]) -> list[Chapter]:
        """Split a flat list of blocks into chapters."""
        chapters: list[Chapter] = []
        chapter_starts: list[tuple[int, int, str]] = []  # (block_index, chapter_num, title)

        pattern = re.compile(self.profile.chapter_pattern, re.IGNORECASE)

        for i, block in enumerate(blocks):
            if block.block_type in (BlockType.HEADING1, BlockType.HEADING2):
                match = pattern.match(block.text.strip())
                if match:
                    chapter_num = int(match.group(1))
                    title = block.text.strip()
                    chapter_starts.append((i, chapter_num, title))

        if not chapter_starts:
            # Fallback: treat entire content as one chapter
            logger.warning("No chapters detected, treating all content as Chapter 1")
            return [Chapter(
                chapter_num=1,
                title="Content",
                start_page=blocks[0].page_num if blocks else 0,
                end_page=blocks[-1].page_num if blocks else 0,
                content_blocks=blocks,
                sections=self._detect_sections(blocks),
            )]

        for idx, (block_i, chapter_num, title) in enumerate(chapter_starts):
            # Determine end of this chapter
            if idx + 1 < len(chapter_starts):
                end_block_i = chapter_starts[idx + 1][0]
            else:
                end_block_i = len(blocks)

            chapter_blocks = blocks[block_i:end_block_i]
            start_page = chapter_blocks[0].page_num if chapter_blocks else 0
            end_page = chapter_blocks[-1].page_num if chapter_blocks else 0

            chapter = Chapter(
                chapter_num=chapter_num,
                title=title,
                start_page=start_page,
                end_page=end_page,
                content_blocks=chapter_blocks,
                sections=self._detect_sections(chapter_blocks),
            )
            chapters.append(chapter)

        return chapters

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
                # Find parent
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
