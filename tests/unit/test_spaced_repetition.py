# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Tests for spaced repetition (review missed quiz questions)."""

from __future__ import annotations

from pathlib import Path

import pytest

from pylearn.core.database import Database


class TestGetWrongQuizAnswers:
    """Test the get_wrong_quiz_answers database method."""

    @pytest.fixture()
    def db(self, tmp_path: Path) -> Database:
        database = Database(tmp_path / "test.db")
        database.upsert_book("b1", "Test Book", "/p", 100, 5)
        yield database
        database.close()

    def test_returns_empty_when_no_wrong_answers(self, db: Database) -> None:
        assert db.get_wrong_quiz_answers("b1") == []

    def test_returns_empty_when_all_correct(self, db: Database) -> None:
        db.save_quiz_answer("q1", "b1", 1, True, "a")
        db.save_quiz_answer("q2", "b1", 1, True, "b")
        assert db.get_wrong_quiz_answers("b1") == []

    def test_returns_wrong_answers_only(self, db: Database) -> None:
        db.save_quiz_answer("q1", "b1", 1, True, "a")
        db.save_quiz_answer("q2", "b1", 1, False, "wrong")
        db.save_quiz_answer("q3", "b1", 2, False, "bad")

        wrong = db.get_wrong_quiz_answers("b1")
        assert len(wrong) == 2
        assert wrong[0]["question_id"] == "q2"
        assert wrong[1]["question_id"] == "q3"

    def test_ordered_by_chapter_then_question(self, db: Database) -> None:
        db.save_quiz_answer("q3_ch2", "b1", 2, False, "x")
        db.save_quiz_answer("q1_ch1", "b1", 1, False, "y")
        db.save_quiz_answer("q2_ch1", "b1", 1, False, "z")

        wrong = db.get_wrong_quiz_answers("b1")
        assert [w["question_id"] for w in wrong] == ["q1_ch1", "q2_ch1", "q3_ch2"]

    def test_scoped_to_book(self, db: Database) -> None:
        db.upsert_book("b2", "Other Book", "/p2", 50, 3)
        db.save_quiz_answer("q1", "b1", 1, False, "x")
        db.save_quiz_answer("q2", "b2", 1, False, "y")

        assert len(db.get_wrong_quiz_answers("b1")) == 1
        assert len(db.get_wrong_quiz_answers("b2")) == 1

    def test_corrected_answers_not_returned(self, db: Database) -> None:
        """If user retries and gets it right, it shouldn't appear."""
        db.save_quiz_answer("q1", "b1", 1, False, "wrong")
        assert len(db.get_wrong_quiz_answers("b1")) == 1

        # User retries and gets it right
        db.save_quiz_answer("q1", "b1", 1, True, "right")
        assert len(db.get_wrong_quiz_answers("b1")) == 0
