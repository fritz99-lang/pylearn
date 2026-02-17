# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Integration tests: MainWindow menu action handlers smoke test.

Verifies that every menu action handler in MainWindow can be called
without raising exceptions. This catches bugs like missing imports
or incorrect widget references that would otherwise cause silent crashes
behind the @safe_slot decorator.

Testing approach:
- Create a MainWindow instance with configs/database redirected to tmp_path
  so tests are isolated and do not touch real user data.
- Call each handler method directly (no actual menu click needed).
- For handlers that open modal dialogs (QDialog.exec / QMessageBox.*),
  monkeypatch those calls to no-op so they return immediately.
- The key assertion: no exception raised.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from pylearn.core.database import Database


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def isolated_main_window(qtbot, tmp_path, monkeypatch):
    """Create a MainWindow whose configs and database point at tmp_path.

    This prevents the test from reading/writing the real user config and
    keeps each test run fully isolated.
    """
    # Redirect config paths to temp directory so MainWindow.__init__ does not
    # load the real user configs or touch the real database.
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    cache_dir = data_dir / "cache"
    cache_dir.mkdir()

    monkeypatch.setattr("pylearn.core.constants.CONFIG_DIR", config_dir)
    monkeypatch.setattr("pylearn.core.constants.DATA_DIR", data_dir)
    monkeypatch.setattr("pylearn.core.constants.CACHE_DIR", cache_dir)
    monkeypatch.setattr("pylearn.core.constants.DB_PATH", data_dir / "test.db")
    monkeypatch.setattr("pylearn.core.constants.APP_CONFIG_PATH", config_dir / "app_config.json")
    monkeypatch.setattr("pylearn.core.constants.BOOKS_CONFIG_PATH", config_dir / "books.json")
    monkeypatch.setattr("pylearn.core.constants.EDITOR_CONFIG_PATH", config_dir / "editor_config.json")

    # Also patch the module-level references that AppConfig/BooksConfig/EditorConfig
    # already imported at the top of config.py.
    monkeypatch.setattr("pylearn.core.config.APP_CONFIG_PATH", config_dir / "app_config.json")
    monkeypatch.setattr("pylearn.core.config.BOOKS_CONFIG_PATH", config_dir / "books.json")
    monkeypatch.setattr("pylearn.core.config.EDITOR_CONFIG_PATH", config_dir / "editor_config.json")

    from pylearn.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)

    yield window

    # Cleanup: kill any lingering subprocess so the test can tear down cleanly.
    window._session.reset()


# ---------------------------------------------------------------------------
# Helpers: suppress modal dialogs
# ---------------------------------------------------------------------------

def _noop_exec(self):
    """Replacement for QDialog.exec / QMessageBox.exec — returns immediately."""
    return 0


def _noop_messagebox(*args, **kwargs):
    """No-op replacement for static QMessageBox methods (information, warning, etc.)."""
    return None


def _noop_question(*args, **kwargs):
    """Replacement for QMessageBox.question — returns StandardButton.No."""
    from PyQt6.QtWidgets import QMessageBox
    return QMessageBox.StandardButton.No


# ---------------------------------------------------------------------------
# Tests: handlers that early-return when no book is loaded
# ---------------------------------------------------------------------------

class TestNoBookLoadedHandlers:
    """Handlers that should return early (silently) when no book is loaded."""

    def test_add_bookmark_no_book(self, isolated_main_window) -> None:
        """_add_bookmark returns early when current_book is None."""
        window = isolated_main_window
        assert window._book.current_book is None
        # Should not raise — just returns early.
        window._add_bookmark()

    def test_add_note_no_book(self, isolated_main_window) -> None:
        """_add_note returns early when current_book is None."""
        window = isolated_main_window
        assert window._book.current_book is None
        window._add_note()

    @patch("pylearn.ui.main_window.QMessageBox.information", _noop_messagebox)
    def test_show_exercises_no_book(self, isolated_main_window) -> None:
        """_show_exercises shows 'No Book' message when no book is loaded."""
        window = isolated_main_window
        assert window._book.current_book is None
        window._show_exercises()

    @patch("pylearn.ui.main_window.QMessageBox.information", _noop_messagebox)
    def test_parse_current_book_no_selection(self, isolated_main_window) -> None:
        """_parse_current_book shows info message when no book is selected."""
        window = isolated_main_window
        window._parse_current_book()

    def test_reparse_book_no_selection(self, isolated_main_window) -> None:
        """_reparse_book returns early when no book is selected."""
        window = isolated_main_window
        window._reparse_book()


# ---------------------------------------------------------------------------
# Tests: dialog-opening handlers (dialogs patched to no-op)
# ---------------------------------------------------------------------------

class TestDialogHandlers:
    """Handlers that open modal dialogs — dialogs are patched to return immediately."""

    @patch("pylearn.ui.main_window.BookmarkDialog.exec", _noop_exec)
    def test_show_bookmarks_empty_db(self, isolated_main_window) -> None:
        """_show_bookmarks opens dialog with empty database (no crash)."""
        window = isolated_main_window
        window._show_bookmarks()

    @patch("pylearn.ui.main_window.NotesDialog.exec", _noop_exec)
    def test_show_notes_empty_db(self, isolated_main_window) -> None:
        """_show_notes opens dialog with empty database (no crash)."""
        window = isolated_main_window
        window._show_notes()

    @patch("pylearn.ui.main_window.ProgressDialog.exec", _noop_exec)
    def test_show_progress_empty_db(self, isolated_main_window) -> None:
        """_show_progress opens dialog with empty database (no crash)."""
        window = isolated_main_window
        window._show_progress()

    @patch("pylearn.ui.main_window.SearchDialog.exec", _noop_exec)
    def test_show_search_empty_books(self, isolated_main_window) -> None:
        """_show_search opens dialog with empty books list (no crash)."""
        window = isolated_main_window
        window._show_search()

    @patch("pylearn.ui.main_window.QMessageBox.information", _noop_messagebox)
    def test_show_shortcuts(self, isolated_main_window) -> None:
        """_show_shortcuts shows QMessageBox (patched to no-op)."""
        window = isolated_main_window
        window._show_shortcuts()

    @patch("pylearn.ui.main_window.QMessageBox.about", _noop_messagebox)
    def test_show_about(self, isolated_main_window) -> None:
        """_show_about shows QMessageBox.about (patched to no-op)."""
        window = isolated_main_window
        window._show_about()


# ---------------------------------------------------------------------------
# Tests: view / focus handlers (no dialogs, just widget manipulation)
# ---------------------------------------------------------------------------

class TestViewHandlers:
    """Handlers that toggle visibility, change focus, or adjust font size."""

    def test_toggle_toc_hides_and_shows(self, isolated_main_window) -> None:
        """_toggle_toc toggles the TOC panel visibility."""
        window = isolated_main_window
        was_visible = window._toc.isVisible()
        window._toggle_toc()
        assert window._toc.isVisible() != was_visible
        window._toggle_toc()
        assert window._toc.isVisible() == was_visible

    def test_increase_font(self, isolated_main_window) -> None:
        """_increase_font increments reader_font_size by 1 (capped at 30)."""
        window = isolated_main_window
        before = window._app_config.reader_font_size
        window._increase_font()
        after = window._app_config.reader_font_size
        assert after == min(before + 1, 30)

    def test_decrease_font(self, isolated_main_window) -> None:
        """_decrease_font decrements reader_font_size by 1 (floored at 6)."""
        window = isolated_main_window
        before = window._app_config.reader_font_size
        window._decrease_font()
        after = window._app_config.reader_font_size
        assert after == max(before - 1, 6)

    def test_increase_font_caps_at_30(self, isolated_main_window) -> None:
        """Repeated _increase_font does not exceed 30."""
        window = isolated_main_window
        window._app_config.reader_font_size = 29
        window._increase_font()
        assert window._app_config.reader_font_size == 30
        window._increase_font()
        assert window._app_config.reader_font_size == 30

    def test_decrease_font_floors_at_6(self, isolated_main_window) -> None:
        """Repeated _decrease_font does not go below 6."""
        window = isolated_main_window
        window._app_config.reader_font_size = 7
        window._decrease_font()
        assert window._app_config.reader_font_size == 6
        window._decrease_font()
        assert window._app_config.reader_font_size == 6

    def test_focus_toc(self, isolated_main_window) -> None:
        """_focus_toc makes the TOC visible and gives it focus."""
        window = isolated_main_window
        window._toc.hide()
        window._focus_toc()
        assert window._toc.isVisible()

    def test_focus_reader(self, isolated_main_window) -> None:
        """_focus_reader does not crash."""
        window = isolated_main_window
        window._focus_reader()

    def test_focus_editor(self, isolated_main_window) -> None:
        """_focus_editor does not crash."""
        window = isolated_main_window
        window._focus_editor()

    def test_find_in_chapter(self, isolated_main_window) -> None:
        """_find_in_chapter shows the inline find bar without crashing."""
        window = isolated_main_window
        window._find_in_chapter()


# ---------------------------------------------------------------------------
# Tests: session / execution handlers
# ---------------------------------------------------------------------------

class TestExecutionHandlers:
    """Handlers related to code execution and session management."""

    def test_stop_code_when_nothing_running(self, isolated_main_window) -> None:
        """_stop_code is safe when no code is running."""
        window = isolated_main_window
        # session.stop() returns False when nothing is running, so this is a no-op.
        window._stop_code()

    def test_reset_session(self, isolated_main_window) -> None:
        """_reset_session clears the session and console."""
        window = isolated_main_window
        window._reset_session()
        assert window._status_state.text() == "Session reset"

    def test_run_code_empty_editor(self, isolated_main_window) -> None:
        """_run_code returns early when the editor is empty."""
        window = isolated_main_window
        # Editor starts empty, so _run_code should bail out.
        window._run_code()


# ---------------------------------------------------------------------------
# Tests: state save / restore
# ---------------------------------------------------------------------------

class TestStatePersistence:
    """_save_state and _restore_state do not crash with default state."""

    def test_save_state(self, isolated_main_window) -> None:
        """_save_state writes config without error."""
        window = isolated_main_window
        window._save_state()

    def test_restore_state(self, isolated_main_window) -> None:
        """_restore_state reads config without error (even when config is empty)."""
        window = isolated_main_window
        # Config files are empty (tmp_path), so this exercises the defaults path.
        window._restore_state()

    def test_save_then_restore(self, isolated_main_window) -> None:
        """Round-trip: save state, then restore it, without error."""
        window = isolated_main_window
        window._save_state()
        window._restore_state()


# ---------------------------------------------------------------------------
# Tests: file operations (dialog patched to cancel)
# ---------------------------------------------------------------------------

class TestFileOperations:
    """Save/load code handlers — file dialogs patched to simulate cancel."""

    @patch("pylearn.ui.main_window.QFileDialog.getSaveFileName", return_value=("", ""))
    def test_save_code_cancelled(self, mock_dialog, isolated_main_window) -> None:
        """_save_code_to_file does nothing when user cancels the dialog."""
        window = isolated_main_window
        window._save_code_to_file()

    @patch("pylearn.ui.main_window.QFileDialog.getOpenFileName", return_value=("", ""))
    def test_load_code_cancelled(self, mock_dialog, isolated_main_window) -> None:
        """_load_code_from_file does nothing when user cancels the dialog."""
        window = isolated_main_window
        window._load_code_from_file()

    @patch("pylearn.ui.main_window.QFileDialog.getSaveFileName")
    def test_save_code_to_file(self, mock_dialog, isolated_main_window, tmp_path) -> None:
        """_save_code_to_file writes editor contents to the chosen path."""
        target = tmp_path / "test_output.py"
        mock_dialog.return_value = (str(target), "Python Files (*.py)")
        window = isolated_main_window
        window._editor.set_code("print('hello')")
        window._save_code_to_file()
        assert target.exists()
        assert "print('hello')" in target.read_text(encoding="utf-8")

    @patch("pylearn.ui.main_window.QFileDialog.getOpenFileName")
    def test_load_code_from_file(self, mock_dialog, isolated_main_window, tmp_path) -> None:
        """_load_code_from_file reads the chosen file into the editor."""
        source = tmp_path / "test_input.py"
        source.write_text("x = 42\n", encoding="utf-8")
        mock_dialog.return_value = (str(source), "Python Files (*.py)")
        window = isolated_main_window
        window._load_code_from_file()
        assert "x = 42" in window._editor.get_code()


# ---------------------------------------------------------------------------
# Tests: theme changes
# ---------------------------------------------------------------------------

class TestThemeHandlers:
    """Theme switching does not crash."""

    @pytest.mark.parametrize("theme", ["light", "dark", "sepia"])
    def test_theme_change(self, isolated_main_window, theme: str) -> None:
        """Switching to each supported theme does not raise."""
        window = isolated_main_window
        window._on_theme_changed(theme)
        assert window._app_config.theme == theme


# ---------------------------------------------------------------------------
# Tests: book controller navigation stubs (no book loaded)
# ---------------------------------------------------------------------------

class TestBookControllerNoBook:
    """BookController navigation methods are safe when no book is loaded."""

    def test_prev_chapter_no_book(self, isolated_main_window) -> None:
        window = isolated_main_window
        window._book.prev_chapter()

    def test_next_chapter_no_book(self, isolated_main_window) -> None:
        window = isolated_main_window
        window._book.next_chapter()

    def test_mark_chapter_complete_no_book(self, isolated_main_window) -> None:
        window = isolated_main_window
        window._book.mark_chapter_complete()


# ---------------------------------------------------------------------------
# Tests: close event
# ---------------------------------------------------------------------------

class TestCloseEvent:
    """closeEvent calls _save_state and cleans up without error."""

    def test_close_event(self, isolated_main_window) -> None:
        """Closing the window does not raise."""
        window = isolated_main_window
        window.close()
