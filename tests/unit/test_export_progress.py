# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Tests for learning progress export to Markdown."""

from __future__ import annotations

from pathlib import Path

import pytest

from pylearn.core.database import Database
from pylearn.utils.export import (
    _pct,
    _progress_bar,
    _score_emoji,
    export_progress_to_markdown,
)


class TestHelpers:
    def test_progress_bar_zero(self) -> None:
        assert _progress_bar(0) == "[" + "░" * 20 + "]"

    def test_progress_bar_100(self) -> None:
        assert _progress_bar(100) == "[" + "█" * 20 + "]"

    def test_progress_bar_50(self) -> None:
        bar = _progress_bar(50)
        assert "█" * 10 in bar
        assert "░" * 10 in bar

    def test_pct_normal(self) -> None:
        assert _pct(3, 10) == 30

    def test_pct_zero_denominator(self) -> None:
        assert _pct(5, 0) == 0

    def test_score_emoji_perfect(self) -> None:
        assert _score_emoji(100) == "Perfect"

    def test_score_emoji_great(self) -> None:
        assert _score_emoji(85) == "Great"

    def test_score_emoji_good(self) -> None:
        assert _score_emoji(65) == "Good"

    def test_score_emoji_needs_review(self) -> None:
        assert _score_emoji(40) == "Needs Review"


class TestExportProgress:
    @pytest.fixture()
    def db(self, tmp_path: Path) -> Database:
        database = Database(tmp_path / "test.db")
        database.upsert_book("b1", "Test Book", "/p", 100, 5)
        yield database
        database.close()

    def test_returns_none_when_no_books(self, tmp_path: Path) -> None:
        db = Database(tmp_path / "empty.db")
        try:
            assert export_progress_to_markdown(db) is None
        finally:
            db.close()

    def test_returns_none_for_nonexistent_book(self, db: Database) -> None:
        assert export_progress_to_markdown(db, "no_book") is None

    def test_basic_export_has_header(self, db: Database) -> None:
        result = export_progress_to_markdown(db, "b1")
        assert result is not None
        assert "Test Book" in result
        assert "Learning Progress" in result
        assert "Reading Progress" in result

    def test_export_includes_quiz_stats(self, db: Database) -> None:
        db.save_quiz_answer("q1", "b1", 1, True, "a")
        db.save_quiz_answer("q2", "b1", 1, False, "b")

        result = export_progress_to_markdown(db, "b1")
        assert result is not None
        assert "Quiz Scores" in result
        assert "1/2 correct" in result

    def test_export_includes_challenge_stats(self, db: Database) -> None:
        db.save_challenge_progress("c1", "b1", 1, True, "code")
        db.save_challenge_progress("c2", "b1", 1, False, "code")

        result = export_progress_to_markdown(db, "b1")
        assert result is not None
        assert "Code Challenges" in result
        assert "1/2" in result

    def test_export_includes_project_stats(self, db: Database) -> None:
        db.save_project_progress("s1", "b1", 1, True, "code")
        db.save_project_progress("s2", "b1", 2, False, "code")

        result = export_progress_to_markdown(db, "b1")
        assert result is not None
        assert "Book Project" in result
        assert "1/2" in result

    def test_export_includes_progress_bar(self, db: Database) -> None:
        result = export_progress_to_markdown(db, "b1")
        assert result is not None
        assert "█" in result or "░" in result

    def test_export_all_books(self, db: Database) -> None:
        db.upsert_book("b2", "Second Book", "/p2", 50, 3)
        result = export_progress_to_markdown(db)
        assert result is not None
        assert "Test Book" in result
        assert "Second Book" in result

    def test_per_chapter_quiz_table(self, db: Database) -> None:
        # Need chapters in DB for the table
        db.upsert_chapter("b1", 1, "Basics", 1, 10)
        db.upsert_chapter("b1", 2, "Advanced", 11, 20)
        db.save_quiz_answer("q1", "b1", 1, True, "a")
        db.save_quiz_answer("q2", "b1", 1, True, "b")
        db.save_quiz_answer("q3", "b1", 2, False, "c")

        result = export_progress_to_markdown(db, "b1")
        assert result is not None
        assert "| Chapter |" in result
        assert "Basics" in result
        assert "Perfect" in result

    def test_omits_sections_with_no_data(self, db: Database) -> None:
        result = export_progress_to_markdown(db, "b1")
        assert result is not None
        assert "Quiz Scores" not in result
        assert "Code Challenges" not in result
        assert "Book Project" not in result
