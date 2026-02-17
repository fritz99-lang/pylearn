"""Tests for parser components with synthetic data."""

import pytest
from pylearn.core.models import BlockType, ContentBlock, FontSpan
from pylearn.parser.book_profiles import BookProfile
from pylearn.parser.content_classifier import ContentClassifier
from pylearn.parser.code_extractor import CodeExtractor
from pylearn.parser.structure_detector import StructureDetector


def make_profile(**overrides) -> BookProfile:
    """Create a test book profile with sensible defaults."""
    defaults = dict(
        name="test",
        heading1_min_size=20.0,
        heading2_min_size=14.0,
        heading3_min_size=12.0,
        body_size=10.0,
        code_size=8.5,
        chapter_pattern=r"^Chapter\s+(\d+)\s*[\.:]",
    )
    defaults.update(overrides)
    return BookProfile(**defaults)


def make_span(text, font_size=10.0, is_bold=False, is_monospace=False,
              page_num=0, font_name="Serif") -> FontSpan:
    """Create a test FontSpan."""
    return FontSpan(
        text=text,
        font_name=font_name,
        font_size=font_size,
        is_bold=is_bold,
        is_monospace=is_monospace,
        page_num=page_num,
    )


# --- ContentClassifier ---

class TestContentClassifierSpan:
    def setup_method(self):
        self.profile = make_profile()
        self.classifier = ContentClassifier(self.profile)

    def test_monospace_is_code(self):
        span = make_span("print('hello')", is_monospace=True)
        assert self.classifier.classify_span(span) == BlockType.CODE

    def test_large_font_is_heading1(self):
        span = make_span("Big Title", font_size=22.0)
        assert self.classifier.classify_span(span) == BlockType.HEADING1

    def test_medium_bold_is_heading2(self):
        span = make_span("Section", font_size=15.0, is_bold=True)
        assert self.classifier.classify_span(span) == BlockType.HEADING2

    def test_small_bold_is_heading3(self):
        span = make_span("Subsection", font_size=12.5, is_bold=True)
        assert self.classifier.classify_span(span) == BlockType.HEADING3

    def test_normal_text_is_body(self):
        span = make_span("Normal text", font_size=10.0)
        assert self.classifier.classify_span(span) == BlockType.BODY

    def test_medium_non_bold_is_body(self):
        # Medium font but NOT bold → should be body, not heading
        span = make_span("Not bold", font_size=14.0, is_bold=False)
        assert self.classifier.classify_span(span) == BlockType.BODY


class TestContentClassifierPage:
    def setup_method(self):
        self.profile = make_profile()
        self.classifier = ContentClassifier(self.profile)

    def test_empty_page(self):
        assert self.classifier.classify_page_spans([]) == []

    def test_merges_adjacent_body(self):
        spans = [
            make_span("Hello "),
            make_span("world"),
        ]
        blocks = self.classifier.classify_page_spans(spans)
        assert len(blocks) == 1
        assert blocks[0].block_type == BlockType.BODY
        assert "Hello" in blocks[0].text
        assert "world" in blocks[0].text

    def test_separates_different_types(self):
        spans = [
            make_span("Title", font_size=22.0),
            make_span("Body text"),
            make_span("code()", is_monospace=True),
        ]
        blocks = self.classifier.classify_page_spans(spans)
        assert len(blocks) == 3
        assert blocks[0].block_type == BlockType.HEADING1
        assert blocks[1].block_type == BlockType.BODY
        assert blocks[2].block_type == BlockType.CODE

    def test_filters_page_headers(self):
        # Standalone page number on its own (different type from adjacent content)
        spans = [
            make_span("42", font_size=22.0),  # heading-sized → separate block → filtered
            make_span("Real content", font_size=10.0),
        ]
        blocks = self.classifier.classify_page_spans(spans, page_num=42)
        # "42" heading block should be filtered; only body "Real content" remains
        assert len(blocks) == 1
        assert blocks[0].text == "Real content"

    def test_filters_standalone_page_number(self):
        # A page with only a page number → completely filtered
        spans = [make_span("42")]
        blocks = self.classifier.classify_page_spans(spans, page_num=42)
        assert len(blocks) == 0

    def test_detects_repl_code(self):
        spans = [
            make_span(">>> x = 1", is_monospace=True),
            make_span(">>> print(x)", is_monospace=True),
            make_span("1", is_monospace=True),
        ]
        blocks = self.classifier.classify_page_spans(spans)
        assert len(blocks) == 1
        assert blocks[0].block_type == BlockType.CODE_REPL

    def test_classify_all_pages(self):
        pages = [
            [make_span("Page 1 text")],
            [make_span("Page 2 text")],
        ]
        blocks = self.classifier.classify_all_pages(pages, start_page_offset=10)
        assert len(blocks) == 2
        assert blocks[0].page_num == 10
        assert blocks[1].page_num == 11


# --- List / Note / Warning / Tip Detection ---

class TestListDetection:
    def setup_method(self):
        self.profile = make_profile()
        self.classifier = ContentClassifier(self.profile)

    def test_bullet_list(self):
        spans = [make_span("- First item"), make_span("- Second item")]
        blocks = self.classifier.classify_page_spans(spans)
        # Both merge into one body block, then the merged block starts with "- "
        list_blocks = [b for b in blocks if b.block_type == BlockType.LIST_ITEM]
        assert len(list_blocks) >= 1

    def test_numbered_list(self):
        spans = [make_span("1. First step")]
        blocks = self.classifier.classify_page_spans(spans)
        assert blocks[0].block_type == BlockType.LIST_ITEM

    def test_bullet_unicode(self):
        spans = [make_span("\u2022 Bullet point")]
        blocks = self.classifier.classify_page_spans(spans)
        assert blocks[0].block_type == BlockType.LIST_ITEM

    def test_asterisk_list(self):
        spans = [make_span("* star item")]
        blocks = self.classifier.classify_page_spans(spans)
        assert blocks[0].block_type == BlockType.LIST_ITEM

    def test_normal_body_not_list(self):
        spans = [make_span("This is a normal paragraph.")]
        blocks = self.classifier.classify_page_spans(spans)
        assert blocks[0].block_type == BlockType.BODY


class TestNoteWarningTipDetection:
    def setup_method(self):
        self.profile = make_profile()
        self.classifier = ContentClassifier(self.profile)

    def test_note_detection(self):
        spans = [make_span("Note: This is important information.")]
        blocks = self.classifier.classify_page_spans(spans)
        assert blocks[0].block_type == BlockType.NOTE
        assert "Note:" not in blocks[0].text
        assert "important" in blocks[0].text

    def test_warning_detection(self):
        spans = [make_span("Warning: Do not do this.")]
        blocks = self.classifier.classify_page_spans(spans)
        assert blocks[0].block_type == BlockType.WARNING
        assert "Warning:" not in blocks[0].text

    def test_caution_detection(self):
        spans = [make_span("Caution: Be careful here.")]
        blocks = self.classifier.classify_page_spans(spans)
        assert blocks[0].block_type == BlockType.WARNING

    def test_tip_detection(self):
        spans = [make_span("Tip: Use this shortcut.")]
        blocks = self.classifier.classify_page_spans(spans)
        assert blocks[0].block_type == BlockType.TIP
        assert "Tip:" not in blocks[0].text

    def test_case_insensitive(self):
        spans = [make_span("NOTE: uppercase note")]
        blocks = self.classifier.classify_page_spans(spans)
        assert blocks[0].block_type == BlockType.NOTE

    def test_normal_body_not_note(self):
        spans = [make_span("Noted that this works fine.")]
        blocks = self.classifier.classify_page_spans(spans)
        # "Noted" should NOT be detected as a Note (different word)
        assert blocks[0].block_type == BlockType.BODY


# --- CodeExtractor ---

class TestCodeExtractor:
    def setup_method(self):
        self.extractor = CodeExtractor()

    def test_merges_adjacent_code(self):
        blocks = [
            ContentBlock(block_type=BlockType.CODE, text="line 1", page_num=1),
            ContentBlock(block_type=BlockType.CODE, text="line 2", page_num=1),
            ContentBlock(block_type=BlockType.BODY, text="Some text"),
            ContentBlock(block_type=BlockType.CODE, text="line 3", page_num=2),
        ]
        result = self.extractor.process(blocks)
        # Two code blocks after merge (1+2 merged, 3 separate)
        code_blocks = [b for b in result if b.block_type in (BlockType.CODE, BlockType.CODE_REPL)]
        assert len(code_blocks) == 2
        assert "line 1" in code_blocks[0].text
        assert "line 2" in code_blocks[0].text
        assert "line 3" in code_blocks[1].text

    def test_assigns_code_ids(self):
        blocks = [
            ContentBlock(block_type=BlockType.CODE, text="code block"),
            ContentBlock(block_type=BlockType.BODY, text="text"),
            ContentBlock(block_type=BlockType.CODE, text="another code"),
        ]
        result = self.extractor.process(blocks)
        code_blocks = [b for b in result if b.block_type in (BlockType.CODE, BlockType.CODE_REPL)]
        assert code_blocks[0].block_id == "code_0"
        assert code_blocks[1].block_id == "code_1"

    def test_assigns_heading_ids(self):
        blocks = [
            ContentBlock(block_type=BlockType.HEADING1, text="Title"),
            ContentBlock(block_type=BlockType.HEADING2, text="Section"),
            ContentBlock(block_type=BlockType.BODY, text="text"),
        ]
        result = self.extractor.process(blocks)
        assert result[0].block_id == "heading_0"
        assert result[1].block_id == "heading_1"

    def test_empty_input(self):
        assert self.extractor.process([]) == []

    def test_extract_runnable_code(self):
        blocks = [
            ContentBlock(block_type=BlockType.CODE, text="x"),  # too short
            ContentBlock(block_type=BlockType.CODE, text="import os\nprint('hello')"),
            ContentBlock(block_type=BlockType.BODY, text="not code"),
        ]
        runnable = self.extractor.extract_runnable_code(blocks)
        assert len(runnable) == 1
        assert "import os" in runnable[0].text


# --- StructureDetector ---

class TestStructureDetector:
    def setup_method(self):
        self.profile = make_profile()
        self.detector = StructureDetector(self.profile)

    def test_detects_chapters_by_regex(self):
        blocks = [
            ContentBlock(block_type=BlockType.HEADING1, text="Chapter 1: Intro", font_size=22.0),
            ContentBlock(block_type=BlockType.BODY, text="Content of chapter 1"),
            ContentBlock(block_type=BlockType.HEADING1, text="Chapter 2: Types", font_size=22.0),
            ContentBlock(block_type=BlockType.BODY, text="Content of chapter 2"),
        ]
        chapters = self.detector.detect_chapters(blocks)
        assert len(chapters) == 2
        assert chapters[0].chapter_num == 1
        assert chapters[0].title == "Chapter 1: Intro"
        assert chapters[1].chapter_num == 2

    def test_detects_chapters_by_font_size(self):
        # Use a pattern that won't match, forcing font-size detection
        profile = make_profile(chapter_pattern=r"^ZZZZZ(\d+)")
        detector = StructureDetector(profile)
        blocks = [
            ContentBlock(block_type=BlockType.HEADING1, text="First Part", font_size=22.0, page_num=1),
            ContentBlock(block_type=BlockType.BODY, text="Content"),
            ContentBlock(block_type=BlockType.HEADING1, text="Second Part", font_size=22.0, page_num=20),
            ContentBlock(block_type=BlockType.BODY, text="More content"),
        ]
        chapters = detector.detect_chapters(blocks)
        assert len(chapters) == 2

    def test_empty_blocks(self):
        assert self.detector.detect_chapters([]) == []

    def test_no_headings_single_chapter(self):
        blocks = [
            ContentBlock(block_type=BlockType.BODY, text="Just body text"),
            ContentBlock(block_type=BlockType.CODE, text="print('hi')"),
        ]
        chapters = self.detector.detect_chapters(blocks)
        assert len(chapters) == 1
        assert chapters[0].title == "Content"
        assert len(chapters[0].content_blocks) == 2

    def test_detects_sections(self):
        blocks = [
            ContentBlock(block_type=BlockType.HEADING1, text="Chapter Title", font_size=22.0),
            ContentBlock(block_type=BlockType.BODY, text="Intro text"),
            ContentBlock(block_type=BlockType.HEADING2, text="Section A", font_size=15.0),
            ContentBlock(block_type=BlockType.BODY, text="Section A content"),
            ContentBlock(block_type=BlockType.HEADING3, text="Subsection A.1", font_size=12.5),
            ContentBlock(block_type=BlockType.BODY, text="Subsection content"),
        ]
        chapters = self.detector.detect_chapters(blocks)
        # Should detect sections within the chapter
        assert len(chapters) >= 1
        sections = chapters[0].sections
        # Should have at least the HEADING1 as a top-level section
        assert len(sections) >= 1

    def test_chapter_content_blocks_assigned(self):
        blocks = [
            ContentBlock(block_type=BlockType.HEADING1, text="Chapter 1: A", font_size=22.0),
            ContentBlock(block_type=BlockType.BODY, text="AAA"),
            ContentBlock(block_type=BlockType.HEADING1, text="Chapter 2: B", font_size=22.0),
            ContentBlock(block_type=BlockType.BODY, text="BBB"),
        ]
        chapters = self.detector.detect_chapters(blocks)
        assert "AAA" in chapters[0].content_blocks[1].text
        assert "BBB" in chapters[1].content_blocks[1].text


# --- BookProfile ---

class TestBookProfile:
    def test_is_monospace(self):
        profile = make_profile()
        assert profile.is_monospace("CourierNew") is True
        assert profile.is_monospace("DejaVuSansMono-Bold") is True
        assert profile.is_monospace("TimesNewRoman") is False
        assert profile.is_monospace("Consolas") is True
        assert profile.is_monospace("Arial") is False
