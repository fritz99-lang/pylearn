"""Integration tests: full parser pipeline from FontSpans to rendered HTML."""

from __future__ import annotations

import pytest

from pylearn.core.models import BlockType, Book, ContentBlock, FontSpan
from pylearn.parser.book_profiles import BookProfile
from pylearn.parser.code_extractor import CodeExtractor
from pylearn.parser.content_classifier import ContentClassifier
from pylearn.parser.structure_detector import StructureDetector
from pylearn.renderer.html_renderer import HTMLRenderer
from pylearn.renderer.theme import get_theme


class TestFullPipeline:
    """Run the full pipeline: classify → extract → structure → render."""

    def test_spans_to_html_all_block_types(self, sample_profile: BookProfile, sample_spans: list[FontSpan]) -> None:
        """Verify all expected block types survive the full pipeline."""
        classifier = ContentClassifier(sample_profile)
        extractor = CodeExtractor()
        detector = StructureDetector(sample_profile)

        # Step 1: Classify spans into blocks
        classifier.classify_page_spans(sample_spans, page_num=10)
        # Also classify page 11 spans
        page11_spans = [s for s in sample_spans if s.page_num == 11]
        page10_spans = [s for s in sample_spans if s.page_num == 10]
        all_blocks = classifier.classify_all_pages([page10_spans, page11_spans], start_page_offset=10)
        assert len(all_blocks) > 0

        # Step 2: Extract/merge code and assign IDs
        processed = extractor.process(all_blocks)

        # Verify expected block types are present
        types_present = {b.block_type for b in processed}
        assert BlockType.HEADING1 in types_present
        assert BlockType.HEADING2 in types_present
        assert BlockType.HEADING3 in types_present
        assert BlockType.BODY in types_present
        assert BlockType.NOTE in types_present
        assert BlockType.WARNING in types_present
        assert BlockType.TIP in types_present
        assert BlockType.LIST_ITEM in types_present
        # Code (either CODE or CODE_REPL)
        assert BlockType.CODE in types_present or BlockType.CODE_REPL in types_present

        # Verify code blocks have IDs
        code_blocks = [b for b in processed if b.block_type in (BlockType.CODE, BlockType.CODE_REPL)]
        assert all(b.block_id for b in code_blocks)

        # Verify heading blocks have IDs
        heading_blocks = [
            b for b in processed if b.block_type in (BlockType.HEADING1, BlockType.HEADING2, BlockType.HEADING3)
        ]
        assert all(b.block_id for b in heading_blocks)

        # Step 3: Detect structure
        chapters = detector.detect_chapters(processed)
        assert len(chapters) >= 1
        assert chapters[0].title.strip() != ""
        assert len(chapters[0].content_blocks) > 0

        # Step 4: Render each chapter to HTML
        renderer = HTMLRenderer()
        for chapter in chapters:
            html = renderer.render_blocks(chapter.content_blocks)
            assert "<html>" in html
            assert "</html>" in html
            assert len(html) > 100  # non-trivial output

    def test_empty_spans_produce_no_chapters(self, sample_profile: BookProfile) -> None:
        """Empty input should flow through without errors."""
        classifier = ContentClassifier(sample_profile)
        extractor = CodeExtractor()
        detector = StructureDetector(sample_profile)

        blocks = classifier.classify_all_pages([])
        processed = extractor.process(blocks)
        chapters = detector.detect_chapters(processed)
        assert chapters == []


class TestThemeRendering:
    """All three themes render the same blocks without errors."""

    @pytest.mark.parametrize("theme_name", ["light", "dark", "sepia"])
    def test_theme_renders_without_error(
        self, theme_name: str, sample_profile: BookProfile, sample_spans: list[FontSpan]
    ) -> None:
        classifier = ContentClassifier(sample_profile)
        extractor = CodeExtractor()
        blocks = classifier.classify_all_pages(
            [[s for s in sample_spans if s.page_num == 10], [s for s in sample_spans if s.page_num == 11]],
            start_page_offset=10,
        )
        processed = extractor.process(blocks)

        theme = get_theme(theme_name)
        renderer = HTMLRenderer(theme=theme)
        html = renderer.render_blocks(processed)

        assert "<html>" in html
        assert theme.bg_color in html
        assert len(html) > 200

    def test_unknown_theme_falls_back_to_light(self) -> None:
        theme = get_theme("nonexistent_theme")
        renderer = HTMLRenderer(theme=theme)
        html = renderer.render_welcome()
        assert "PyLearn" in html


class TestBookSerialization:
    """Book round-trip: to_dict → from_dict."""

    def test_round_trip(self, sample_book: Book) -> None:
        data = sample_book.to_dict()
        restored = Book.from_dict(data)

        assert restored.book_id == sample_book.book_id
        assert restored.title == sample_book.title
        assert restored.pdf_path == sample_book.pdf_path
        assert restored.profile_name == sample_book.profile_name
        assert restored.language == sample_book.language
        assert restored.total_pages == sample_book.total_pages
        assert len(restored.chapters) == len(sample_book.chapters)

        ch_orig = sample_book.chapters[0]
        ch_rest = restored.chapters[0]
        assert ch_rest.chapter_num == ch_orig.chapter_num
        assert ch_rest.title == ch_orig.title
        assert len(ch_rest.content_blocks) == len(ch_orig.content_blocks)
        assert len(ch_rest.sections) == len(ch_orig.sections)

        # Verify content block fidelity
        for orig, rest in zip(ch_orig.content_blocks, ch_rest.content_blocks):
            assert rest.block_type == orig.block_type
            assert rest.text == orig.text

    def test_round_trip_preserves_block_ids(self, sample_book: Book) -> None:
        data = sample_book.to_dict()
        restored = Book.from_dict(data)
        orig_ids = [b.block_id for b in sample_book.chapters[0].content_blocks]
        rest_ids = [b.block_id for b in restored.chapters[0].content_blocks]
        assert orig_ids == rest_ids

    def test_large_book_round_trip(self) -> None:
        """A book with many chapters survives serialization."""
        chapters = []
        for i in range(25):
            chapters.append(
                __import__("pylearn.core.models", fromlist=["Chapter"]).Chapter(
                    chapter_num=i + 1,
                    title=f"Chapter {i + 1}: Topic {i + 1}",
                    start_page=i * 20,
                    end_page=(i + 1) * 20,
                    content_blocks=[
                        ContentBlock(block_type=BlockType.HEADING1, text=f"Chapter {i + 1}", page_num=i * 20),
                        ContentBlock(block_type=BlockType.BODY, text=f"Body text for chapter {i + 1}", page_num=i * 20),
                    ],
                )
            )
        book = Book(
            book_id="big_book",
            title="Big Book",
            pdf_path="/tmp/big.pdf",
            total_pages=500,
            chapters=chapters,
        )
        data = book.to_dict()
        restored = Book.from_dict(data)
        assert len(restored.chapters) == 25
        assert restored.chapters[24].title == "Chapter 25: Topic 25"
