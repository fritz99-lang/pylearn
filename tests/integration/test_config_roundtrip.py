"""Integration tests: config, database, and cache round-trips."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pylearn.core.config import AppConfig, BooksConfig, EditorConfig, _load_json, _save_json
from pylearn.core.database import Database
from pylearn.core.models import Book, BlockType, Chapter, ContentBlock
from pylearn.parser.cache_manager import CacheManager


class TestAppConfigRoundTrip:
    """AppConfig save → load preserves values."""

    def test_save_load(self, tmp_path: Path) -> None:
        config_path = tmp_path / "app_config.json"

        # Write config data manually
        data = {
            "window_width": 1200,
            "window_height": 800,
            "theme": "dark",
            "reader_font_size": 14,
            "toc_visible": False,
        }
        _save_json(config_path, data)

        loaded = _load_json(config_path)
        assert loaded["window_width"] == 1200
        assert loaded["window_height"] == 800
        assert loaded["theme"] == "dark"
        assert loaded["reader_font_size"] == 14
        assert loaded["toc_visible"] is False

    def test_font_size_clamped_on_read(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        config_path = tmp_path / "app_config.json"
        _save_json(config_path, {"reader_font_size": 200})

        monkeypatch.setattr("pylearn.core.config.APP_CONFIG_PATH", config_path)
        config = AppConfig()
        assert config.reader_font_size == 72  # clamped to max

    def test_font_size_clamped_low(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        config_path = tmp_path / "app_config.json"
        _save_json(config_path, {"reader_font_size": 2})

        monkeypatch.setattr("pylearn.core.config.APP_CONFIG_PATH", config_path)
        config = AppConfig()
        assert config.reader_font_size == 6  # clamped to min


class TestEditorConfigRoundTrip:
    """EditorConfig save → load preserves values."""

    def test_save_load(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        config_path = tmp_path / "editor_config.json"
        monkeypatch.setattr("pylearn.core.config.EDITOR_CONFIG_PATH", config_path)

        config = EditorConfig()
        config.font_size = 16
        config.tab_width = 8
        config.word_wrap = True
        config.execution_timeout = 60
        config.save()

        config2 = EditorConfig()
        assert config2.font_size == 16
        assert config2.tab_width == 8
        assert config2.word_wrap is True
        assert config2.execution_timeout == 60

    def test_font_size_clamping(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        config_path = tmp_path / "editor_config.json"
        _save_json(config_path, {"font_size": 100})

        monkeypatch.setattr("pylearn.core.config.EDITOR_CONFIG_PATH", config_path)
        config = EditorConfig()
        assert config.font_size == 72

    def test_timeout_clamping(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        config_path = tmp_path / "editor_config.json"
        _save_json(config_path, {"execution_timeout": 1})

        monkeypatch.setattr("pylearn.core.config.EDITOR_CONFIG_PATH", config_path)
        config = EditorConfig()
        assert config.execution_timeout == 5  # clamped to min


class TestBooksConfigRoundTrip:
    """BooksConfig save → load preserves books list."""

    def test_add_and_retrieve(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        config_path = tmp_path / "books.json"
        monkeypatch.setattr("pylearn.core.config.BOOKS_CONFIG_PATH", config_path)

        config = BooksConfig()
        config.add_book("book1", "Test Book", "/tmp/test.pdf", "python", "learning_python")
        config.save()

        config2 = BooksConfig()
        assert len(config2.books) == 1
        assert config2.books[0]["book_id"] == "book1"
        assert config2.books[0]["language"] == "python"

    def test_remove_book(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        config_path = tmp_path / "books.json"
        monkeypatch.setattr("pylearn.core.config.BOOKS_CONFIG_PATH", config_path)

        config = BooksConfig()
        config.add_book("a", "A", "/a.pdf")
        config.add_book("b", "B", "/b.pdf")
        config.remove_book("a")
        config.save()

        config2 = BooksConfig()
        assert len(config2.books) == 1
        assert config2.books[0]["book_id"] == "b"


class TestDatabaseLifecycle:
    """Full database lifecycle: books → chapters → progress → bookmarks → notes → exercises."""

    def test_full_lifecycle(self, tmp_path: Path) -> None:
        db = Database(db_path=tmp_path / "test.db")

        # Books
        db.upsert_book("book1", "Test Book", "/test.pdf", 100, 5)
        books = db.get_books()
        assert len(books) == 1
        assert books[0]["title"] == "Test Book"

        # Chapters
        db.upsert_chapter("book1", 1, "Chapter 1", 1, 20)
        db.upsert_chapter("book1", 2, "Chapter 2", 21, 40)
        chapters = db.get_chapters("book1")
        assert len(chapters) == 2

        # Reading progress
        db.update_reading_progress("book1", 1, "in_progress", 150)
        progress = db.get_reading_progress("book1", 1)
        assert progress is not None
        assert progress["status"] == "in_progress"
        assert progress["scroll_position"] == 150

        db.update_reading_progress("book1", 1, "completed")
        stats = db.get_completion_stats("book1")
        assert stats["completed"] == 1

        # Bookmarks
        bm_id = db.add_bookmark("book1", 1, 200, "Important section")
        assert bm_id > 0
        bookmarks = db.get_bookmarks("book1")
        assert len(bookmarks) == 1
        assert bookmarks[0]["label"] == "Important section"

        db.delete_bookmark(bm_id)
        assert len(db.get_bookmarks("book1")) == 0

        # Notes
        note_id = db.add_note("book1", 1, "Section A", "My note content")
        assert note_id > 0
        notes = db.get_notes("book1", 1)
        assert len(notes) == 1
        assert notes[0]["content"] == "My note content"

        db.update_note(note_id, "Updated content")
        notes = db.get_notes("book1", 1)
        assert notes[0]["content"] == "Updated content"

        db.delete_note(note_id)
        assert len(db.get_notes("book1", 1)) == 0

        # Exercises
        db.upsert_exercise("ex1", "book1", 1, "Quiz 1", "What is 1+1?", "quiz", "2")
        exercises = db.get_exercises("book1", 1)
        assert len(exercises) == 1
        assert exercises[0]["title"] == "Quiz 1"

        db.update_exercise_progress("ex1", completed=True, user_code="print(2)")
        ep = db.get_exercise_progress("ex1")
        assert ep is not None
        assert ep["completed"]

    def test_persistence_across_instances(self, tmp_path: Path) -> None:
        db_path = tmp_path / "persist.db"

        # Instance 1: write
        db1 = Database(db_path=db_path)
        db1.upsert_book("book1", "Persistent Book", "/test.pdf", 50, 3)
        db1.add_bookmark("book1", 1, 100, "Bookmark from instance 1")

        # Instance 2: read
        db2 = Database(db_path=db_path)
        books = db2.get_books()
        assert len(books) == 1
        assert books[0]["title"] == "Persistent Book"

        bookmarks = db2.get_bookmarks("book1")
        assert len(bookmarks) == 1

    def test_last_position(self, tmp_path: Path) -> None:
        db = Database(db_path=tmp_path / "test.db")
        db.upsert_book("book1", "Test", "/t.pdf", 10, 1)

        db.save_last_position("book1", 3, 500)
        pos = db.get_last_position("book1")
        assert pos is not None
        assert pos["chapter_num"] == 3
        assert pos["scroll_position"] == 500

        # Overwrite
        db.save_last_position("book1", 5, 800)
        pos = db.get_last_position("book1")
        assert pos is not None
        assert pos["chapter_num"] == 5

    def test_saved_code(self, tmp_path: Path) -> None:
        db = Database(db_path=tmp_path / "test.db")
        db.upsert_book("book1", "Test", "/t.pdf", 10, 1)

        code_id = db.save_code("book1", 1, "print('hello')", "My snippet")
        assert code_id > 0

        saved = db.get_saved_code("book1", 1)
        assert len(saved) == 1
        assert saved[0]["code"] == "print('hello')"

        db.delete_saved_code(code_id)
        assert len(db.get_saved_code("book1", 1)) == 0


class TestCacheManagerRoundTrip:
    """CacheManager save → load → invalidate."""

    def test_save_and_load(self, tmp_path: Path, sample_book: Book) -> None:
        cache = CacheManager(cache_dir=tmp_path)
        cache.save(sample_book)

        assert cache.has_cache("test_book")

        loaded = cache.load("test_book")
        assert loaded is not None
        assert loaded.book_id == "test_book"
        assert loaded.title == "Test Book"
        assert len(loaded.chapters) == 1
        assert len(loaded.chapters[0].content_blocks) == 3

    def test_invalidate(self, tmp_path: Path, sample_book: Book) -> None:
        cache = CacheManager(cache_dir=tmp_path)
        cache.save(sample_book)
        assert cache.has_cache("test_book")

        cache.invalidate("test_book")
        assert not cache.has_cache("test_book")
        assert cache.load("test_book") is None

    def test_invalidate_all(self, tmp_path: Path, sample_book: Book) -> None:
        cache = CacheManager(cache_dir=tmp_path)
        cache.save(sample_book)

        # Save a second book
        book2 = Book(book_id="book2", title="Book 2", pdf_path="/tmp/b2.pdf")
        cache.save(book2)

        assert cache.has_cache("test_book")
        assert cache.has_cache("book2")

        cache.invalidate_all()
        assert not cache.has_cache("test_book")
        assert not cache.has_cache("book2")

    def test_load_nonexistent(self, tmp_path: Path) -> None:
        cache = CacheManager(cache_dir=tmp_path)
        assert cache.load("nonexistent") is None

    def test_cache_info(self, tmp_path: Path, sample_book: Book) -> None:
        cache = CacheManager(cache_dir=tmp_path)
        cache.save(sample_book)

        info = cache.get_cache_info()
        assert len(info) == 1
        assert info[0]["book_id"] == "test_book"
        assert info[0]["size_kb"] > 0

    def test_image_dir_created(self, tmp_path: Path) -> None:
        cache = CacheManager(cache_dir=tmp_path)
        img_dir = cache.image_dir("test_book")
        assert img_dir.exists()
        assert img_dir.is_dir()
