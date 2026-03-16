"""Tests for CacheManager — JSON cache for parsed books.

Uses tmp_path for file I/O, minimal mocking.
"""

from __future__ import annotations

import json
import os
import time

import pytest

from pylearn.core.models import BlockType, Book, Chapter, ContentBlock, Section
from pylearn.parser.cache_manager import CacheManager, sanitize_book_id

# ---------------------------------------------------------------------------
# sanitize_book_id
# ---------------------------------------------------------------------------


class TestSanitizeBookId:
    def test_basic(self):
        assert sanitize_book_id("learning_python") == "learning_python"

    def test_uppercase_lowered(self):
        assert sanitize_book_id("Learning_Python") == "learning_python"

    def test_special_chars_stripped(self):
        assert sanitize_book_id("my-book!@#$%") == "mybook"

    def test_path_traversal_stripped(self):
        assert sanitize_book_id("../../etc/passwd") == "etcpasswd"

    def test_spaces_stripped(self):
        assert sanitize_book_id("my book title") == "mybooktitle"

    def test_truncated_at_60(self):
        long_id = "a" * 100
        assert len(sanitize_book_id(long_id)) == 60

    def test_empty_string(self):
        assert sanitize_book_id("") == ""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def cache(tmp_path):
    return CacheManager(cache_dir=tmp_path)


@pytest.fixture
def sample_book(tmp_path):
    """A minimal Book with a real PDF path for mtime testing."""
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    return Book(
        book_id="test_book",
        title="Test Book",
        pdf_path=str(pdf),
        profile_name="test",
        language="python",
        total_pages=50,
        chapters=[
            Chapter(
                chapter_num=1,
                title="Intro",
                start_page=1,
                end_page=25,
                content_blocks=[
                    ContentBlock(block_type=BlockType.HEADING1, text="Intro", page_num=1, font_size=22.0),
                    ContentBlock(block_type=BlockType.BODY, text="Welcome.", page_num=1, font_size=10.0),
                ],
                sections=[Section(title="Intro", level=1, page_num=1, block_index=0)],
            ),
        ],
    )


# ---------------------------------------------------------------------------
# CacheManager construction
# ---------------------------------------------------------------------------


class TestCacheManagerInit:
    def test_creates_directory(self, tmp_path):
        cache_dir = tmp_path / "new_cache"
        assert not cache_dir.exists()
        CacheManager(cache_dir=cache_dir)
        assert cache_dir.exists()


# ---------------------------------------------------------------------------
# has_cache
# ---------------------------------------------------------------------------


class TestHasCache:
    def test_no_cache_initially(self, cache):
        assert cache.has_cache("test_book") is False

    def test_has_cache_after_save(self, cache, sample_book):
        cache.save(sample_book)
        assert cache.has_cache("test_book") is True


# ---------------------------------------------------------------------------
# save / load round-trip
# ---------------------------------------------------------------------------


class TestSaveLoad:
    def test_round_trip(self, cache, sample_book):
        cache.save(sample_book)
        loaded = cache.load("test_book")

        assert loaded is not None
        assert loaded.book_id == "test_book"
        assert loaded.title == "Test Book"
        assert loaded.language == "python"
        assert len(loaded.chapters) == 1
        assert loaded.chapters[0].title == "Intro"
        assert len(loaded.chapters[0].content_blocks) == 2

    def test_cache_miss_returns_none(self, cache):
        assert cache.load("nonexistent") is None

    def test_save_overwrites_existing(self, cache, sample_book):
        cache.save(sample_book)
        sample_book.title = "Updated Title"
        cache.save(sample_book)

        loaded = cache.load("test_book")
        assert loaded is not None
        assert loaded.title == "Updated Title"

    def test_save_stores_pdf_mtime(self, cache, sample_book, tmp_path):
        cache.save(sample_book)
        path = cache._cache_path("test_book")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert "_pdf_mtime" in data
        assert data["_pdf_mtime"] > 0

    def test_save_handles_missing_pdf_mtime(self, cache, tmp_path):
        """If PDF is deleted before save, mtime should be 0."""
        book = Book(
            book_id="gone",
            title="Gone",
            pdf_path=str(tmp_path / "nonexistent.pdf"),
            total_pages=0,
        )
        cache.save(book)
        path = cache._cache_path("gone")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert data["_pdf_mtime"] == 0.0


# ---------------------------------------------------------------------------
# Staleness detection
# ---------------------------------------------------------------------------


class TestStalenessDetection:
    def test_stale_cache_returns_none(self, cache, sample_book, tmp_path):
        """If the PDF is modified after caching, load should return None."""
        cache.save(sample_book)

        # Modify the PDF to change its mtime
        pdf_path = sample_book.pdf_path
        time.sleep(0.1)  # ensure mtime changes
        with open(pdf_path, "ab") as f:
            f.write(b"modified content")
        # Force a 2-second mtime difference
        new_mtime = os.path.getmtime(pdf_path) + 5
        os.utime(pdf_path, (new_mtime, new_mtime))

        result = cache.load("test_book")
        assert result is None

    def test_fresh_cache_loads_ok(self, cache, sample_book):
        cache.save(sample_book)
        result = cache.load("test_book")
        assert result is not None


# ---------------------------------------------------------------------------
# File size guard
# ---------------------------------------------------------------------------


class TestFileSizeGuard:
    def test_oversized_cache_returns_none(self, cache, tmp_path):
        """Cache files > 200MB should be skipped."""
        path = cache._cache_path("huge")
        # Write a minimal JSON that we'll pretend is huge
        path.write_text('{"book_id":"huge","title":"Big","pdf_path":"/x"}', encoding="utf-8")

        # Monkey-patch stat to report 201MB
        original_stat = path.stat

        class FakeStat:
            def __init__(self, real_stat):
                self._real = real_stat

            def __getattr__(self, name):
                return getattr(self._real, name)

            @property
            def st_size(self):
                return 201 * 1024 * 1024

        from unittest.mock import patch

        with patch.object(type(path), "stat", return_value=FakeStat(original_stat())):
            result = cache.load("huge")
        assert result is None


# ---------------------------------------------------------------------------
# invalidate
# ---------------------------------------------------------------------------


class TestInvalidate:
    def test_invalidate_single(self, cache, sample_book):
        cache.save(sample_book)
        assert cache.has_cache("test_book")
        cache.invalidate("test_book")
        assert not cache.has_cache("test_book")

    def test_invalidate_nonexistent_is_noop(self, cache):
        cache.invalidate("nonexistent")  # should not raise

    def test_invalidate_all(self, cache, sample_book, tmp_path):
        cache.save(sample_book)
        book2 = Book(
            book_id="other",
            title="Other",
            pdf_path=str(tmp_path / "other.pdf"),
            total_pages=0,
        )
        # Create a dummy PDF for book2 so save doesn't fail mtime
        (tmp_path / "other.pdf").write_bytes(b"pdf")
        cache.save(book2)

        assert cache.has_cache("test_book")
        assert cache.has_cache("other")
        cache.invalidate_all()
        assert not cache.has_cache("test_book")
        assert not cache.has_cache("other")


# ---------------------------------------------------------------------------
# image_dir
# ---------------------------------------------------------------------------


class TestImageDir:
    def test_creates_directory(self, cache):
        d = cache.image_dir("test_book")
        assert d.exists()
        assert d.is_dir()
        assert "test_book_images" in d.name

    def test_sanitized_name(self, cache):
        d = cache.image_dir("../../evil")
        assert ".." not in str(d.name)


# ---------------------------------------------------------------------------
# get_cache_info
# ---------------------------------------------------------------------------


class TestGetCacheInfo:
    def test_empty_cache(self, cache):
        assert cache.get_cache_info() == []

    def test_with_cached_books(self, cache, sample_book, tmp_path):
        cache.save(sample_book)
        info = cache.get_cache_info()
        assert len(info) == 1
        assert info[0]["book_id"] == "test_book"
        assert info[0]["size_kb"] >= 0
        assert info[0]["modified"] > 0


# ---------------------------------------------------------------------------
# _cache_path
# ---------------------------------------------------------------------------


class TestCachePath:
    def test_sanitizes_book_id(self, cache):
        path = cache._cache_path("My Book!!")
        assert path.name == "mybook.json"

    def test_json_extension(self, cache):
        path = cache._cache_path("test")
        assert path.suffix == ".json"


# ---------------------------------------------------------------------------
# Corrupt cache recovery
# ---------------------------------------------------------------------------


class TestCorruptCache:
    def test_corrupt_json_returns_none(self, cache, tmp_path):
        path = cache._cache_path("corrupt")
        path.write_text("not valid json {{{", encoding="utf-8")
        assert cache.load("corrupt") is None

    def test_missing_required_fields_returns_none(self, cache, tmp_path):
        path = cache._cache_path("incomplete")
        path.write_text('{"foo": "bar"}', encoding="utf-8")
        assert cache.load("incomplete") is None
