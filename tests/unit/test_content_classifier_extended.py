"""Extended tests for ContentClassifier — classify_all_pages and _interleave_images.

These fill gaps not covered by the existing test_parser.py tests.
"""

from __future__ import annotations

import pytest

from pylearn.core.models import BlockType, ContentBlock, FontSpan
from pylearn.parser.book_profiles import BookProfile
from pylearn.parser.content_classifier import ContentClassifier


@pytest.fixture
def profile():
    return BookProfile(
        name="test",
        heading1_min_size=20.0,
        heading2_min_size=14.0,
        heading3_min_size=12.0,
        body_size=10.0,
        code_size=8.5,
    )


@pytest.fixture
def classifier(profile):
    return ContentClassifier(profile)


def _span(text, font="Serif", size=10.0, bold=False, mono=False, page=0):
    return FontSpan(
        text=text,
        font_name=font,
        font_size=size,
        is_bold=bold,
        is_monospace=mono,
        page_num=page,
    )


# ===========================================================================
# classify_all_pages
# ===========================================================================


class TestClassifyAllPages:
    def test_basic_multi_page(self, classifier):
        pages = [
            [_span("Chapter 1: Getting Started with Python", size=22.0, bold=True, page=0)],
            [_span("Body text here.", page=1)],
        ]
        blocks = classifier.classify_all_pages(pages, start_page_offset=5)
        assert len(blocks) == 2
        assert blocks[0].block_type == BlockType.HEADING1
        assert blocks[0].page_num == 5
        assert blocks[1].block_type == BlockType.BODY
        assert blocks[1].page_num == 6

    def test_empty_pages(self, classifier):
        blocks = classifier.classify_all_pages([[], [], []])
        assert blocks == []

    def test_with_page_images(self, classifier):
        pages = [
            [_span("Some text", page=0)],
        ]
        page_images = {
            0: [{"filename": "fig1.png", "y0": 50, "page_num": 0, "width": 200, "height": 100}],
        }
        blocks = classifier.classify_all_pages(pages, page_images=page_images)
        types = [b.block_type for b in blocks]
        assert BlockType.FIGURE in types

    def test_images_on_nonexistent_page_ignored(self, classifier):
        pages = [[_span("Text", page=0)]]
        page_images = {
            5: [{"filename": "fig.png", "y0": 50, "page_num": 5, "width": 200, "height": 100}],
        }
        blocks = classifier.classify_all_pages(pages, page_images=page_images)
        types = [b.block_type for b in blocks]
        assert BlockType.FIGURE not in types

    def test_preserves_block_order(self, classifier):
        pages = [
            [
                _span("Heading", size=22.0, bold=True, page=0),
                _span("Body", page=0),
                _span("code()", font="Courier", mono=True, page=0),
            ],
        ]
        blocks = classifier.classify_all_pages(pages)
        types = [b.block_type for b in blocks]
        assert types == [BlockType.HEADING1, BlockType.BODY, BlockType.CODE]


# ===========================================================================
# _interleave_images
# ===========================================================================


class TestInterleaveImages:
    def test_no_images_returns_original(self):
        blocks = [ContentBlock(block_type=BlockType.BODY, text="Text", page_num=0)]
        result = ContentClassifier._interleave_images(blocks, [], 0)
        assert result == blocks

    def test_images_inserted_by_y_position(self):
        blocks = [
            ContentBlock(block_type=BlockType.BODY, text="First", page_num=0),
            ContentBlock(block_type=BlockType.BODY, text="Second", page_num=0),
        ]
        images = [
            {"filename": "fig.png", "y0": 400, "page_num": 0, "width": 200, "height": 100},
        ]
        result = ContentClassifier._interleave_images(blocks, images, 0)
        types = [b.block_type for b in result]
        assert BlockType.FIGURE in types
        assert len(result) == 3

    def test_images_at_end_when_y_large(self):
        blocks = [ContentBlock(block_type=BlockType.BODY, text="Only block", page_num=0)]
        images = [
            {"filename": "bottom.png", "y0": 900, "page_num": 0, "width": 200, "height": 100},
        ]
        result = ContentClassifier._interleave_images(blocks, images, 0, page_height=792.0)
        assert result[-1].block_type == BlockType.FIGURE
        assert result[-1].text == "bottom.png"

    def test_multiple_images_sorted(self):
        blocks = [ContentBlock(block_type=BlockType.BODY, text="Text", page_num=0)]
        images = [
            {"filename": "b.png", "y0": 500, "page_num": 0, "width": 200, "height": 100},
            {"filename": "a.png", "y0": 100, "page_num": 0, "width": 200, "height": 100},
        ]
        result = ContentClassifier._interleave_images(blocks, images, 0)
        figure_blocks = [b for b in result if b.block_type == BlockType.FIGURE]
        # Should be sorted by y0: a.png first, then b.png
        assert figure_blocks[0].text == "a.png"
        assert figure_blocks[1].text == "b.png"

    def test_empty_blocks_with_images(self):
        images = [
            {"filename": "fig.png", "y0": 100, "page_num": 0, "width": 200, "height": 100},
        ]
        result = ContentClassifier._interleave_images([], images, 0)
        assert len(result) == 1
        assert result[0].block_type == BlockType.FIGURE


# ===========================================================================
# classify_page_spans — hyphen rejoining
# ===========================================================================


class TestHyphenRejoining:
    def test_hyphenated_words_rejoined(self, classifier):
        spans = [_span("com- municate")]
        blocks = classifier.classify_page_spans(spans)
        assert "communicate" in blocks[0].text

    def test_code_blocks_not_rejoined(self, classifier):
        spans = [_span("some- thing", font="Courier", mono=True)]
        blocks = classifier.classify_page_spans(spans)
        # Code blocks should preserve the hyphen
        assert "some- thing" in blocks[0].text or "some-" in blocks[0].text
