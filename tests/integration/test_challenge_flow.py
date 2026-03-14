# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Integration tests for the challenge feature."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest


def _noop_messagebox(*args, **kwargs):
    return None


@pytest.fixture()
def challenge_content(tmp_path: Path) -> Path:
    """Create challenge content in a temp directory."""
    ch_dir = tmp_path / "content" / "test_book" / "challenges"
    ch_dir.mkdir(parents=True)

    data = {
        "book_id": "test_book",
        "chapter_num": 1,
        "challenges": [
            {
                "id": "tb_c01",
                "title": "Add Numbers",
                "description": "Create result = a + b",
                "starter_code": "a = 1\nb = 2\nresult = 0  # fix this\n",
                "test_code": "assert result == 3, f'Expected 3, got {result}'",
                "difficulty": "easy",
                "hints": ["Change 0 to a + b"],
            },
            {
                "id": "tb_c02",
                "title": "String Upper",
                "description": "Make text uppercase",
                "starter_code": "text = 'hello'\nupper_text = ''  # fix this\n",
                "test_code": "assert upper_text == 'HELLO', f'Expected HELLO, got {upper_text}'",
                "difficulty": "easy",
                "hints": ["Use .upper()"],
            },
        ],
    }
    (ch_dir / "ch01.json").write_text(json.dumps(data), encoding="utf-8")
    return tmp_path / "content"


@pytest.fixture()
def isolated_main_window(qtbot, tmp_path, monkeypatch, challenge_content):
    """MainWindow with isolated config/db and challenge content."""
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
    monkeypatch.setattr("pylearn.core.content_loader.CONTENT_DIR", challenge_content)

    from pylearn.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)

    yield window

    window._session.reset()


class TestChallengeTabExists:
    def test_challenge_tab_present(self, isolated_main_window) -> None:
        window = isolated_main_window
        assert window._right_tabs.tabText(2) == "Challenge"


class TestShowChallengeNoBook:
    @patch("pylearn.ui.main_window.QMessageBox.information", _noop_messagebox)
    def test_show_challenge_no_book(self, isolated_main_window) -> None:
        window = isolated_main_window
        assert window._book.current_book is None
        window._show_challenge()


class TestChallengePanelDirect:
    def test_load_challenges(self, qtbot, tmp_path: Path, challenge_content: Path) -> None:
        from pylearn.core.content_loader import ContentLoader
        from pylearn.core.database import Database
        from pylearn.executor.session import Session
        from pylearn.ui.challenge_panel import ChallengePanel

        db = Database(tmp_path / "test.db")
        loader = ContentLoader(challenge_content)
        session = Session(timeout=10)
        try:
            db.upsert_book("test_book", "Test", "/p", 100, 5)
            panel = ChallengePanel(db, loader, session)
            qtbot.addWidget(panel)
            panel.show()

            result = panel.load_challenges("test_book", 1)
            assert result is True
            assert panel._challenges is not None
            assert len(panel._challenges.challenges) == 2
            assert "Add Numbers" in panel._title_label.text() or "Chapter 1" in panel._title_label.text()
        finally:
            session.reset()
            db.close()

    def test_load_nonexistent(self, qtbot, tmp_path: Path, challenge_content: Path) -> None:
        from pylearn.core.content_loader import ContentLoader
        from pylearn.core.database import Database
        from pylearn.executor.session import Session
        from pylearn.ui.challenge_panel import ChallengePanel

        db = Database(tmp_path / "test2.db")
        loader = ContentLoader(challenge_content)
        session = Session(timeout=10)
        try:
            panel = ChallengePanel(db, loader, session)
            qtbot.addWidget(panel)
            assert panel.load_challenges("test_book", 99) is False
        finally:
            session.reset()
            db.close()

    def test_navigation(self, qtbot, tmp_path: Path, challenge_content: Path) -> None:
        from pylearn.core.content_loader import ContentLoader
        from pylearn.core.database import Database
        from pylearn.executor.session import Session
        from pylearn.ui.challenge_panel import ChallengePanel

        db = Database(tmp_path / "test3.db")
        loader = ContentLoader(challenge_content)
        session = Session(timeout=10)
        try:
            panel = ChallengePanel(db, loader, session)
            qtbot.addWidget(panel)
            panel.show()
            panel.load_challenges("test_book", 1)

            assert panel._current_index == 0
            assert not panel._prev_btn.isEnabled()
            assert panel._next_btn.isEnabled()

            panel._next_challenge()
            assert panel._current_index == 1
            assert panel._prev_btn.isEnabled()
            assert not panel._next_btn.isEnabled()

            panel._prev_challenge()
            assert panel._current_index == 0
        finally:
            session.reset()
            db.close()

    def test_reset_code(self, qtbot, tmp_path: Path, challenge_content: Path) -> None:
        from pylearn.core.content_loader import ContentLoader
        from pylearn.core.database import Database
        from pylearn.executor.session import Session
        from pylearn.ui.challenge_panel import ChallengePanel

        db = Database(tmp_path / "test4.db")
        loader = ContentLoader(challenge_content)
        session = Session(timeout=10)
        try:
            panel = ChallengePanel(db, loader, session)
            qtbot.addWidget(panel)
            panel.load_challenges("test_book", 1)

            original = panel._editor.text()
            panel._editor.setText("modified code")
            panel._reset_code()
            assert panel._editor.text() == original
        finally:
            session.reset()
            db.close()

    def test_hints(self, qtbot, tmp_path: Path, challenge_content: Path) -> None:
        from pylearn.core.content_loader import ContentLoader
        from pylearn.core.database import Database
        from pylearn.executor.session import Session
        from pylearn.ui.challenge_panel import ChallengePanel

        db = Database(tmp_path / "test5.db")
        loader = ContentLoader(challenge_content)
        session = Session(timeout=10)
        try:
            panel = ChallengePanel(db, loader, session)
            qtbot.addWidget(panel)
            panel.show()
            panel.load_challenges("test_book", 1)

            assert panel._hints_widget.isVisible()
            assert panel._hint_label.text() == ""

            panel._show_next_hint()
            assert "a + b" in panel._hint_label.text()
        finally:
            session.reset()
            db.close()

    @pytest.mark.parametrize("theme", ["light", "dark", "sepia"])
    def test_theme_change(self, qtbot, tmp_path: Path, challenge_content: Path, theme: str) -> None:
        from pylearn.core.content_loader import ContentLoader
        from pylearn.core.database import Database
        from pylearn.executor.session import Session
        from pylearn.ui.challenge_panel import ChallengePanel

        db = Database(tmp_path / f"test_theme_{theme}.db")
        loader = ContentLoader(challenge_content)
        session = Session(timeout=10)
        try:
            panel = ChallengePanel(db, loader, session)
            qtbot.addWidget(panel)
            panel.set_theme(theme)
            assert panel._theme == theme
        finally:
            session.reset()
            db.close()
