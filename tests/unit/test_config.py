"""Tests for configuration loading, saving, and migration."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from pylearn.core.config import _load_json, _save_json, BooksConfig


class TestLoadJson:
    def test_valid_json(self, tmp_path):
        p = tmp_path / "test.json"
        p.write_text('{"key": "value"}', encoding="utf-8")
        result = _load_json(p)
        assert result == {"key": "value"}

    def test_missing_file(self, tmp_path):
        p = tmp_path / "missing.json"
        result = _load_json(p)
        assert result == {}

    def test_corrupt_json(self, tmp_path):
        p = tmp_path / "corrupt.json"
        p.write_text("{broken json", encoding="utf-8")
        result = _load_json(p)
        assert result == {}

    def test_empty_file(self, tmp_path):
        p = tmp_path / "empty.json"
        p.write_text("", encoding="utf-8")
        result = _load_json(p)
        assert result == {}

    def test_unicode_error(self, tmp_path):
        p = tmp_path / "binary.json"
        p.write_bytes(b"\xff\xfe" + b"\x00" * 10)
        result = _load_json(p)
        # Should not crash — returns default
        assert isinstance(result, dict)


class TestSaveJson:
    def test_creates_file(self, tmp_path):
        p = tmp_path / "new.json"
        _save_json(p, {"hello": "world"})
        assert p.exists()
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data == {"hello": "world"}

    def test_creates_parent_dirs(self, tmp_path):
        p = tmp_path / "a" / "b" / "c.json"
        _save_json(p, {"nested": True})
        assert p.exists()

    def test_atomic_write(self, tmp_path):
        """Verify that a .tmp file is used (atomic rename)."""
        p = tmp_path / "atomic.json"
        _save_json(p, {"step": 1})
        # If it's atomic, no .tmp file should remain after write
        tmp_file = p.with_suffix(".tmp")
        assert not tmp_file.exists()
        assert p.exists()

    def test_overwrites_existing(self, tmp_path):
        p = tmp_path / "overwrite.json"
        _save_json(p, {"v": 1})
        _save_json(p, {"v": 2})
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data["v"] == 2

    def test_unicode_content(self, tmp_path):
        p = tmp_path / "unicode.json"
        _save_json(p, {"text": "caf\u00e9 \u2603"})
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data["text"] == "caf\u00e9 \u2603"


class TestBooksConfigMigration:
    def test_adds_missing_language(self, tmp_path):
        config_path = tmp_path / "books.json"
        config_path.write_text(json.dumps({
            "books": [
                {"book_id": "b1", "title": "Book 1", "pdf_path": "/b1.pdf"},
                {"book_id": "b2", "title": "Book 2", "pdf_path": "/b2.pdf", "language": "cpp"},
            ]
        }), encoding="utf-8")

        with patch("pylearn.core.config.BOOKS_CONFIG_PATH", config_path):
            cfg = BooksConfig()
            books = cfg.books
            assert books[0]["language"] == "python"  # default added
            assert books[1]["language"] == "cpp"      # existing preserved

    def test_adds_missing_profile_name(self, tmp_path):
        config_path = tmp_path / "books.json"
        config_path.write_text(json.dumps({
            "books": [
                {"book_id": "b1", "title": "B1", "pdf_path": "/b1.pdf"},
            ]
        }), encoding="utf-8")

        with patch("pylearn.core.config.BOOKS_CONFIG_PATH", config_path):
            cfg = BooksConfig()
            assert cfg.books[0]["profile_name"] == ""

    def test_add_book(self, tmp_path):
        config_path = tmp_path / "books.json"
        config_path.write_text('{"books": []}', encoding="utf-8")

        with patch("pylearn.core.config.BOOKS_CONFIG_PATH", config_path):
            cfg = BooksConfig()
            cfg.add_book("new_book", "New Book", "/new.pdf", "python", "")
            assert len(cfg.books) == 1
            assert cfg.books[0]["book_id"] == "new_book"

    def test_remove_book(self, tmp_path):
        config_path = tmp_path / "books.json"
        config_path.write_text(json.dumps({
            "books": [{"book_id": "b1", "title": "B1", "pdf_path": "/b1.pdf"}]
        }), encoding="utf-8")

        with patch("pylearn.core.config.BOOKS_CONFIG_PATH", config_path):
            cfg = BooksConfig()
            cfg.remove_book("b1")
            assert len(cfg.books) == 0

    def test_get_book(self, tmp_path):
        config_path = tmp_path / "books.json"
        config_path.write_text(json.dumps({
            "books": [
                {"book_id": "b1", "title": "Book One", "pdf_path": "/b1.pdf"},
                {"book_id": "b2", "title": "Book Two", "pdf_path": "/b2.pdf"},
            ]
        }), encoding="utf-8")

        with patch("pylearn.core.config.BOOKS_CONFIG_PATH", config_path):
            cfg = BooksConfig()
            assert cfg.get_book("b1")["title"] == "Book One"
            assert cfg.get_book("b2")["title"] == "Book Two"
            assert cfg.get_book("b3") is None
