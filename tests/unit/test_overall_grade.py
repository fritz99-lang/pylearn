"""Tests for compute_overall_grade — overall 1-100% scoring."""

from __future__ import annotations

import pytest

from pylearn.core.database import Database
from pylearn.utils.export import _grade_label, compute_overall_grade


@pytest.fixture
def db(tmp_path):
    return Database(db_path=tmp_path / "test.db")


@pytest.fixture
def seeded_db(db):
    """DB with one book, 10 chapters, some quiz/challenge/project data."""
    db.upsert_book("b1", "Test Book", "/test.pdf", 500, 10)
    for i in range(1, 11):
        db.upsert_chapter("b1", i, f"Chapter {i}", i * 50, (i + 1) * 50)
    return db


# ===========================================================================
# No data
# ===========================================================================


class TestNoData:
    def test_empty_db(self, db):
        db.upsert_book("b1", "Test", "/x.pdf", 100, 0)
        result = compute_overall_grade(db, "b1")
        assert result["grade"] == 0
        assert result["breakdown"] == {}
        assert result["label"] == "F"

    def test_nonexistent_book(self, db):
        result = compute_overall_grade(db, "nope")
        assert result["grade"] == 0


# ===========================================================================
# Reading only
# ===========================================================================


class TestReadingOnly:
    def test_no_chapters_completed(self, seeded_db):
        result = compute_overall_grade(seeded_db, "b1")
        assert result["grade"] == 0
        assert "reading" in result["breakdown"]
        # With only reading active, its weight should be 100%
        assert result["breakdown"]["reading"]["weight"] == 100

    def test_half_chapters_completed(self, seeded_db):
        for i in range(1, 6):
            seeded_db.update_reading_progress("b1", i, "completed")
        result = compute_overall_grade(seeded_db, "b1")
        assert result["grade"] == 50
        assert result["breakdown"]["reading"]["score"] == 50

    def test_all_chapters_completed(self, seeded_db):
        for i in range(1, 11):
            seeded_db.update_reading_progress("b1", i, "completed")
        result = compute_overall_grade(seeded_db, "b1")
        assert result["grade"] == 100
        assert result["label"] == "A+"


# ===========================================================================
# Multiple categories
# ===========================================================================


class TestMultipleCategories:
    def test_reading_and_quizzes(self, seeded_db):
        # 5/10 chapters completed = 50%
        for i in range(1, 6):
            seeded_db.update_reading_progress("b1", i, "completed")
        # 8/10 quiz questions correct = 80%
        for i in range(1, 11):
            seeded_db.save_quiz_answer(f"q{i}", "b1", 1, i <= 8, "ans")

        result = compute_overall_grade(seeded_db, "b1")
        bd = result["breakdown"]
        assert "reading" in bd
        assert "quizzes" in bd
        assert bd["reading"]["score"] == 50
        assert bd["quizzes"]["score"] == 80
        # Weights should redistribute: reading=40/(40+30)=57%, quizzes=30/(40+30)=43%
        assert bd["reading"]["weight"] == 57
        assert bd["quizzes"]["weight"] == 43
        # Grade: 50*0.571 + 80*0.429 ≈ 63
        assert 62 <= result["grade"] <= 64

    def test_all_four_categories(self, seeded_db):
        # Reading: 10/10 = 100%
        for i in range(1, 11):
            seeded_db.update_reading_progress("b1", i, "completed")
        # Quizzes: 9/10 = 90%
        for i in range(1, 11):
            seeded_db.save_quiz_answer(f"q{i}", "b1", 1, i <= 9, "ans")
        # Challenges: 3/4 = 75%
        for i in range(1, 5):
            seeded_db.save_challenge_progress(f"c{i}", "b1", 1, i <= 3, "code")
        # Project: 2/3 = 67%
        for i in range(1, 4):
            seeded_db.save_project_progress(f"s{i}", "b1", 1, i <= 2, "code")

        result = compute_overall_grade(seeded_db, "b1")
        bd = result["breakdown"]
        assert set(bd.keys()) == {"reading", "quizzes", "challenges", "project"}

        # Weights should be the defaults: 40, 30, 15, 15
        assert bd["reading"]["weight"] == 40
        assert bd["quizzes"]["weight"] == 30
        assert bd["challenges"]["weight"] == 15
        assert bd["project"]["weight"] == 15

        # Grade: 100*0.4 + 90*0.3 + 75*0.15 + 67*0.15 = 40+27+11.25+10.05 = 88.3
        assert 88 <= result["grade"] <= 89

    def test_perfect_score(self, seeded_db):
        for i in range(1, 11):
            seeded_db.update_reading_progress("b1", i, "completed")
        for i in range(1, 6):
            seeded_db.save_quiz_answer(f"q{i}", "b1", 1, True, "ans")
        for i in range(1, 4):
            seeded_db.save_challenge_progress(f"c{i}", "b1", 1, True, "code")
        for i in range(1, 3):
            seeded_db.save_project_progress(f"s{i}", "b1", 1, True, "code")

        result = compute_overall_grade(seeded_db, "b1")
        assert result["grade"] == 100
        assert result["label"] == "A+"

    def test_zero_score_all_wrong(self, seeded_db):
        # All quizzes wrong, no chapters completed
        for i in range(1, 6):
            seeded_db.save_quiz_answer(f"q{i}", "b1", 1, False, "wrong")

        result = compute_overall_grade(seeded_db, "b1")
        assert result["grade"] == 0


# ===========================================================================
# Weight redistribution
# ===========================================================================


class TestWeightRedistribution:
    def test_only_challenges(self, db):
        # Book with 0 chapters — reading has no data
        db.upsert_book("b2", "No Chapters", "/x.pdf", 100, 0)
        db.save_challenge_progress("c1", "b2", 1, True, "code")
        result = compute_overall_grade(db, "b2")
        assert result["breakdown"]["challenges"]["weight"] == 100

    def test_reading_and_project_only(self, seeded_db):
        for i in range(1, 11):
            seeded_db.update_reading_progress("b1", i, "completed")
        seeded_db.save_project_progress("s1", "b1", 1, True, "code")

        result = compute_overall_grade(seeded_db, "b1")
        bd = result["breakdown"]
        # reading=40, project=15 → reading=40/55=73%, project=15/55=27%
        assert bd["reading"]["weight"] == 73
        assert bd["project"]["weight"] == 27


# ===========================================================================
# Breakdown details
# ===========================================================================


class TestBreakdown:
    def test_numerator_denominator(self, seeded_db):
        for i in range(1, 4):
            seeded_db.update_reading_progress("b1", i, "completed")

        result = compute_overall_grade(seeded_db, "b1")
        r = result["breakdown"]["reading"]
        assert r["numerator"] == 3
        assert r["denominator"] == 10
        assert r["score"] == 30

    def test_quiz_accuracy(self, seeded_db):
        seeded_db.save_quiz_answer("q1", "b1", 1, True, "a")
        seeded_db.save_quiz_answer("q2", "b1", 1, True, "b")
        seeded_db.save_quiz_answer("q3", "b1", 1, False, "c")

        result = compute_overall_grade(seeded_db, "b1")
        q = result["breakdown"]["quizzes"]
        assert q["numerator"] == 2
        assert q["denominator"] == 3
        assert q["score"] == 67


# ===========================================================================
# Grade labels
# ===========================================================================


class TestGradeLabel:
    @pytest.mark.parametrize(
        "grade,expected",
        [
            (100, "A+"),
            (97, "A+"),
            (96, "A"),
            (93, "A"),
            (92, "A-"),
            (90, "A-"),
            (89, "B+"),
            (87, "B+"),
            (86, "B"),
            (83, "B"),
            (82, "B-"),
            (80, "B-"),
            (79, "C+"),
            (77, "C+"),
            (76, "C"),
            (73, "C"),
            (72, "C-"),
            (70, "C-"),
            (65, "D"),
            (60, "D"),
            (59, "F"),
            (0, "F"),
        ],
    )
    def test_label(self, grade, expected):
        assert _grade_label(grade) == expected
