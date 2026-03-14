# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Tests for ContentLoader and quiz data models."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pylearn.core.content_loader import ContentLoader
from pylearn.core.models import QuizQuestion, QuizSet


@pytest.fixture
def content_dir(tmp_path: Path) -> Path:
    """Create a temporary content directory with sample quiz data."""
    quiz_dir = tmp_path / "test_book" / "quizzes"
    quiz_dir.mkdir(parents=True)

    quiz_data = {
        "book_id": "test_book",
        "chapter_num": 1,
        "questions": [
            {
                "id": "tb_ch01_q01",
                "type": "multiple_choice",
                "question": "What is 2 + 2?",
                "choices": ["3", "4", "5", "6"],
                "correct": 1,
                "explanation": "Basic arithmetic.",
                "concepts": ["math"],
            },
            {
                "id": "tb_ch01_q02",
                "type": "fill_in_blank",
                "question": "Python is a ___ language.",
                "correct": "programming",
                "explanation": "Python is a programming language.",
                "concepts": ["basics"],
            },
        ],
    }
    (quiz_dir / "ch01.json").write_text(json.dumps(quiz_data), encoding="utf-8")

    # Also create a chapter 3 quiz
    quiz_data_ch3 = {
        "book_id": "test_book",
        "chapter_num": 3,
        "questions": [
            {
                "id": "tb_ch03_q01",
                "type": "multiple_choice",
                "question": "Which is a list?",
                "choices": ["(1,2)", "[1,2]", "{1,2}", "1,2"],
                "correct": 1,
                "explanation": "Square brackets create lists.",
            }
        ],
    }
    (quiz_dir / "ch03.json").write_text(json.dumps(quiz_data_ch3), encoding="utf-8")

    return tmp_path


@pytest.fixture
def loader(content_dir: Path) -> ContentLoader:
    return ContentLoader(content_dir)


class TestQuizQuestion:
    def test_from_dict_mc(self) -> None:
        data = {
            "id": "q1",
            "type": "multiple_choice",
            "question": "Test?",
            "choices": ["a", "b"],
            "correct": 0,
        }
        q = QuizQuestion.from_dict(data)
        assert q.question_id == "q1"
        assert q.question_type == "multiple_choice"
        assert q.choices == ["a", "b"]
        assert q.correct == 0

    def test_from_dict_fill_in(self) -> None:
        data = {
            "id": "q2",
            "type": "fill_in_blank",
            "question": "Answer is ___",
            "correct": "hello",
            "explanation": "Because hello.",
        }
        q = QuizQuestion.from_dict(data)
        assert q.question_id == "q2"
        assert q.question_type == "fill_in_blank"
        assert q.correct == "hello"
        assert q.explanation == "Because hello."

    def test_from_dict_missing_key(self) -> None:
        with pytest.raises(ValueError, match="missing required key"):
            QuizQuestion.from_dict({"id": "q1"})


class TestQuizSet:
    def test_from_dict(self) -> None:
        data = {
            "book_id": "book1",
            "chapter_num": 5,
            "questions": [{"id": "q1", "type": "multiple_choice", "question": "?", "choices": ["a"], "correct": 0}],
        }
        qs = QuizSet.from_dict(data)
        assert qs.book_id == "book1"
        assert qs.chapter_num == 5
        assert len(qs.questions) == 1

    def test_from_dict_missing_key(self) -> None:
        with pytest.raises(ValueError, match="missing required key"):
            QuizSet.from_dict({"book_id": "b"})


class TestContentLoader:
    def test_load_quiz(self, loader: ContentLoader) -> None:
        quiz = loader.load_quiz("test_book", 1)
        assert quiz is not None
        assert quiz.book_id == "test_book"
        assert quiz.chapter_num == 1
        assert len(quiz.questions) == 2
        assert quiz.questions[0].question_id == "tb_ch01_q01"
        assert quiz.questions[1].question_type == "fill_in_blank"

    def test_load_quiz_nonexistent(self, loader: ContentLoader) -> None:
        assert loader.load_quiz("test_book", 99) is None

    def test_load_quiz_nonexistent_book(self, loader: ContentLoader) -> None:
        assert loader.load_quiz("no_such_book", 1) is None

    def test_has_quiz(self, loader: ContentLoader) -> None:
        assert loader.has_quiz("test_book", 1) is True
        assert loader.has_quiz("test_book", 2) is False
        assert loader.has_quiz("test_book", 3) is True

    def test_list_quiz_chapters(self, loader: ContentLoader) -> None:
        chapters = loader.list_quiz_chapters("test_book")
        assert chapters == [1, 3]

    def test_list_quiz_chapters_no_book(self, loader: ContentLoader) -> None:
        assert loader.list_quiz_chapters("nonexistent") == []

    def test_load_quiz_invalid_json(self, content_dir: Path) -> None:
        # Write invalid JSON
        bad_path = content_dir / "test_book" / "quizzes" / "ch99.json"
        bad_path.write_text("not valid json", encoding="utf-8")
        loader = ContentLoader(content_dir)
        assert loader.load_quiz("test_book", 99) is None


class TestQuizDatabaseMethods:
    """Test quiz_progress database methods."""

    def test_save_and_get_quiz_answer(self, tmp_path: Path) -> None:
        from pylearn.core.database import Database

        db = Database(tmp_path / "test.db")
        try:
            # Need a book first for FK
            db.upsert_book("book1", "Test Book", "/path", 100, 5)

            db.save_quiz_answer("q1", "book1", 1, True, "answer_a")
            result = db.get_quiz_answer("q1")
            assert result is not None
            assert result["correct"] == 1
            assert result["user_answer"] == "answer_a"
            assert result["attempts"] == 1

            # Update with second attempt
            db.save_quiz_answer("q1", "book1", 1, False, "answer_b")
            result = db.get_quiz_answer("q1")
            assert result is not None
            assert result["correct"] == 0
            assert result["user_answer"] == "answer_b"
            assert result["attempts"] == 2
        finally:
            db.close()

    def test_get_quiz_progress(self, tmp_path: Path) -> None:
        from pylearn.core.database import Database

        db = Database(tmp_path / "test.db")
        try:
            db.upsert_book("book1", "Test Book", "/path", 100, 5)
            db.save_quiz_answer("q1", "book1", 1, True, "a")
            db.save_quiz_answer("q2", "book1", 1, False, "b")
            db.save_quiz_answer("q3", "book1", 2, True, "c")

            progress = db.get_quiz_progress("book1", 1)
            assert len(progress) == 2

            progress_ch2 = db.get_quiz_progress("book1", 2)
            assert len(progress_ch2) == 1
        finally:
            db.close()

    def test_get_quiz_stats(self, tmp_path: Path) -> None:
        from pylearn.core.database import Database

        db = Database(tmp_path / "test.db")
        try:
            db.upsert_book("book1", "Test Book", "/path", 100, 5)
            db.save_quiz_answer("q1", "book1", 1, True, "a")
            db.save_quiz_answer("q2", "book1", 1, False, "b")
            db.save_quiz_answer("q3", "book1", 1, True, "c")

            stats = db.get_quiz_stats("book1", 1)
            assert stats["total"] == 3
            assert stats["correct"] == 2

            # Book-wide stats
            db.save_quiz_answer("q4", "book1", 2, True, "d")
            stats_all = db.get_quiz_stats("book1")
            assert stats_all["total"] == 4
            assert stats_all["correct"] == 3
        finally:
            db.close()

    def test_get_quiz_answer_nonexistent(self, tmp_path: Path) -> None:
        from pylearn.core.database import Database

        db = Database(tmp_path / "test.db")
        try:
            assert db.get_quiz_answer("nonexistent") is None
        finally:
            db.close()
