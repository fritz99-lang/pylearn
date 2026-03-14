# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Tests for project data models, ContentLoader project methods, and DB methods."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pylearn.core.content_loader import ContentLoader
from pylearn.core.models import ProjectMeta, ProjectStep


@pytest.fixture
def content_dir(tmp_path: Path) -> Path:
    """Create temp content with project data."""
    proj_dir = tmp_path / "test_book" / "project"
    proj_dir.mkdir(parents=True)

    meta = {
        "book_id": "test_book",
        "title": "Test Project",
        "description": "Build something cool",
        "final_description": "A cool thing",
    }
    (proj_dir / "project.json").write_text(json.dumps(meta), encoding="utf-8")

    step1 = {
        "step_id": "tp_ch01",
        "book_id": "test_book",
        "chapter_num": 1,
        "title": "Step One",
        "description": "Create x = 42",
        "starter_code": "x = 0  # fix this\n",
        "test_code": "assert x == 42",
        "acceptance_criteria": ["x equals 42"],
        "hints": ["Set x to 42"],
    }
    (proj_dir / "ch01.json").write_text(json.dumps(step1), encoding="utf-8")

    step2 = {
        "step_id": "tp_ch02",
        "book_id": "test_book",
        "chapter_num": 2,
        "title": "Step Two",
        "description": "Create y = x * 2",
        "builds_on": "tp_ch01",
        "starter_code": "x = 42\ny = 0  # fix this\n",
        "test_code": "assert y == 84",
    }
    (proj_dir / "ch02.json").write_text(json.dumps(step2), encoding="utf-8")

    return tmp_path


@pytest.fixture
def loader(content_dir: Path) -> ContentLoader:
    return ContentLoader(content_dir)


class TestProjectMeta:
    def test_from_dict(self) -> None:
        data = {"book_id": "b1", "title": "T", "description": "D", "final_description": "F"}
        m = ProjectMeta.from_dict(data)
        assert m.title == "T"
        assert m.final_description == "F"

    def test_from_dict_missing_key(self) -> None:
        with pytest.raises(ValueError, match="missing required key"):
            ProjectMeta.from_dict({"book_id": "b1"})


class TestProjectStep:
    def test_from_dict(self) -> None:
        data = {
            "step_id": "s1",
            "book_id": "b1",
            "chapter_num": 1,
            "title": "S",
            "description": "D",
            "starter_code": "x = 0",
            "test_code": "assert x == 0",
            "builds_on": "s0",
            "acceptance_criteria": ["works"],
            "hints": ["try harder"],
        }
        s = ProjectStep.from_dict(data)
        assert s.step_id == "s1"
        assert s.builds_on == "s0"
        assert s.acceptance_criteria == ["works"]
        assert s.hints == ["try harder"]

    def test_from_dict_missing_key(self) -> None:
        with pytest.raises(ValueError, match="missing required key"):
            ProjectStep.from_dict({"step_id": "s1"})


class TestContentLoaderProject:
    def test_load_project_meta(self, loader: ContentLoader) -> None:
        meta = loader.load_project_meta("test_book")
        assert meta is not None
        assert meta.title == "Test Project"

    def test_load_project_meta_nonexistent(self, loader: ContentLoader) -> None:
        assert loader.load_project_meta("no_book") is None

    def test_load_project_step(self, loader: ContentLoader) -> None:
        step = loader.load_project_step("test_book", 1)
        assert step is not None
        assert step.step_id == "tp_ch01"
        assert step.title == "Step One"

    def test_load_project_step_nonexistent(self, loader: ContentLoader) -> None:
        assert loader.load_project_step("test_book", 99) is None

    def test_list_project_steps(self, loader: ContentLoader) -> None:
        assert loader.list_project_steps("test_book") == [1, 2]

    def test_has_project(self, loader: ContentLoader) -> None:
        assert loader.has_project("test_book") is True
        assert loader.has_project("no_book") is False


class TestProjectDatabaseMethods:
    def test_save_and_get_progress(self, tmp_path: Path) -> None:
        from pylearn.core.database import Database

        db = Database(tmp_path / "test.db")
        try:
            db.upsert_book("b1", "Book", "/p", 100, 5)
            db.save_project_progress("s1", "b1", 1, True, "x = 42")

            p = db.get_project_progress("s1")
            assert p is not None
            assert p["completed"] == 1
            assert p["user_code"] == "x = 42"
        finally:
            db.close()

    def test_completed_stays_true(self, tmp_path: Path) -> None:
        from pylearn.core.database import Database

        db = Database(tmp_path / "test.db")
        try:
            db.upsert_book("b1", "Book", "/p", 100, 5)
            db.save_project_progress("s1", "b1", 1, True, "good")
            db.save_project_progress("s1", "b1", 1, False, "wip")

            p = db.get_project_progress("s1")
            assert p is not None
            assert p["completed"] == 1  # Still completed
            assert p["user_code"] == "wip"  # Code updated
        finally:
            db.close()

    def test_get_project_steps_progress(self, tmp_path: Path) -> None:
        from pylearn.core.database import Database

        db = Database(tmp_path / "test.db")
        try:
            db.upsert_book("b1", "Book", "/p", 100, 5)
            db.save_project_progress("s1", "b1", 1, True, "code1")
            db.save_project_progress("s2", "b1", 2, False, "code2")

            steps = db.get_project_steps_progress("b1")
            assert len(steps) == 2
            assert steps[0]["step_id"] == "s1"
            assert steps[1]["step_id"] == "s2"
        finally:
            db.close()

    def test_get_project_stats(self, tmp_path: Path) -> None:
        from pylearn.core.database import Database

        db = Database(tmp_path / "test.db")
        try:
            db.upsert_book("b1", "Book", "/p", 100, 5)
            db.save_project_progress("s1", "b1", 1, True, "c1")
            db.save_project_progress("s2", "b1", 2, False, "c2")
            db.save_project_progress("s3", "b1", 3, True, "c3")

            stats = db.get_project_stats("b1")
            assert stats["total"] == 3
            assert stats["completed"] == 2
        finally:
            db.close()

    def test_get_progress_nonexistent(self, tmp_path: Path) -> None:
        from pylearn.core.database import Database

        db = Database(tmp_path / "test.db")
        try:
            assert db.get_project_progress("nope") is None
        finally:
            db.close()
