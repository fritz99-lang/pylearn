# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Tests for challenge data models, ContentLoader challenge methods, and DB methods."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pylearn.core.content_loader import ContentLoader
from pylearn.core.models import ChallengeSet, ChallengeSpec


@pytest.fixture
def content_dir(tmp_path: Path) -> Path:
    """Create temp content with challenge data."""
    ch_dir = tmp_path / "test_book" / "challenges"
    ch_dir.mkdir(parents=True)

    data = {
        "book_id": "test_book",
        "chapter_num": 1,
        "challenges": [
            {
                "id": "tb_c01",
                "title": "Hello World",
                "description": "Print hello",
                "starter_code": "# your code\n",
                "test_code": "assert greeting == 'hello'",
                "difficulty": "easy",
                "hints": ["Use print()"],
            },
            {
                "id": "tb_c02",
                "title": "Add Numbers",
                "description": "Add two numbers",
                "starter_code": "a = 1\nb = 2\nresult = # fix\n",
                "test_code": "assert result == 3\nassert isinstance(result, int)",
                "difficulty": "medium",
                "concepts_new": ["arithmetic"],
            },
        ],
    }
    (ch_dir / "ch01.json").write_text(json.dumps(data), encoding="utf-8")
    return tmp_path


@pytest.fixture
def loader(content_dir: Path) -> ContentLoader:
    return ContentLoader(content_dir)


class TestChallengeSpec:
    def test_from_dict(self) -> None:
        data = {
            "id": "c1",
            "title": "Test",
            "description": "Do it",
            "starter_code": "x = 0",
            "test_code": "assert x == 0",
            "difficulty": "hard",
            "hints": ["hint1"],
        }
        c = ChallengeSpec.from_dict(data)
        assert c.challenge_id == "c1"
        assert c.title == "Test"
        assert c.difficulty == "hard"
        assert c.hints == ["hint1"]

    def test_from_dict_missing_key(self) -> None:
        with pytest.raises(ValueError, match="missing required key"):
            ChallengeSpec.from_dict({"id": "c1", "title": "T"})


class TestChallengeSet:
    def test_from_dict(self) -> None:
        data = {
            "book_id": "b1",
            "chapter_num": 3,
            "challenges": [
                {"id": "c1", "title": "T", "description": "D", "starter_code": "", "test_code": "assert True"}
            ],
        }
        cs = ChallengeSet.from_dict(data)
        assert cs.book_id == "b1"
        assert cs.chapter_num == 3
        assert len(cs.challenges) == 1


class TestContentLoaderChallenges:
    def test_load_challenges(self, loader: ContentLoader) -> None:
        cs = loader.load_challenges("test_book", 1)
        assert cs is not None
        assert len(cs.challenges) == 2
        assert cs.challenges[0].challenge_id == "tb_c01"

    def test_load_challenges_nonexistent(self, loader: ContentLoader) -> None:
        assert loader.load_challenges("test_book", 99) is None

    def test_has_challenges(self, loader: ContentLoader) -> None:
        assert loader.has_challenges("test_book", 1) is True
        assert loader.has_challenges("test_book", 2) is False

    def test_list_challenge_chapters(self, loader: ContentLoader) -> None:
        assert loader.list_challenge_chapters("test_book") == [1]


class TestChallengeDatabaseMethods:
    def test_save_and_get_progress(self, tmp_path: Path) -> None:
        from pylearn.core.database import Database

        db = Database(tmp_path / "test.db")
        try:
            db.upsert_book("b1", "Book", "/p", 100, 5)
            db.save_challenge_progress("c1", "b1", 1, True, "x = 42")

            p = db.get_challenge_progress("c1")
            assert p is not None
            assert p["passed"] == 1
            assert p["user_code"] == "x = 42"
            assert p["best_code"] == "x = 42"
            assert p["attempts"] == 1
        finally:
            db.close()

    def test_attempts_increment(self, tmp_path: Path) -> None:
        from pylearn.core.database import Database

        db = Database(tmp_path / "test.db")
        try:
            db.upsert_book("b1", "Book", "/p", 100, 5)
            db.save_challenge_progress("c1", "b1", 1, False, "v1")
            db.save_challenge_progress("c1", "b1", 1, False, "v2")

            p = db.get_challenge_progress("c1")
            assert p is not None
            assert p["attempts"] == 2
            assert p["user_code"] == "v2"
        finally:
            db.close()

    def test_passed_stays_true(self, tmp_path: Path) -> None:
        """Once passed, subsequent failures don't reset the passed flag."""
        from pylearn.core.database import Database

        db = Database(tmp_path / "test.db")
        try:
            db.upsert_book("b1", "Book", "/p", 100, 5)
            db.save_challenge_progress("c1", "b1", 1, True, "good")
            db.save_challenge_progress("c1", "b1", 1, False, "bad")

            p = db.get_challenge_progress("c1")
            assert p is not None
            assert p["passed"] == 1  # Still passed
            assert p["best_code"] == "good"  # Best code preserved
            assert p["user_code"] == "bad"  # Current code updated
        finally:
            db.close()

    def test_get_challenge_stats(self, tmp_path: Path) -> None:
        from pylearn.core.database import Database

        db = Database(tmp_path / "test.db")
        try:
            db.upsert_book("b1", "Book", "/p", 100, 5)
            db.save_challenge_progress("c1", "b1", 1, True, "code1")
            db.save_challenge_progress("c2", "b1", 1, False, "code2")
            db.save_challenge_progress("c3", "b1", 2, True, "code3")

            stats = db.get_challenge_stats("b1", 1)
            assert stats["total"] == 2
            assert stats["passed"] == 1

            stats_all = db.get_challenge_stats("b1")
            assert stats_all["total"] == 3
            assert stats_all["passed"] == 2
        finally:
            db.close()
