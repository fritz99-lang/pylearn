# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Integration tests for quiz feature: panel loading, answering, navigation, theme, retry."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest


def _noop_messagebox(*args, **kwargs):
    return None


@pytest.fixture()
def quiz_content(tmp_path: Path) -> Path:
    """Create quiz content in a temp directory."""
    quiz_dir = tmp_path / "content" / "test_book" / "quizzes"
    quiz_dir.mkdir(parents=True)

    quiz = {
        "book_id": "test_book",
        "chapter_num": 1,
        "questions": [
            {
                "id": "tb_q01",
                "type": "multiple_choice",
                "question": "What is 1+1?",
                "choices": ["1", "2", "3", "4"],
                "correct": 1,
                "explanation": "Basic math.",
            },
            {
                "id": "tb_q02",
                "type": "fill_in_blank",
                "question": "Python uses ___ for indentation.",
                "correct": "spaces",
                "explanation": "Spaces (or tabs) are used.",
            },
            {
                "id": "tb_q03",
                "type": "multiple_choice",
                "question": "Which is a list?",
                "choices": ["()", "[]", "{}", "<>"],
                "correct": 1,
                "explanation": "Square brackets.",
            },
        ],
    }
    (quiz_dir / "ch01.json").write_text(json.dumps(quiz), encoding="utf-8")
    return tmp_path / "content"


@pytest.fixture()
def isolated_main_window(qtbot, tmp_path, monkeypatch, quiz_content):
    """MainWindow with isolated config/db and quiz content."""
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

    # Patch ContentLoader to use our quiz content dir
    monkeypatch.setattr("pylearn.core.content_loader.CONTENT_DIR", quiz_content)

    from pylearn.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)

    yield window

    window._session.reset()


class TestQuizTabExists:
    """Verify the tab refactor worked — right panel has tabs."""

    def test_right_panel_has_tabs(self, isolated_main_window) -> None:
        window = isolated_main_window
        assert window._right_tabs.count() == 4
        assert window._right_tabs.tabText(0) == "Editor"
        assert window._right_tabs.tabText(1) == "Quiz"
        assert window._right_tabs.tabText(2) == "Challenge"
        assert window._right_tabs.tabText(3) == "Project"

    def test_editor_is_default_tab(self, isolated_main_window) -> None:
        window = isolated_main_window
        assert window._right_tabs.currentIndex() == 0


class TestShowQuizNoBook:
    """_show_quiz with no book loaded shows a message."""

    @patch("pylearn.ui.main_window.QMessageBox.information", _noop_messagebox)
    def test_show_quiz_no_book(self, isolated_main_window) -> None:
        window = isolated_main_window
        assert window._book.current_book is None
        window._show_quiz()  # Should not crash


class TestQuizPanelDirect:
    """Test QuizPanel widget directly with a real database."""

    def test_load_quiz(self, qtbot, tmp_path: Path, quiz_content: Path) -> None:
        """Load a quiz and verify state."""
        from pylearn.core.content_loader import ContentLoader
        from pylearn.core.database import Database
        from pylearn.ui.quiz_panel import QuizPanel

        db = Database(tmp_path / "direct_test.db")
        loader = ContentLoader(quiz_content)
        try:
            db.upsert_book("test_book", "Test Book", "/path", 100, 5)

            panel = QuizPanel(db, loader)
            qtbot.addWidget(panel)
            result = panel.load_quiz("test_book", 1)
            assert result is True
            assert panel._quiz is not None
            assert len(panel._quiz.questions) == 3
            assert panel._current_index == 0
            assert panel._title_label.text() == "Chapter 1 Quiz"
            assert "1 of 3" in panel._progress_label.text()
        finally:
            db.close()

    def test_load_quiz_nonexistent(self, qtbot, tmp_path: Path, quiz_content: Path) -> None:
        """Loading a non-existent quiz returns False."""
        from pylearn.core.content_loader import ContentLoader
        from pylearn.core.database import Database
        from pylearn.ui.quiz_panel import QuizPanel

        db = Database(tmp_path / "direct_test2.db")
        loader = ContentLoader(quiz_content)
        try:
            panel = QuizPanel(db, loader)
            qtbot.addWidget(panel)
            result = panel.load_quiz("test_book", 99)
            assert result is False
            assert panel._title_label.text() == "No Quiz Available"
        finally:
            db.close()

    def test_answer_mc_question(self, qtbot, tmp_path: Path, quiz_content: Path) -> None:
        """Answer an MC question and verify it's saved."""
        from pylearn.core.content_loader import ContentLoader
        from pylearn.core.database import Database
        from pylearn.ui.quiz_panel import QuizPanel

        db = Database(tmp_path / "direct_test3.db")
        loader = ContentLoader(quiz_content)
        try:
            db.upsert_book("test_book", "Test Book", "/path", 100, 5)
            panel = QuizPanel(db, loader)
            qtbot.addWidget(panel)
            panel.load_quiz("test_book", 1)

            # Select the correct answer (index 1 = "2")
            buttons = panel._button_group.buttons()
            assert len(buttons) == 4
            buttons[1].setChecked(True)
            panel._check_answer()

            # Verify saved
            saved = db.get_quiz_answer("tb_q01")
            assert saved is not None
            assert saved["correct"] == 1
            assert saved["user_answer"] == "1"

            # Feedback text should be set
            assert "Correct" in panel._feedback_label.text()
        finally:
            db.close()

    def test_answer_fill_in_blank(self, qtbot, tmp_path: Path, quiz_content: Path) -> None:
        """Answer a fill-in-blank question."""
        from pylearn.core.content_loader import ContentLoader
        from pylearn.core.database import Database
        from pylearn.ui.quiz_panel import QuizPanel

        db = Database(tmp_path / "direct_test4.db")
        loader = ContentLoader(quiz_content)
        try:
            db.upsert_book("test_book", "Test Book", "/path", 100, 5)
            panel = QuizPanel(db, loader)
            qtbot.addWidget(panel)
            panel.show()
            panel.load_quiz("test_book", 1)

            # Navigate to q2 (fill-in-blank)
            panel._next_question()
            assert panel._current_index == 1
            assert panel._fill_input.isVisible()

            # Type answer
            panel._fill_input.setText("spaces")
            panel._check_answer()

            saved = db.get_quiz_answer("tb_q02")
            assert saved is not None
            assert saved["correct"] == 1
            assert "Correct" in panel._feedback_label.text()
        finally:
            db.close()

    def test_wrong_answer(self, qtbot, tmp_path: Path, quiz_content: Path) -> None:
        """Wrong answer shows the correct one."""
        from pylearn.core.content_loader import ContentLoader
        from pylearn.core.database import Database
        from pylearn.ui.quiz_panel import QuizPanel

        db = Database(tmp_path / "direct_test5.db")
        loader = ContentLoader(quiz_content)
        try:
            db.upsert_book("test_book", "Test Book", "/path", 100, 5)
            panel = QuizPanel(db, loader)
            qtbot.addWidget(panel)
            panel.load_quiz("test_book", 1)

            # Select wrong answer (index 0 = "1")
            buttons = panel._button_group.buttons()
            buttons[0].setChecked(True)
            panel._check_answer()

            saved = db.get_quiz_answer("tb_q01")
            assert saved is not None
            assert saved["correct"] == 0
            assert "Incorrect" in panel._feedback_label.text()
            assert "2" in panel._feedback_label.text()  # Shows correct answer
        finally:
            db.close()

    def test_navigation(self, qtbot, tmp_path: Path, quiz_content: Path) -> None:
        """Navigate between questions."""
        from pylearn.core.content_loader import ContentLoader
        from pylearn.core.database import Database
        from pylearn.ui.quiz_panel import QuizPanel

        db = Database(tmp_path / "direct_test6.db")
        loader = ContentLoader(quiz_content)
        try:
            panel = QuizPanel(db, loader)
            qtbot.addWidget(panel)
            panel.load_quiz("test_book", 1)

            assert panel._current_index == 0
            assert not panel._prev_btn.isEnabled()
            assert panel._next_btn.isEnabled()

            panel._next_question()
            assert panel._current_index == 1
            assert panel._prev_btn.isEnabled()

            panel._next_question()
            assert panel._current_index == 2
            assert not panel._next_btn.isEnabled()  # Last question

            panel._prev_question()
            assert panel._current_index == 1
        finally:
            db.close()

    def test_retry_quiz(self, qtbot, tmp_path: Path, quiz_content: Path) -> None:
        """Retry clears all progress and resets to question 1."""
        from pylearn.core.content_loader import ContentLoader
        from pylearn.core.database import Database
        from pylearn.ui.quiz_panel import QuizPanel

        db = Database(tmp_path / "direct_test7.db")
        loader = ContentLoader(quiz_content)
        try:
            db.upsert_book("test_book", "Test Book", "/path", 100, 5)
            panel = QuizPanel(db, loader)
            qtbot.addWidget(panel)
            panel.show()
            panel.load_quiz("test_book", 1)

            # Answer all questions
            buttons = panel._button_group.buttons()
            buttons[1].setChecked(True)
            panel._check_answer()

            panel._next_question()
            panel._fill_input.setText("spaces")
            panel._check_answer()

            panel._next_question()
            buttons = panel._button_group.buttons()
            buttons[1].setChecked(True)
            panel._check_answer()

            # Retry should be visible now
            assert panel._retry_btn.isVisible()

            # Retry
            panel._retry_quiz()
            assert panel._current_index == 0
            assert not panel._retry_btn.isVisible()

            # Progress should be cleared
            assert db.get_quiz_answer("tb_q01") is None
            assert db.get_quiz_answer("tb_q02") is None
            assert db.get_quiz_answer("tb_q03") is None
        finally:
            db.close()

    def test_theme_change(self, qtbot, tmp_path: Path, quiz_content: Path) -> None:
        """Theme change doesn't crash."""
        from pylearn.core.content_loader import ContentLoader
        from pylearn.core.database import Database
        from pylearn.ui.quiz_panel import QuizPanel

        db = Database(tmp_path / "direct_test8.db")
        loader = ContentLoader(quiz_content)
        try:
            panel = QuizPanel(db, loader)
            qtbot.addWidget(panel)
            panel.load_quiz("test_book", 1)

            for theme in ("light", "dark", "sepia"):
                panel.set_theme(theme)
                assert panel._theme == theme
        finally:
            db.close()


class TestQuizThemeIntegration:
    """Theme switching applies to quiz panel via MainWindow."""

    @pytest.mark.parametrize("theme", ["light", "dark", "sepia"])
    def test_theme_change_with_quiz(self, isolated_main_window, theme: str) -> None:
        window = isolated_main_window
        window._on_theme_changed(theme)
        assert window._quiz_panel._theme == theme
