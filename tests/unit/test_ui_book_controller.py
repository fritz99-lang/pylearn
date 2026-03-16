"""Tests for BookController — state management with signals.

BookController is a QObject with no direct UI references, making it
highly testable. We mock Database and CacheManager to verify signal
emission and state transitions.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from pylearn.core.constants import STATUS_COMPLETED, STATUS_IN_PROGRESS
from pylearn.core.models import BlockType, Book, Chapter, ContentBlock, Section


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.get_completion_stats.return_value = {"percent": 50}
    db.get_last_position.return_value = None
    db.get_reading_progress.return_value = None
    db.get_all_progress.return_value = []
    return db


@pytest.fixture
def mock_cache():
    return MagicMock()


@pytest.fixture
def mock_books_config():
    config = MagicMock()
    config.get_book.return_value = {
        "book_id": "test",
        "title": "Test",
        "pdf_path": "/tmp/test.pdf",
        "language": "python",
    }
    return config


@pytest.fixture
def controller(mock_db, mock_cache, mock_books_config):
    from pylearn.ui.book_controller import BookController

    return BookController(mock_db, mock_cache, mock_books_config)


@pytest.fixture
def sample_book():
    return Book(
        book_id="test",
        title="Test Book",
        pdf_path="/tmp/test.pdf",
        language="python",
        total_pages=100,
        chapters=[
            Chapter(
                chapter_num=1,
                title="Intro",
                start_page=1,
                end_page=50,
                content_blocks=[
                    ContentBlock(block_type=BlockType.HEADING1, text="Intro", page_num=1),
                    ContentBlock(block_type=BlockType.BODY, text="Body", page_num=1),
                ],
                sections=[Section(title="Intro", level=1, page_num=1, block_index=0)],
            ),
            Chapter(
                chapter_num=2,
                title="Basics",
                start_page=51,
                end_page=100,
                content_blocks=[
                    ContentBlock(block_type=BlockType.HEADING1, text="Basics", page_num=51),
                ],
            ),
        ],
    )


# ===========================================================================
# Properties
# ===========================================================================


class TestControllerProperties:
    def test_initial_state(self, controller):
        assert controller.current_book is None
        assert controller.current_chapter_num == 0
        assert controller.current_language == "python"
        assert controller.image_dir == ""

    def test_image_dir_with_book(self, controller, mock_cache, sample_book):
        mock_cache.image_dir.return_value = "/cache/test_images"
        controller.load_book(sample_book)
        assert "test_images" in controller.image_dir


# ===========================================================================
# load_book
# ===========================================================================


class TestLoadBook:
    def test_load_book_sets_state(self, controller, sample_book):
        controller.load_book(sample_book)
        assert controller.current_book is sample_book
        assert controller.current_language == "python"

    def test_load_book_emits_signals(self, controller, sample_book, mock_db):
        signals = {"book_loaded": [], "language": [], "progress": [], "chapter": []}
        controller.book_loaded.connect(lambda b: signals["book_loaded"].append(b))
        controller.language_changed.connect(signals["language"].append)
        controller.progress_updated.connect(signals["progress"].append)
        controller.chapter_changed.connect(lambda n, b: signals["chapter"].append(n))

        controller.load_book(sample_book)

        assert len(signals["book_loaded"]) == 1
        assert signals["language"] == ["python"]
        assert signals["progress"] == ["50% complete"]
        # Should navigate to first chapter
        assert 1 in signals["chapter"]

    def test_load_book_registers_in_db(self, controller, sample_book, mock_db):
        controller.load_book(sample_book)
        mock_db.upsert_book.assert_called_once_with("test", "Test Book", "/tmp/test.pdf", 100, 2)
        mock_db.upsert_chapters_batch.assert_called_once()

    def test_load_book_restores_last_position(self, controller, sample_book, mock_db):
        mock_db.get_last_position.return_value = {"chapter_num": 2, "scroll_position": 500}
        signals = {"scroll": [], "chapter": []}
        controller.scroll_to_position.connect(signals["scroll"].append)
        controller.chapter_changed.connect(lambda n, b: signals["chapter"].append(n))

        controller.load_book(sample_book)
        assert 2 in signals["chapter"]
        assert 500 in signals["scroll"]


# ===========================================================================
# on_book_selected
# ===========================================================================


class TestOnBookSelected:
    def test_loads_from_cache(self, controller, mock_cache, mock_books_config, sample_book):
        mock_cache.load.return_value = sample_book
        controller.on_book_selected("test")
        assert controller.current_book is sample_book

    def test_requests_parse_on_cache_miss(self, controller, mock_cache, mock_books_config, tmp_path):
        mock_cache.load.return_value = None
        # Make the PDF exist
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF")
        mock_books_config.get_book.return_value = {
            "book_id": "test",
            "title": "Test",
            "pdf_path": str(pdf),
            "language": "python",
        }

        signals = []
        controller.parse_requested.connect(signals.append)
        controller.on_book_selected("test")
        assert len(signals) == 1

    def test_unknown_book_id_ignored(self, controller, mock_books_config):
        mock_books_config.get_book.return_value = None
        controller.on_book_selected("unknown")
        assert controller.current_book is None

    def test_missing_pdf_shows_error(self, controller, mock_cache, mock_books_config):
        mock_cache.load.return_value = None
        mock_books_config.get_book.return_value = {
            "book_id": "test",
            "title": "Test",
            "pdf_path": "/nonexistent/test.pdf",
        }
        errors = []
        controller.error_message.connect(lambda t, m: errors.append(t))
        controller.on_book_selected("test")
        assert len(errors) == 1
        assert errors[0] == "PDF Not Found"


# ===========================================================================
# Navigation
# ===========================================================================


class TestNavigation:
    def test_navigate_to_chapter(self, controller, sample_book, mock_db):
        controller.load_book(sample_book)
        signals = []
        controller.chapter_changed.connect(lambda n, b: signals.append(n))

        controller.navigate_to_chapter(2)
        assert controller.current_chapter_num == 2
        assert 2 in signals

    def test_navigate_to_nonexistent_chapter(self, controller, sample_book):
        controller.load_book(sample_book)
        controller.navigate_to_chapter(999)
        # Should not change from current chapter
        assert controller.current_chapter_num != 999

    def test_navigate_without_book(self, controller):
        controller.navigate_to_chapter(1)  # should not raise

    def test_next_chapter(self, controller, sample_book):
        controller.load_book(sample_book)
        controller.navigate_to_chapter(1)
        controller.next_chapter()
        assert controller.current_chapter_num == 2

    def test_next_chapter_at_end(self, controller, sample_book):
        controller.load_book(sample_book)
        controller.navigate_to_chapter(2)
        controller.next_chapter()
        assert controller.current_chapter_num == 2  # stays at last

    def test_prev_chapter(self, controller, sample_book):
        controller.load_book(sample_book)
        controller.navigate_to_chapter(2)
        controller.prev_chapter()
        assert controller.current_chapter_num == 1

    def test_prev_chapter_at_start(self, controller, sample_book):
        controller.load_book(sample_book)
        controller.navigate_to_chapter(1)
        controller.prev_chapter()
        assert controller.current_chapter_num == 1  # stays at first

    def test_prev_next_without_book(self, controller):
        controller.prev_chapter()  # should not raise
        controller.next_chapter()

    def test_navigate_to_section(self, controller, sample_book):
        controller.load_book(sample_book)
        controller.navigate_to_section(1, 0)
        assert controller.current_chapter_num == 1

    def test_navigate_to_section_cross_chapter(self, controller, sample_book):
        controller.load_book(sample_book)
        controller.navigate_to_chapter(1)
        controller.navigate_to_section(2, 0)
        assert controller.current_chapter_num == 2

    def test_navigate_marks_in_progress(self, controller, sample_book, mock_db):
        mock_db.get_reading_progress.return_value = None
        controller.load_book(sample_book)
        controller.navigate_to_chapter(2)
        mock_db.update_reading_progress.assert_called_with("test", 2, STATUS_IN_PROGRESS)

    def test_navigate_does_not_downgrade_completed(self, controller, sample_book, mock_db):
        mock_db.get_reading_progress.return_value = {"status": STATUS_COMPLETED}
        controller.load_book(sample_book)
        # Reset mock to track only the navigate call
        mock_db.update_reading_progress.reset_mock()
        controller.navigate_to_chapter(1)
        # Should NOT call update_reading_progress since chapter is completed
        mock_db.update_reading_progress.assert_not_called()


# ===========================================================================
# mark_chapter_complete
# ===========================================================================


class TestMarkChapterComplete:
    def test_marks_complete(self, controller, sample_book, mock_db):
        controller.load_book(sample_book)
        controller.navigate_to_chapter(1)
        mock_db.update_reading_progress.reset_mock()

        signals = []
        controller.chapter_status_changed.connect(lambda n, s: signals.append((n, s)))
        controller.mark_chapter_complete()
        mock_db.update_reading_progress.assert_called_with("test", 1, STATUS_COMPLETED)
        assert (1, STATUS_COMPLETED) in signals

    def test_no_book_is_noop(self, controller, mock_db):
        mock_db.update_reading_progress.reset_mock()
        controller.mark_chapter_complete()
        mock_db.update_reading_progress.assert_not_called()


# ===========================================================================
# save_position / get_progress_data / current_chapter_title
# ===========================================================================


class TestHelpers:
    def test_save_position(self, controller, sample_book, mock_db):
        controller.load_book(sample_book)
        controller.navigate_to_chapter(1)
        mock_db.get_reading_progress.return_value = {"status": STATUS_IN_PROGRESS}
        controller.save_position(500)
        mock_db.save_last_position.assert_called_with("test", 1, 500)

    def test_save_position_without_book(self, controller, mock_db):
        controller.save_position(100)
        mock_db.save_last_position.assert_not_called()

    def test_save_position_does_not_downgrade_completed(self, controller, sample_book, mock_db):
        controller.load_book(sample_book)
        controller.navigate_to_chapter(1)
        mock_db.get_reading_progress.return_value = {"status": STATUS_COMPLETED}
        mock_db.update_reading_progress.reset_mock()
        controller.save_position(500)
        mock_db.update_reading_progress.assert_not_called()

    def test_get_progress_data(self, controller, sample_book, mock_db):
        mock_db.get_all_progress.return_value = [
            {"chapter_num": 1, "status": STATUS_COMPLETED},
            {"chapter_num": 2, "status": STATUS_IN_PROGRESS},
        ]
        controller.load_book(sample_book)
        data = controller.get_progress_data()
        assert data == {1: STATUS_COMPLETED, 2: STATUS_IN_PROGRESS}

    def test_get_progress_data_no_book(self, controller):
        assert controller.get_progress_data() == {}

    def test_current_chapter_title(self, controller, sample_book):
        controller.load_book(sample_book)
        controller.navigate_to_chapter(1)
        assert controller.current_chapter_title() == "Intro"

    def test_current_chapter_title_no_chapter(self, controller):
        assert controller.current_chapter_title() == ""
