"""Shared pytest fixtures for PyLearn tests."""

from __future__ import annotations

import pytest

from pylearn.core.models import (
    BlockType,
    Book,
    Chapter,
    ContentBlock,
    FontSpan,
    Section,
)
from pylearn.parser.book_profiles import BookProfile


@pytest.fixture
def sample_profile() -> BookProfile:
    """A test book profile with sensible defaults."""
    return BookProfile(
        name="test",
        heading1_min_size=20.0,
        heading2_min_size=14.0,
        heading3_min_size=12.0,
        body_size=10.0,
        code_size=8.5,
        chapter_pattern=r"^Chapter\s+(\d+)\s*[\.:]",
    )


@pytest.fixture
def sample_spans() -> list[FontSpan]:
    """A realistic set of FontSpans representing a mini-chapter."""
    return [
        # Chapter heading
        FontSpan(text="Chapter 1: Getting Started", font_name="Serif", font_size=22.0, is_bold=True, page_num=10),
        # Section heading
        FontSpan(text="Installing Python", font_name="Serif", font_size=15.0, is_bold=True, page_num=10),
        # Body text
        FontSpan(text="Python is a versatile programming language.", font_name="Serif", font_size=10.0, page_num=10),
        FontSpan(text="It supports multiple paradigms.", font_name="Serif", font_size=10.0, page_num=10),
        # Code block
        FontSpan(text=">>> print('hello')", font_name="Courier", font_size=9.0, is_monospace=True, page_num=10),
        FontSpan(text="hello", font_name="Courier", font_size=9.0, is_monospace=True, page_num=10),
        # Note callout
        FontSpan(text="Note: Python 3 is recommended.", font_name="Serif", font_size=10.0, page_num=11),
        # Subsection heading
        FontSpan(text="First Steps", font_name="Serif", font_size=12.5, is_bold=True, page_num=11),
        # List item
        FontSpan(text="- Open a terminal", font_name="Serif", font_size=10.0, page_num=11),
        # More code
        FontSpan(text="x = 42", font_name="Courier", font_size=9.0, is_monospace=True, page_num=11),
        FontSpan(text="print(x)", font_name="Courier", font_size=9.0, is_monospace=True, page_num=11),
        # Warning callout
        FontSpan(text="Warning: Do not use Python 2.", font_name="Serif", font_size=10.0, page_num=11),
        # Code separator so Warning and Tip don't merge
        FontSpan(text="python --version", font_name="Courier", font_size=9.0, is_monospace=True, page_num=11),
        # Tip callout
        FontSpan(text="Tip: Use a virtual environment.", font_name="Serif", font_size=10.0, page_num=11),
    ]


@pytest.fixture
def sample_book() -> Book:
    """A minimal Book with one chapter for serialization tests."""
    return Book(
        book_id="test_book",
        title="Test Book",
        pdf_path="/tmp/test.pdf",
        profile_name="test",
        language="python",
        total_pages=100,
        chapters=[
            Chapter(
                chapter_num=1,
                title="Introduction",
                start_page=1,
                end_page=20,
                content_blocks=[
                    ContentBlock(
                        block_type=BlockType.HEADING1, text="Introduction", page_num=1, font_size=22.0, is_bold=True
                    ),
                    ContentBlock(block_type=BlockType.BODY, text="Welcome to Python.", page_num=1, font_size=10.0),
                    ContentBlock(
                        block_type=BlockType.CODE,
                        text="print('hello')",
                        page_num=2,
                        is_monospace=True,
                        block_id="code_0",
                    ),
                ],
                sections=[
                    Section(title="Introduction", level=1, page_num=1, block_index=0),
                ],
            ),
        ],
    )
