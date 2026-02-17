# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Unit tests for BookController — book loading, navigation, and progress tracking.

BookController is the core workflow coordinator. These tests use a real
Database (pointing at a tmp_path SQLite file) and a mock CacheManager/BooksConfig,
exercising the full load-navigate-complete lifecycle without a Qt event loop.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pylearn.core.constants import STATUS_IN_PROGRESS, STATUS_COMPLETED
from pylearn.core.database import Database
from pylearn.core.models import (
    BlockType, Book, Chapter, ContentBlock, Section,
)
from pylearn.ui.book_controller import BookController


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_test_book(
    book_id: str = "test_book",
    title: str = "Test Book",
    language: str = "python",
    num_chapters: int = 3,
) -> Book:
    """Create a synthetic Book with *num_chapters* chapters for testing."""
    chapters: list[Chapter] = []
    for i in range(1, num_chapters + 1):
        blocks = [
            ContentBlock(
                block_type=BlockType.HEADING1,
                text=f"Chapter {i}",
                block_id=f"heading_{i}",
            ),
            ContentBlock(
                block_type=BlockType.BODY,
                text=f"Chapter {i} content paragraph.",
                block_id=f"body_{i}",
            ),
            ContentBlock(
                block_type=BlockType.CODE,
                text=f"print('chapter {i}')",
                block_id=f"code_{i}",
            ),
        ]
        sections = [
            Section(
                title=f"Section {i}.1",
                level=2,
                page_num=i * 10,
                block_index=0,
            ),
        ]
        chapters.append(
            Chapter(
                chapter_num=i,
                title=f"Chapter {i}",
                start_page=i * 10,
                end_page=i * 10 + 9,
                sections=sections,
                content_blocks=blocks,
            )
        )
    return Book(
        book_id=book_id,
        title=title,
        pdf_path="/tmp/test.pdf",
        profile_name="test",
        language=language,
        total_pages=num_chapters * 10,
        chapters=chapters,
    )


@pytest.fixture
def db(tmp_path: Path) -> Database:
    """Provide a real Database backed by a temporary SQLite file."""
    return Database(db_path=tmp_path / "test.db")


@pytest.fixture
def cache() -> MagicMock:
    """Provide a mock CacheManager."""
    mock = MagicMock()
    mock.image_dir.return_value = Path("/tmp/images")
    return mock


@pytest.fixture
def books_config() -> MagicMock:
    """Provide a mock BooksConfig."""
    return MagicMock()


@pytest.fixture
def controller(db: Database, cache: MagicMock, books_config: MagicMock) -> BookController:
    """Provide a BookController wired to real DB and mock config/cache."""
    return BookController(db=db, cache=cache, books_config=books_config)


# ---------------------------------------------------------------------------
# Book loading
# ---------------------------------------------------------------------------

class TestLoadBook:
    """Tests for BookController.load_book()."""

    def test_load_book_sets_current_book(
        self, controller: BookController, db: Database,
    ) -> None:
        book = make_test_book()
        controller.load_book(book)
        assert controller.current_book is book

    def test_load_book_sets_language(self, controller: BookController) -> None:
        book = make_test_book(language="cpp")
        controller.load_book(book)
        assert controller.current_language == "cpp"

    def test_load_book_emits_book_loaded(self, controller: BookController) -> None:
        book = make_test_book()
        received: list[object] = []
        controller.book_loaded.connect(received.append)
        controller.load_book(book)
        assert len(received) == 1
        assert received[0] is book

    def test_load_book_emits_language_changed(self, controller: BookController) -> None:
        book = make_test_book(language="html")
        received: list[str] = []
        controller.language_changed.connect(received.append)
        controller.load_book(book)
        assert received == ["html"]

    def test_load_book_emits_progress_updated(self, controller: BookController) -> None:
        book = make_test_book()
        received: list[str] = []
        controller.progress_updated.connect(received.append)
        controller.load_book(book)
        # Fresh book with no completed chapters -> 0% complete
        assert len(received) >= 1
        assert "0% complete" in received[0]

    def test_load_book_registers_book_in_db(
        self, controller: BookController, db: Database,
    ) -> None:
        book = make_test_book()
        controller.load_book(book)
        rows = db.get_books()
        assert len(rows) == 1
        assert rows[0]["book_id"] == "test_book"
        assert rows[0]["total_chapters"] == 3

    def test_load_book_registers_chapters_in_db(
        self, controller: BookController, db: Database,
    ) -> None:
        book = make_test_book()
        controller.load_book(book)
        chapters = db.get_chapters("test_book")
        assert len(chapters) == 3
        titles = [ch["title"] for ch in chapters]
        assert titles == ["Chapter 1", "Chapter 2", "Chapter 3"]

    def test_load_book_navigates_to_first_chapter(
        self, controller: BookController,
    ) -> None:
        book = make_test_book()
        controller.load_book(book)
        # Should auto-navigate to chapter 1
        assert controller.current_chapter_num == 1

    def test_load_book_restores_last_position(
        self, controller: BookController, db: Database,
    ) -> None:
        """When a last_position exists in DB, load_book navigates there."""
        book = make_test_book()
        # Pre-register book so we can save a position
        db.upsert_book(book.book_id, book.title, book.pdf_path,
                        book.total_pages, len(book.chapters))
        db.save_last_position(book.book_id, 2, 500)

        scroll_positions: list[int] = []
        controller.scroll_to_position.connect(scroll_positions.append)

        controller.load_book(book)

        assert controller.current_chapter_num == 2
        assert scroll_positions == [500]

    def test_load_book_builds_chapter_map(
        self, controller: BookController,
    ) -> None:
        book = make_test_book()
        controller.load_book(book)
        # Internal _chapter_map should have O(1) lookup for all chapters
        assert set(controller._chapter_map.keys()) == {1, 2, 3}

    def test_load_book_builds_chapter_order(
        self, controller: BookController,
    ) -> None:
        book = make_test_book()
        controller.load_book(book)
        assert controller._chapter_order == [1, 2, 3]


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------

class TestNavigation:
    """Tests for navigate_to_chapter, next_chapter, prev_chapter."""

    def test_navigate_to_valid_chapter(self, controller: BookController) -> None:
        book = make_test_book()
        controller.load_book(book)
        controller.navigate_to_chapter(2)
        assert controller.current_chapter_num == 2

    def test_navigate_emits_chapter_changed(self, controller: BookController) -> None:
        book = make_test_book()
        controller.load_book(book)

        received: list[tuple[int, list]] = []
        controller.chapter_changed.connect(lambda n, blocks: received.append((n, blocks)))
        controller.navigate_to_chapter(3)

        assert len(received) >= 1
        ch_num, blocks = received[-1]
        assert ch_num == 3
        assert len(blocks) == 3  # heading + body + code

    def test_navigate_emits_status_message(self, controller: BookController) -> None:
        book = make_test_book()
        controller.load_book(book)

        messages: list[str] = []
        controller.status_message.connect(messages.append)
        controller.navigate_to_chapter(2)

        assert any("Chapter 2 of 3" in m for m in messages)

    def test_navigate_marks_chapter_in_progress(
        self, controller: BookController, db: Database,
    ) -> None:
        book = make_test_book()
        controller.load_book(book)
        controller.navigate_to_chapter(2)

        progress = db.get_reading_progress("test_book", 2)
        assert progress is not None
        assert progress["status"] == STATUS_IN_PROGRESS

    def test_navigate_to_invalid_chapter(self, controller: BookController) -> None:
        book = make_test_book()
        controller.load_book(book)
        controller.navigate_to_chapter(1)
        # Navigate to non-existent chapter 99 -- should be a no-op
        controller.navigate_to_chapter(99)
        assert controller.current_chapter_num == 1

    def test_navigate_without_book_loaded(self, controller: BookController) -> None:
        # No book loaded — should silently return without crash
        controller.navigate_to_chapter(1)
        assert controller.current_chapter_num == 0

    def test_next_chapter(self, controller: BookController) -> None:
        book = make_test_book()
        controller.load_book(book)
        controller.navigate_to_chapter(1)
        controller.next_chapter()
        assert controller.current_chapter_num == 2

    def test_next_chapter_at_last(self, controller: BookController) -> None:
        book = make_test_book()
        controller.load_book(book)
        controller.navigate_to_chapter(3)
        controller.next_chapter()
        # Should stay at chapter 3
        assert controller.current_chapter_num == 3

    def test_prev_chapter(self, controller: BookController) -> None:
        book = make_test_book()
        controller.load_book(book)
        controller.navigate_to_chapter(3)
        controller.prev_chapter()
        assert controller.current_chapter_num == 2

    def test_prev_chapter_at_first(self, controller: BookController) -> None:
        book = make_test_book()
        controller.load_book(book)
        controller.navigate_to_chapter(1)
        controller.prev_chapter()
        # Should stay at chapter 1
        assert controller.current_chapter_num == 1

    def test_next_prev_without_book(self, controller: BookController) -> None:
        # Should not crash
        controller.next_chapter()
        controller.prev_chapter()
        assert controller.current_chapter_num == 0


# ---------------------------------------------------------------------------
# Section navigation
# ---------------------------------------------------------------------------

class TestSectionNavigation:
    """Tests for navigate_to_section."""

    def test_navigate_to_section_same_chapter(self, controller: BookController) -> None:
        book = make_test_book()
        controller.load_book(book)
        controller.navigate_to_chapter(1)
        block_id = controller.navigate_to_section(1, 0)
        assert block_id == "heading_1"

    def test_navigate_to_section_different_chapter(self, controller: BookController) -> None:
        book = make_test_book()
        controller.load_book(book)
        controller.navigate_to_chapter(1)
        block_id = controller.navigate_to_section(2, 1)
        # Should navigate to chapter 2 and return block_id for index 1
        assert controller.current_chapter_num == 2
        assert block_id == "body_2"

    def test_navigate_to_section_invalid_index(self, controller: BookController) -> None:
        book = make_test_book()
        controller.load_book(book)
        controller.navigate_to_chapter(1)
        block_id = controller.navigate_to_section(1, 999)
        assert block_id is None


# ---------------------------------------------------------------------------
# Progress tracking
# ---------------------------------------------------------------------------

class TestProgress:
    """Tests for mark_chapter_complete, save_position, get_progress_data."""

    def test_mark_chapter_complete(
        self, controller: BookController, db: Database,
    ) -> None:
        book = make_test_book()
        controller.load_book(book)
        controller.navigate_to_chapter(2)
        controller.mark_chapter_complete()

        progress = db.get_reading_progress("test_book", 2)
        assert progress is not None
        assert progress["status"] == STATUS_COMPLETED

    def test_mark_complete_emits_chapter_status_changed(
        self, controller: BookController,
    ) -> None:
        book = make_test_book()
        controller.load_book(book)
        controller.navigate_to_chapter(2)

        received: list[tuple[int, str]] = []
        controller.chapter_status_changed.connect(
            lambda num, status: received.append((num, status))
        )
        controller.mark_chapter_complete()

        assert (2, STATUS_COMPLETED) in received

    def test_mark_complete_emits_progress_updated(
        self, controller: BookController,
    ) -> None:
        book = make_test_book()
        controller.load_book(book)
        controller.navigate_to_chapter(1)

        messages: list[str] = []
        controller.progress_updated.connect(messages.append)
        controller.mark_chapter_complete()

        # 1 of 3 complete = 33%
        assert any("33% complete" in m for m in messages)

    def test_mark_complete_emits_status_message(
        self, controller: BookController,
    ) -> None:
        book = make_test_book()
        controller.load_book(book)
        controller.navigate_to_chapter(1)

        messages: list[str] = []
        controller.status_message.connect(messages.append)
        controller.mark_chapter_complete()

        assert any("marked complete" in m for m in messages)

    def test_mark_complete_without_book(self, controller: BookController) -> None:
        # No book loaded, chapter_num == 0 — should be no-op
        controller.mark_chapter_complete()  # should not raise

    def test_save_position(
        self, controller: BookController, db: Database,
    ) -> None:
        book = make_test_book()
        controller.load_book(book)
        controller.navigate_to_chapter(2)
        controller.save_position(750)

        pos = db.get_last_position("test_book")
        assert pos is not None
        assert pos["chapter_num"] == 2
        assert pos["scroll_position"] == 750

    def test_save_position_updates_reading_progress(
        self, controller: BookController, db: Database,
    ) -> None:
        book = make_test_book()
        controller.load_book(book)
        controller.navigate_to_chapter(1)
        controller.save_position(300)

        progress = db.get_reading_progress("test_book", 1)
        assert progress is not None
        assert progress["scroll_position"] == 300

    def test_save_position_without_book(
        self, controller: BookController, db: Database,
    ) -> None:
        # No book loaded — should be no-op, not crash
        controller.save_position(100)
        # DB should have no last_position entries
        assert db.get_last_position("test_book") is None

    def test_get_progress_data(
        self, controller: BookController, db: Database,
    ) -> None:
        book = make_test_book()
        controller.load_book(book)
        controller.navigate_to_chapter(1)
        controller.mark_chapter_complete()
        controller.navigate_to_chapter(2)

        data = controller.get_progress_data()
        assert data[1] == STATUS_COMPLETED
        assert data[2] == STATUS_IN_PROGRESS

    def test_get_progress_data_without_book(self, controller: BookController) -> None:
        assert controller.get_progress_data() == {}


# ---------------------------------------------------------------------------
# Properties and misc
# ---------------------------------------------------------------------------

class TestProperties:
    """Tests for properties and helper methods."""

    def test_current_chapter_title(self, controller: BookController) -> None:
        book = make_test_book()
        controller.load_book(book)
        controller.navigate_to_chapter(2)
        assert controller.current_chapter_title() == "Chapter 2"

    def test_current_chapter_title_no_chapter(self, controller: BookController) -> None:
        assert controller.current_chapter_title() == ""

    def test_current_language_default(self, controller: BookController) -> None:
        assert controller.current_language == "python"

    def test_image_dir_with_book(
        self, controller: BookController, cache: MagicMock,
    ) -> None:
        book = make_test_book()
        controller.load_book(book)
        result = controller.image_dir
        cache.image_dir.assert_called_with("test_book")
        assert result == str(Path("/tmp/images"))

    def test_image_dir_without_book(self, controller: BookController) -> None:
        assert controller.image_dir == ""

    def test_chapter_map_lookup(self, controller: BookController) -> None:
        """The dict-based chapter map provides O(1) access."""
        book = make_test_book()
        controller.load_book(book)
        ch = controller._chapter_map[2]
        assert ch.title == "Chapter 2"
        assert ch.chapter_num == 2
        assert len(ch.content_blocks) == 3


# ---------------------------------------------------------------------------
# on_book_selected (integration with cache/config mocks)
# ---------------------------------------------------------------------------

class TestOnBookSelected:
    """Tests for on_book_selected — the entry point from UI book picker."""

    def test_book_not_in_config(
        self, controller: BookController, books_config: MagicMock,
    ) -> None:
        books_config.get_book.return_value = None
        # Should not crash or emit anything
        controller.on_book_selected("nonexistent")
        assert controller.current_book is None

    def test_book_cached_loads_immediately(
        self, controller: BookController, books_config: MagicMock,
        cache: MagicMock,
    ) -> None:
        book_info = {
            "book_id": "cached_book",
            "title": "Cached Book",
            "pdf_path": "/tmp/cached.pdf",
            "language": "python",
            "profile_name": "test",
        }
        books_config.get_book.return_value = book_info

        book = make_test_book(book_id="cached_book", title="Cached Book")
        cache.load.return_value = book

        controller.on_book_selected("cached_book")
        assert controller.current_book is book

    def test_book_not_cached_pdf_missing_emits_error(
        self, controller: BookController, books_config: MagicMock,
        cache: MagicMock,
    ) -> None:
        book_info = {
            "book_id": "missing_pdf",
            "title": "Missing PDF Book",
            "pdf_path": "/nonexistent/path/book.pdf",
            "language": "python",
            "profile_name": "test",
        }
        books_config.get_book.return_value = book_info
        cache.load.return_value = None

        errors: list[tuple[str, str]] = []
        controller.error_message.connect(
            lambda title, msg: errors.append((title, msg))
        )

        controller.on_book_selected("missing_pdf")
        assert len(errors) == 1
        assert "PDF Not Found" in errors[0][0]

    def test_book_not_cached_pdf_exists_requests_parse(
        self, controller: BookController, books_config: MagicMock,
        cache: MagicMock, tmp_path: Path,
    ) -> None:
        pdf_path = tmp_path / "real.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 fake")

        book_info = {
            "book_id": "parse_me",
            "title": "Parse Me",
            "pdf_path": str(pdf_path),
            "language": "python",
            "profile_name": "test",
        }
        books_config.get_book.return_value = book_info
        cache.load.return_value = None

        parse_requests: list[dict] = []
        controller.parse_requested.connect(parse_requests.append)

        controller.on_book_selected("parse_me")
        assert len(parse_requests) == 1
        assert parse_requests[0]["book_id"] == "parse_me"
