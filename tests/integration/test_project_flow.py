# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Integration tests for the project feature."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest


def _noop_messagebox(*args, **kwargs):
    return None


@pytest.fixture()
def project_content(tmp_path: Path) -> Path:
    """Create project content in a temp directory."""
    proj_dir = tmp_path / "content" / "test_book" / "project"
    proj_dir.mkdir(parents=True)

    meta = {
        "book_id": "test_book",
        "title": "Test Project",
        "description": "A test project",
    }
    (proj_dir / "project.json").write_text(json.dumps(meta), encoding="utf-8")

    step1 = {
        "step_id": "tp_s01",
        "book_id": "test_book",
        "chapter_num": 1,
        "title": "Create Variable",
        "description": "Set x = 10",
        "starter_code": "x = 0  # fix\n",
        "test_code": "assert x == 10, f'Expected 10, got {x}'",
        "acceptance_criteria": ["x equals 10"],
        "hints": ["Change 0 to 10"],
    }
    (proj_dir / "ch01.json").write_text(json.dumps(step1), encoding="utf-8")

    step2 = {
        "step_id": "tp_s02",
        "book_id": "test_book",
        "chapter_num": 2,
        "title": "Double It",
        "description": "Create y = x * 2",
        "builds_on": "tp_s01",
        "starter_code": "x = 10\ny = 0  # fix\n",
        "test_code": "assert y == 20, f'Expected 20, got {y}'",
    }
    (proj_dir / "ch02.json").write_text(json.dumps(step2), encoding="utf-8")

    return tmp_path / "content"


@pytest.fixture()
def isolated_main_window(qtbot, tmp_path, monkeypatch, project_content):
    config_dir = tmp_path / "config"
    config_dir.mkdir(exist_ok=True)
    data_dir = tmp_path / "data"
    data_dir.mkdir(exist_ok=True)
    cache_dir = data_dir / "cache"
    cache_dir.mkdir(exist_ok=True)

    monkeypatch.setattr("pylearn.core.constants.CONFIG_DIR", config_dir)
    monkeypatch.setattr("pylearn.core.constants.DATA_DIR", data_dir)
    monkeypatch.setattr("pylearn.core.constants.CACHE_DIR", cache_dir)
    monkeypatch.setattr("pylearn.core.constants.DB_PATH", data_dir / "test.db")
    monkeypatch.setattr("pylearn.core.constants.APP_CONFIG_PATH", config_dir / "app_config.json")
    monkeypatch.setattr("pylearn.core.constants.BOOKS_CONFIG_PATH", config_dir / "books.json")
    monkeypatch.setattr("pylearn.core.constants.EDITOR_CONFIG_PATH", config_dir / "editor_config.json")
    monkeypatch.setattr("pylearn.core.config.APP_CONFIG_PATH", config_dir / "app_config.json")
    monkeypatch.setattr("pylearn.core.config.BOOKS_CONFIG_PATH", config_dir / "books.json")
    monkeypatch.setattr("pylearn.core.config.EDITOR_CONFIG_PATH", config_dir / "editor_config.json")
    monkeypatch.setattr("pylearn.core.content_loader.CONTENT_DIR", project_content)

    from pylearn.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    yield window
    window._session.reset()


class TestProjectTabExists:
    def test_project_tab_present(self, isolated_main_window) -> None:
        assert isolated_main_window._right_tabs.tabText(3) == "Project"


class TestShowProjectNoBook:
    @patch("pylearn.ui.main_window.QMessageBox.information", _noop_messagebox)
    def test_show_project_no_book(self, isolated_main_window) -> None:
        isolated_main_window._show_project()


class TestProjectPanelDirect:
    def test_load_project(self, qtbot, tmp_path: Path, project_content: Path) -> None:
        from pylearn.core.content_loader import ContentLoader
        from pylearn.core.database import Database
        from pylearn.executor.session import Session
        from pylearn.ui.project_panel import ProjectPanel

        db = Database(tmp_path / "test.db")
        loader = ContentLoader(project_content)
        session = Session(timeout=10)
        try:
            db.upsert_book("test_book", "Test", "/p", 100, 5)
            panel = ProjectPanel(db, loader, session)
            qtbot.addWidget(panel)
            panel.show()

            result = panel.load_project("test_book")
            assert result is True
            assert panel._meta is not None
            assert panel._meta.title == "Test Project"
            assert len(panel._steps) == 2
            assert panel._step_list.count() == 2
        finally:
            session.reset()
            db.close()

    def test_load_nonexistent(self, qtbot, tmp_path: Path, project_content: Path) -> None:
        from pylearn.core.content_loader import ContentLoader
        from pylearn.core.database import Database
        from pylearn.executor.session import Session
        from pylearn.ui.project_panel import ProjectPanel

        db = Database(tmp_path / "test2.db")
        loader = ContentLoader(project_content)
        session = Session(timeout=10)
        try:
            panel = ProjectPanel(db, loader, session)
            qtbot.addWidget(panel)
            assert panel.load_project("no_book") is False
        finally:
            session.reset()
            db.close()

    def test_step_navigation(self, qtbot, tmp_path: Path, project_content: Path) -> None:
        from pylearn.core.content_loader import ContentLoader
        from pylearn.core.database import Database
        from pylearn.executor.session import Session
        from pylearn.ui.project_panel import ProjectPanel

        db = Database(tmp_path / "test3.db")
        loader = ContentLoader(project_content)
        session = Session(timeout=10)
        try:
            db.upsert_book("test_book", "Test", "/p", 100, 5)
            panel = ProjectPanel(db, loader, session)
            qtbot.addWidget(panel)
            panel.show()
            panel.load_project("test_book")

            # First step selected by default
            assert panel._current_step_index == 0
            assert "Create Variable" in panel._step_browser.toPlainText()

            # Select second step
            panel._step_list.setCurrentRow(1)
            assert panel._current_step_index == 1
            assert "Double It" in panel._step_browser.toPlainText()
        finally:
            session.reset()
            db.close()

    def test_load_previous_code(self, qtbot, tmp_path: Path, project_content: Path) -> None:
        from pylearn.core.content_loader import ContentLoader
        from pylearn.core.database import Database
        from pylearn.executor.session import Session
        from pylearn.ui.project_panel import ProjectPanel

        db = Database(tmp_path / "test4.db")
        loader = ContentLoader(project_content)
        session = Session(timeout=10)
        try:
            db.upsert_book("test_book", "Test", "/p", 100, 5)
            # Save some code for step 1
            db.save_project_progress("tp_s01", "test_book", 1, True, "x = 10\n# my solution\n")

            panel = ProjectPanel(db, loader, session)
            qtbot.addWidget(panel)
            panel.show()
            panel.load_project("test_book")

            # Go to step 2
            panel._step_list.setCurrentRow(1)
            assert panel._current_step_index == 1

            # Load previous step's code
            panel._load_previous_code()
            assert "x = 10" in panel._editor.text()
            assert "my solution" in panel._editor.text()
        finally:
            session.reset()
            db.close()

    def test_reset_code(self, qtbot, tmp_path: Path, project_content: Path) -> None:
        from pylearn.core.content_loader import ContentLoader
        from pylearn.core.database import Database
        from pylearn.executor.session import Session
        from pylearn.ui.project_panel import ProjectPanel

        db = Database(tmp_path / "test5.db")
        loader = ContentLoader(project_content)
        session = Session(timeout=10)
        try:
            panel = ProjectPanel(db, loader, session)
            qtbot.addWidget(panel)
            panel.load_project("test_book")

            original = panel._editor.text()
            panel._editor.setText("modified")
            panel._reset_code()
            assert panel._editor.text() == original
        finally:
            session.reset()
            db.close()

    def test_hints(self, qtbot, tmp_path: Path, project_content: Path) -> None:
        from pylearn.core.content_loader import ContentLoader
        from pylearn.core.database import Database
        from pylearn.executor.session import Session
        from pylearn.ui.project_panel import ProjectPanel

        db = Database(tmp_path / "test6.db")
        loader = ContentLoader(project_content)
        session = Session(timeout=10)
        try:
            db.upsert_book("test_book", "Test", "/p", 100, 5)
            panel = ProjectPanel(db, loader, session)
            qtbot.addWidget(panel)
            panel.show()
            panel.load_project("test_book")

            # Step 1 has hints
            assert panel._hints_widget.isVisible()
            panel._show_next_hint()
            assert "10" in panel._hint_label.text()
        finally:
            session.reset()
            db.close()

    @pytest.mark.parametrize("theme", ["light", "dark", "sepia"])
    def test_theme_change(self, qtbot, tmp_path: Path, project_content: Path, theme: str) -> None:
        from pylearn.core.content_loader import ContentLoader
        from pylearn.core.database import Database
        from pylearn.executor.session import Session
        from pylearn.ui.project_panel import ProjectPanel

        db = Database(tmp_path / f"test_theme_{theme}.db")
        loader = ContentLoader(project_content)
        session = Session(timeout=10)
        try:
            panel = ProjectPanel(db, loader, session)
            qtbot.addWidget(panel)
            panel.set_theme(theme)
            assert panel._theme == theme
        finally:
            session.reset()
            db.close()


class TestProjectThemeIntegration:
    @pytest.mark.parametrize("theme", ["light", "dark", "sepia"])
    def test_theme_applies_to_project(self, isolated_main_window, theme: str) -> None:
        isolated_main_window._on_theme_changed(theme)
        assert isolated_main_window._project_panel._theme == theme
