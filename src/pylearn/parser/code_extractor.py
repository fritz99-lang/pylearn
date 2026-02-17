# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Extract and merge code blocks from classified content."""

from __future__ import annotations

import re
from pylearn.core.models import BlockType, ContentBlock
from pylearn.utils.text_utils import clean_code_text, detect_repl_code


class CodeExtractor:
    """Post-process content blocks to merge and clean code blocks."""

    def process(self, blocks: list[ContentBlock]) -> list[ContentBlock]:
        """Merge adjacent code blocks and assign IDs."""
        merged = self._merge_adjacent_code(blocks)
        self._assign_block_ids(merged)
        return merged

    def _merge_adjacent_code(self, blocks: list[ContentBlock]) -> list[ContentBlock]:
        """Merge consecutive code blocks into single blocks."""
        if not blocks:
            return []

        result: list[ContentBlock] = []
        i = 0

        while i < len(blocks):
            block = blocks[i]

            if block.block_type not in (BlockType.CODE, BlockType.CODE_REPL):
                result.append(block)
                i += 1
                continue

            # Collect consecutive code blocks
            code_parts = [block.text]
            code_type = block.block_type
            start_page = block.page_num
            j = i + 1

            while j < len(blocks) and blocks[j].block_type in (BlockType.CODE, BlockType.CODE_REPL):
                code_parts.append(blocks[j].text)
                j += 1

            merged_text = clean_code_text("\n".join(code_parts))

            # Re-check if it's REPL after merging
            if detect_repl_code(merged_text):
                code_type = BlockType.CODE_REPL

            result.append(ContentBlock(
                block_type=code_type,
                text=merged_text,
                page_num=start_page,
                font_size=block.font_size,
                is_monospace=True,
            ))
            i = j

        return result

    def _assign_block_ids(self, blocks: list[ContentBlock]) -> None:
        """Assign unique IDs to code and heading blocks."""
        code_index = 0
        heading_index = 0
        for block in blocks:
            if block.block_type in (BlockType.CODE, BlockType.CODE_REPL):
                block.block_id = f"code_{code_index}"
                code_index += 1
            elif block.block_type in (BlockType.HEADING1, BlockType.HEADING2, BlockType.HEADING3):
                block.block_id = f"heading_{heading_index}"
                heading_index += 1

    def extract_runnable_code(self, blocks: list[ContentBlock]) -> list[ContentBlock]:
        """Extract only code blocks that appear runnable."""
        runnable = []
        for block in blocks:
            if block.block_type not in (BlockType.CODE, BlockType.CODE_REPL):
                continue
            text = block.text.strip()
            # Skip very short snippets (likely inline references)
            if len(text) < 10 or "\n" not in text:
                continue
            # Skip blocks that are just output
            if not any(line.strip().startswith((">>>", "import", "def ", "class ",
                                                 "for ", "while ", "if ", "print",
                                                 "from ", "with ", "#"))
                       for line in text.split("\n")):
                continue
            runnable.append(block)
        return runnable
