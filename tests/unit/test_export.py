# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Unit tests for notes/bookmarks Markdown export.

Pure-Python tests — no Qt required. Each test seeds a temporary SQLite
database and verifies the exported Markdown content.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pylearn.core.database import Database
from pylearn.utils.export import _fmt_timestamp, export_to_markdown


@pytest.fixture()
def db(tmp_path: Path) -> Database:
    """Create a fresh Database in a temp directory."""
    return Database(db_path=tmp_path / "test.db")


def _seed_book(db: Database, book_id: str = "book1", title: str = "Learning Python") -> None:
    """Insert a book with two chapters."""
    db.upsert_book(book_id, title, "/fake/path.pdf", 500, 2)
    db.upsert_chapter(book_id, 1, "Getting Started", 1, 50)
    db.upsert_chapter(book_id, 2, "Variables", 51, 100)


class TestFmtTimestamp:
    def test_valid_iso(self) -> None:
        assert _fmt_timestamp("2026-02-23T14:32:00") == "2026-02-23 at 14:32"

    def test_none(self) -> None:
        assert _fmt_timestamp(None) == ""

    def test_invalid(self) -> None:
        assert _fmt_timestamp("not-a-date") == "not-a-date"


class TestExportToMarkdown:
    def test_notes_and_bookmarks(self, db: Database) -> None:
        """Both notes and bookmarks present — verify both sections appear."""
        _seed_book(db)
        db.add_note("book1", 1, "Installation", "Install Python 3.12")
        db.add_bookmark("book1", 1, 0, "Start of chapter 1")

        result = export_to_markdown(db, "book1")
        assert result is not None
        assert "## Notes" in result
        assert "## Bookmarks" in result
        assert "Learning Python" in result
        assert "Install Python 3.12" in result
        assert "Start of chapter 1" in result

    def test_notes_only(self, db: Database) -> None:
        """Only notes, no bookmarks — Bookmarks section absent."""
        _seed_book(db)
        db.add_note("book1", 1, "Intro", "Some note content")

        result = export_to_markdown(db, "book1")
        assert result is not None
        assert "## Notes" in result
        assert "## Bookmarks" not in result

    def test_bookmarks_only(self, db: Database) -> None:
        """Only bookmarks, no notes — Notes section absent."""
        _seed_book(db)
        db.add_bookmark("book1", 2, 100, "Variable assignment section")

        result = export_to_markdown(db, "book1")
        assert result is not None
        assert "## Bookmarks" in result
        assert "## Notes" not in result
        assert "Chapter 2: Variables" in result

    def test_nothing_to_export(self, db: Database) -> None:
        """No notes or bookmarks — returns None."""
        _seed_book(db)

        result = export_to_markdown(db, "book1")
        assert result is None

    def test_multi_book_export(self, db: Database) -> None:
        """Export all books — both book titles appear."""
        _seed_book(db, "book1", "Learning Python")
        _seed_book(db, "book2", "C++ Primer")
        db.add_note("book1", 1, "Intro", "Python note")
        db.add_note("book2", 1, "Intro", "C++ note")

        result = export_to_markdown(db)
        assert result is not None
        assert "Learning Python" in result
        assert "C++ Primer" in result
        assert "Python note" in result
        assert "C++ note" in result

    def test_missing_chapter_title(self, db: Database) -> None:
        """Note in a chapter not registered in DB — falls back to 'Chapter {N}'."""
        db.upsert_book("book1", "Learning Python", "/fake.pdf", 100, 1)
        # Don't insert chapter metadata — chapter 99 has no title
        db.add_note("book1", 99, "Some section", "Orphan note")

        result = export_to_markdown(db, "book1")
        assert result is not None
        assert "Chapter 99: Chapter 99" in result

    def test_empty_section_title(self, db: Database) -> None:
        """Note with empty section_title — falls back to 'Note {id}'."""
        _seed_book(db)
        note_id = db.add_note("book1", 1, "", "A note with no section")

        result = export_to_markdown(db, "book1")
        assert result is not None
        assert f"Note {note_id}" in result
        assert "A note with no section" in result

    def test_no_books_returns_none(self, db: Database) -> None:
        """Requesting export for a non-existent book returns None."""
        result = export_to_markdown(db, "nonexistent")
        assert result is None
