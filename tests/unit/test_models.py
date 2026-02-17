"""Tests for data model serialization round-trips."""

import pytest
from pylearn.core.models import (
    BlockType, ContentBlock, Section, Chapter, Book, Exercise, FontSpan,
)


class TestContentBlock:
    def test_round_trip(self):
        block = ContentBlock(
            block_type=BlockType.CODE,
            text="print('hello')",
            page_num=42,
            font_size=9.5,
            is_bold=False,
            is_monospace=True,
            block_id="code_7",
            language="python",
        )
        d = block.to_dict()
        restored = ContentBlock.from_dict(d)
        assert restored.block_type == block.block_type
        assert restored.text == block.text
        assert restored.page_num == block.page_num
        assert restored.font_size == block.font_size
        assert restored.is_bold == block.is_bold
        assert restored.is_monospace == block.is_monospace
        assert restored.block_id == block.block_id
        assert restored.language == block.language

    def test_round_trip_heading(self):
        block = ContentBlock(
            block_type=BlockType.HEADING1,
            text="Chapter 1: Intro",
            page_num=1,
            font_size=20.0,
            is_bold=True,
            block_id="heading_0",
        )
        restored = ContentBlock.from_dict(block.to_dict())
        assert restored.block_type == BlockType.HEADING1
        assert restored.text == "Chapter 1: Intro"
        assert restored.is_bold is True

    def test_defaults(self):
        data = {"block_type": "body", "text": "Hello"}
        block = ContentBlock.from_dict(data)
        assert block.page_num == 0
        assert block.font_size == 0.0
        assert block.is_bold is False
        assert block.is_monospace is False
        assert block.block_id == ""
        assert block.language == "python"

    def test_all_block_types(self):
        for bt in BlockType:
            block = ContentBlock(block_type=bt, text="test")
            d = block.to_dict()
            assert d["block_type"] == bt.value
            restored = ContentBlock.from_dict(d)
            assert restored.block_type == bt

    def test_figure_round_trip(self):
        block = ContentBlock(
            block_type=BlockType.FIGURE,
            text="p42_abc123def4.png",
            page_num=42,
        )
        d = block.to_dict()
        assert d["block_type"] == "figure"
        restored = ContentBlock.from_dict(d)
        assert restored.block_type == BlockType.FIGURE
        assert restored.text == "p42_abc123def4.png"


class TestSection:
    def test_round_trip(self):
        section = Section(
            title="Variables",
            level=2,
            page_num=10,
            block_index=5,
            children=[
                Section(title="Naming Rules", level=3, page_num=11, block_index=8),
            ],
        )
        d = section.to_dict()
        restored = Section.from_dict(d)
        assert restored.title == "Variables"
        assert restored.level == 2
        assert restored.page_num == 10
        assert restored.block_index == 5
        assert len(restored.children) == 1
        assert restored.children[0].title == "Naming Rules"
        assert restored.children[0].level == 3

    def test_no_children(self):
        section = Section(title="Leaf", level=3, page_num=1, block_index=0)
        restored = Section.from_dict(section.to_dict())
        assert restored.children == []


class TestChapter:
    def test_round_trip(self):
        chapter = Chapter(
            chapter_num=3,
            title="Chapter 3: Functions",
            start_page=50,
            end_page=80,
            content_blocks=[
                ContentBlock(block_type=BlockType.HEADING1, text="Functions"),
                ContentBlock(block_type=BlockType.BODY, text="Functions are reusable..."),
                ContentBlock(block_type=BlockType.CODE, text="def greet(): pass"),
            ],
            sections=[
                Section(title="Functions", level=1, page_num=50, block_index=0),
            ],
        )
        d = chapter.to_dict()
        restored = Chapter.from_dict(d)
        assert restored.chapter_num == 3
        assert restored.title == "Chapter 3: Functions"
        assert restored.start_page == 50
        assert restored.end_page == 80
        assert len(restored.content_blocks) == 3
        assert restored.content_blocks[2].block_type == BlockType.CODE
        assert len(restored.sections) == 1

    def test_empty_chapter(self):
        chapter = Chapter(chapter_num=0, title="Empty", start_page=0, end_page=0)
        restored = Chapter.from_dict(chapter.to_dict())
        assert restored.content_blocks == []
        assert restored.sections == []


class TestBook:
    def test_round_trip(self):
        book = Book(
            book_id="test_book",
            title="Test Book",
            pdf_path="/path/to/test.pdf",
            profile_name="learning_python",
            language="python",
            total_pages=500,
            chapters=[
                Chapter(
                    chapter_num=1,
                    title="Chapter 1",
                    start_page=1,
                    end_page=20,
                    content_blocks=[
                        ContentBlock(block_type=BlockType.BODY, text="Hello world"),
                    ],
                ),
            ],
        )
        d = book.to_dict()
        restored = Book.from_dict(d)
        assert restored.book_id == "test_book"
        assert restored.title == "Test Book"
        assert restored.pdf_path == "/path/to/test.pdf"
        assert restored.profile_name == "learning_python"
        assert restored.language == "python"
        assert restored.total_pages == 500
        assert len(restored.chapters) == 1
        assert restored.chapters[0].title == "Chapter 1"

    def test_language_defaults_to_python(self):
        data = {
            "book_id": "x",
            "title": "X",
            "pdf_path": "/x.pdf",
            "language": "python",
            "total_pages": 10,
        }
        book = Book.from_dict(data)
        assert book.language == "python"

    def test_empty_book(self):
        book = Book(book_id="empty", title="Empty", pdf_path="/e.pdf")
        restored = Book.from_dict(book.to_dict())
        assert restored.chapters == []
        assert restored.total_pages == 0


class TestExercise:
    def test_round_trip(self):
        ex = Exercise(
            exercise_id="ex_1_1",
            book_id="test",
            chapter_num=1,
            title="Exercise 1",
            description="Write a function that...",
            exercise_type="exercise",
            answer="def solution(): pass",
            page_num=42,
        )
        d = ex.to_dict()
        restored = Exercise.from_dict(d)
        assert restored.exercise_id == "ex_1_1"
        assert restored.answer == "def solution(): pass"
        assert restored.page_num == 42

    def test_no_answer(self):
        ex = Exercise(
            exercise_id="q1", book_id="b", chapter_num=1,
            title="Q1", description="What is...", exercise_type="quiz",
        )
        restored = Exercise.from_dict(ex.to_dict())
        assert restored.answer is None
