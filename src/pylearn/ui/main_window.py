"""Main application window with splitters, menus, and status bar."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QSplitter, QWidget, QVBoxLayout, QHBoxLayout,
    QMenuBar, QMenu, QStatusBar, QLabel, QApplication, QMessageBox,
    QFileDialog, QProgressDialog,
)
from PyQt6.QtCore import Qt, QThread, QProcess, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence, QCloseEvent

from pylearn.core.config import AppConfig, BooksConfig, EditorConfig
from pylearn.core.constants import (
    APP_NAME, APP_VERSION, READER_SPLITTER_RATIO,
    EDITOR_CONSOLE_RATIO, TOC_WIDTH, STATUS_IN_PROGRESS,
    _FROZEN,
)
from pylearn.core.database import Database
from pylearn.core.models import Book, ContentBlock, BlockType
from pylearn.parser.cache_manager import CacheManager
from pylearn.parser.pdf_parser import PDFParser
from pylearn.parser.content_classifier import ContentClassifier
from pylearn.parser.code_extractor import CodeExtractor
from pylearn.parser.structure_detector import StructureDetector
from pylearn.renderer.html_renderer import HTMLRenderer
from pylearn.executor.sandbox import Sandbox
from pylearn.executor.session import Session
from pylearn.executor.output_handler import OutputHandler
from pylearn.utils.text_utils import strip_repl_prompts, detect_repl_code
from pylearn.ui.reader_panel import ReaderPanel
from pylearn.ui.toc_panel import TOCPanel
from pylearn.ui.editor_panel import EditorPanel
from pylearn.ui.console_panel import ConsolePanel
from pylearn.ui.library_panel import LibraryPanel
from pylearn.ui.toolbar import MainToolBar
from pylearn.ui.external_editor import ExternalEditorManager
from pylearn.ui.styles import get_stylesheet
from pylearn.ui.bookmark_dialog import BookmarkDialog, add_bookmark_dialog
from pylearn.ui.notes_dialog import NotesDialog
from pylearn.ui.progress_dialog import ProgressDialog
from pylearn.ui.search_dialog import SearchDialog
from pylearn.ui.exercise_panel import ExercisePanel

logger = logging.getLogger("pylearn.ui")


class ParseProcess:
    """Run book parsing in a separate process via QProcess.

    QProcess integrates with the Qt event loop natively — no threads needed.
    The UI stays fully responsive while PyMuPDF does heavy work in the child process.
    """

    def __init__(self, parent: QWidget) -> None:
        self._process = QProcess(parent)
        self._process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self._book_id: str = ""
        self._parent = parent

        # Wire QProcess signals
        self._process.readyReadStandardOutput.connect(self._on_output)
        self._process.finished.connect(self._on_finished)
        self._process.errorOccurred.connect(self._on_error)

        # Callbacks (set by MainWindow)
        self.on_progress: callable = lambda msg: None
        self.on_finished: callable = lambda book: None
        self.on_error: callable = lambda msg: None

    def start(self, book_id: str) -> None:
        if self._process.state() != QProcess.ProcessState.NotRunning:
            return
        self._book_id = book_id
        if _FROZEN:
            # Frozen mode: re-invoke the exe itself with --parse flag
            self._process.start(sys.executable, ["--parse", "--book", book_id, "--force"])
        else:
            # Dev mode: run the parse script directly
            script = str(Path(__file__).resolve().parent.parent.parent.parent / "scripts" / "parse_books.py")
            self._process.start(sys.executable, [script, "--book", book_id, "--force"])

    def stop(self) -> None:
        if self._process.state() != QProcess.ProcessState.NotRunning:
            self._process.kill()

    def is_running(self) -> bool:
        return self._process.state() != QProcess.ProcessState.NotRunning

    def _on_output(self) -> None:
        data = self._process.readAllStandardOutput().data().decode("utf-8", errors="replace")
        for line in data.splitlines():
            line = line.strip()
            if line:
                self.on_progress(line)

    def _on_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        if exit_code != 0:
            self.on_error(f"Parsing process exited with code {exit_code}")
            return

        self.on_progress("Loading parsed content...")
        cache = CacheManager()
        book = cache.load(self._book_id)
        if book:
            self.on_finished(book)
        else:
            self.on_error("Parsing completed but cache file not found.")

    def _on_error(self, error: QProcess.ProcessError) -> None:
        self.on_error(f"Process error: {error}")


class ExecuteWorker(QThread):
    """Background thread for code execution."""
    finished = pyqtSignal(object)  # ExecutionResult

    def __init__(self, code: str, session: Session) -> None:
        super().__init__()
        self.code = code
        self.session = session

    def run(self) -> None:
        result = self.session.run(self.code)
        self.finished.emit(result)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()

        # Config
        self._app_config = AppConfig()
        self._books_config = BooksConfig()
        self._editor_config = EditorConfig()

        # Core services
        self._db = Database()
        self._cache = CacheManager()
        self._session = Session(timeout=self._editor_config.execution_timeout)
        self._output = OutputHandler()

        # External editor
        self._external_editor = ExternalEditorManager(self)

        # State
        self._current_book: Book | None = None
        self._current_chapter_num: int = 0
        self._parse_process: ParseProcess | None = None
        self._exec_worker: ExecuteWorker | None = None

        self._setup_ui()
        self._setup_menus()
        self._connect_signals()
        self._restore_state()

    def _setup_ui(self) -> None:
        """Build the main UI layout."""
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Library panel (book selector)
        self._library = LibraryPanel(self._books_config)
        main_layout.addWidget(self._library)

        # Toolbar
        self._toolbar = MainToolBar()
        self.addToolBar(self._toolbar)

        # Main content area
        content_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left side: TOC + Reader
        left_splitter = QSplitter(Qt.Orientation.Horizontal)

        self._toc = TOCPanel()
        self._toc.setMaximumWidth(350)
        left_splitter.addWidget(self._toc)

        self._reader = ReaderPanel()
        left_splitter.addWidget(self._reader)

        left_splitter.setSizes([TOC_WIDTH, 600])
        content_splitter.addWidget(left_splitter)

        # Right side: Editor + Console
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        right_splitter = QSplitter(Qt.Orientation.Vertical)

        self._editor = EditorPanel()
        right_splitter.addWidget(self._editor)

        self._console = ConsolePanel()
        right_splitter.addWidget(self._console)

        right_splitter.setSizes(self._app_config.editor_console_sizes)
        self._right_splitter = right_splitter

        right_layout.addWidget(right_splitter)
        content_splitter.addWidget(right_widget)

        content_splitter.setSizes(self._app_config.splitter_sizes)
        self._content_splitter = content_splitter
        self._left_splitter = left_splitter

        main_layout.addWidget(content_splitter)

        # Status bar
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)

        self._status_book = QLabel("")
        self._status_chapter = QLabel("")
        self._status_progress = QLabel("")
        self._status_state = QLabel("Ready")

        self._status_bar.addWidget(self._status_book, 1)
        self._status_bar.addWidget(self._status_chapter, 1)
        self._status_bar.addWidget(self._status_progress, 1)
        self._status_bar.addPermanentWidget(self._status_state)

        # Show welcome
        self._reader.display_welcome()

    def _add_menu_action(self, menu: QMenu, text: str, slot, shortcut: str | None = None) -> QAction:
        """Helper to add a menu action with optional shortcut (PyQt6-compatible)."""
        action = QAction(text, self)
        action.triggered.connect(slot)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        menu.addAction(action)
        return action

    def _setup_menus(self) -> None:
        """Create the menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")
        self._add_menu_action(file_menu, "Save Code...", self._save_code_to_file, "Ctrl+S")
        self._add_menu_action(file_menu, "Load Code...", self._load_code_from_file, "Ctrl+O")
        file_menu.addSeparator()
        self._add_menu_action(file_menu, "E&xit", self.close, "Alt+F4")

        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        self._add_menu_action(edit_menu, "Add Bookmark...", self._add_bookmark, "Ctrl+B")
        self._add_menu_action(edit_menu, "Add Note...", self._add_note, "Ctrl+N")
        edit_menu.addSeparator()
        self._add_menu_action(edit_menu, "Clear Editor", self._editor.clear)
        self._add_menu_action(edit_menu, "Reset Session", self._reset_session)

        # View menu
        view_menu = menubar.addMenu("&View")
        self._toc_action = self._add_menu_action(view_menu, "Toggle TOC", self._toggle_toc, "Ctrl+T")
        self._add_menu_action(view_menu, "Bookmarks...", self._show_bookmarks)
        self._add_menu_action(view_menu, "Notes...", self._show_notes)
        self._add_menu_action(view_menu, "Exercises...", self._show_exercises)
        view_menu.addSeparator()
        self._add_menu_action(view_menu, "Progress...", self._show_progress)

        # Book menu
        book_menu = menubar.addMenu("&Book")
        self._add_menu_action(book_menu, "Parse Current Book", self._parse_current_book)
        self._add_menu_action(book_menu, "Re-parse (clear cache)", self._reparse_book)
        book_menu.addSeparator()
        self._add_menu_action(book_menu, "Previous Chapter", self._prev_chapter, "Alt+Left")
        self._add_menu_action(book_menu, "Next Chapter", self._next_chapter, "Alt+Right")

        # Run menu
        run_menu = menubar.addMenu("&Run")
        self._add_menu_action(run_menu, "Run Code", self._run_code, "F5")
        self._add_menu_action(run_menu, "Stop", self._stop_code, "Shift+F5")
        run_menu.addSeparator()
        self._add_menu_action(run_menu, "Clear Console", self._console.clear_console)

        # Search menu
        search_menu = menubar.addMenu("&Search")
        self._add_menu_action(search_menu, "Search Books...", self._show_search, "Ctrl+F")

        # Help menu
        help_menu = menubar.addMenu("&Help")
        self._add_menu_action(help_menu, "About", self._show_about)

    def _connect_signals(self) -> None:
        """Wire up all signals between components."""
        # Library
        self._library.book_selected.connect(self._on_book_selected)

        # TOC
        self._toc.chapter_selected.connect(self._navigate_to_chapter)
        self._toc.section_selected.connect(self._navigate_to_section)

        # Reader
        self._reader.code_copy_requested.connect(self._copy_code_block)
        self._reader.code_tryit_requested.connect(self._try_code_block)
        self._reader.visible_heading_changed.connect(self._on_visible_heading_changed)

        # Toolbar
        self._toolbar.run_requested.connect(self._run_code)
        self._toolbar.stop_requested.connect(self._stop_code)
        self._toolbar.clear_console_requested.connect(self._console.clear_console)
        self._toolbar.font_size_changed.connect(self._on_font_size_changed)
        self._toolbar.theme_changed.connect(self._on_theme_changed)
        self._toolbar.external_editor_requested.connect(self._open_external_editor)

        # External editor
        self._external_editor.code_changed.connect(self._editor.set_code)

    def _restore_state(self) -> None:
        """Restore window geometry and last session."""
        cfg = self._app_config

        # Window geometry
        if cfg.window_x is not None and cfg.window_y is not None:
            self.move(cfg.window_x, cfg.window_y)
        self.resize(cfg.window_width, cfg.window_height)
        if cfg.window_maximized:
            self.showMaximized()

        # Theme
        self._on_theme_changed(cfg.theme)
        self._toolbar.set_theme(cfg.theme)

        # Font
        self._toolbar.set_font_size(cfg.reader_font_size)
        self._editor.set_font_size(self._editor_config.font_size)

        # TOC visibility
        if not cfg.toc_visible:
            self._toc.hide()

        # Load last book
        if cfg.last_book_id:
            self._library.select_book(cfg.last_book_id)

    def _save_state(self) -> None:
        """Save window geometry and current session."""
        cfg = self._app_config

        if not self.isMaximized():
            geo = self.geometry()
            cfg.window_x = geo.x()
            cfg.window_y = geo.y()
            cfg.window_width = geo.width()
            cfg.window_height = geo.height()
        cfg.window_maximized = self.isMaximized()

        cfg.splitter_sizes = self._content_splitter.sizes()
        cfg.editor_console_sizes = self._right_splitter.sizes()
        cfg.toc_visible = self._toc.isVisible()

        if self._current_book:
            cfg.last_book_id = self._current_book.book_id
            # Save scroll position
            scroll_pos = self._reader.verticalScrollBar().value()
            self._db.save_last_position(
                self._current_book.book_id, self._current_chapter_num, scroll_pos
            )
            # Update reading progress
            if self._current_chapter_num > 0:
                self._db.update_reading_progress(
                    self._current_book.book_id, self._current_chapter_num,
                    STATUS_IN_PROGRESS, scroll_pos,
                )

        cfg.save()
        self._editor_config.save()

    # --- Book Management ---

    def _on_book_selected(self, book_id: str) -> None:
        """Handle book selection from the library panel."""
        book_info = self._books_config.get_book(book_id)
        if not book_info:
            return

        # Try loading from cache
        book = self._cache.load(book_id)
        if book:
            self._load_book(book)
        else:
            # Check if PDF exists
            if not Path(book_info["pdf_path"]).exists():
                QMessageBox.warning(
                    self, "PDF Not Found",
                    f'PDF not found at: {book_info["pdf_path"]}\n'
                    f'Please update the book path in the library.'
                )
                return

            reply = QMessageBox.question(
                self, "Parse Book",
                f'"{book_info["title"]}" has not been parsed yet.\n'
                f'Parse it now? (This may take a few minutes)',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._start_parse(book_info)

    def _load_book(self, book: Book) -> None:
        """Load a parsed book into the UI."""
        self._current_book = book
        self._status_book.setText(f"Book: {book.title}")

        # Set language directly from book model
        self._current_language = book.language
        self._editor.set_language(book.language)
        self._session.language = book.language
        self._reader.set_language(book.language)

        # Register in database
        self._db.upsert_book(
            book.book_id, book.title, book.pdf_path,
            book.total_pages, len(book.chapters),
        )
        for ch in book.chapters:
            self._db.upsert_chapter(
                book.book_id, ch.chapter_num, ch.title,
                ch.start_page, ch.end_page,
            )

        # Load TOC
        progress_data = {}
        for p in self._db.get_all_progress(book.book_id):
            progress_data[p["chapter_num"]] = p["status"]
        self._toc.load_chapters(book.chapters, progress_data)

        # Update status
        stats = self._db.get_completion_stats(book.book_id)
        self._status_progress.setText(f"{stats['percent']}% complete")

        # Navigate to last position or first chapter
        last_pos = self._db.get_last_position(book.book_id)
        if last_pos:
            self._navigate_to_chapter(last_pos["chapter_num"])
            scroll_pos = last_pos.get("scroll_position", 0)
            if scroll_pos:
                QTimer.singleShot(0, lambda: self._reader.verticalScrollBar().setValue(scroll_pos))
        elif book.chapters:
            self._navigate_to_chapter(book.chapters[0].chapter_num)

    def _parse_current_book(self) -> None:
        """Parse (or re-parse) the currently selected book."""
        book_id = self._library.current_book_id()
        if not book_id:
            QMessageBox.information(self, "No Book", "Please select a book first.")
            return

        book_info = self._books_config.get_book(book_id)
        if book_info:
            self._start_parse(book_info)

    def _reparse_book(self) -> None:
        """Clear cache and re-parse the current book."""
        book_id = self._library.current_book_id()
        if book_id:
            self._cache.invalidate(book_id)
            self._parse_current_book()

    def _start_parse(self, book_info: dict) -> None:
        """Start parsing a book in a separate process via QProcess."""
        if self._parse_process and self._parse_process.is_running():
            QMessageBox.warning(self, "Busy", "A book is already being parsed.")
            return

        self._status_state.setText("Parsing (background process)...")

        self._parse_process = ParseProcess(self)
        self._parse_process.on_progress = lambda msg: self._status_state.setText(msg)
        self._parse_process.on_finished = self._on_parse_finished
        self._parse_process.on_error = self._on_parse_error
        self._parse_process.start(book_info["book_id"])

    def _on_parse_finished(self, book: Book) -> None:
        self._status_state.setText("Ready")
        if book:
            self._load_book(book)
            QMessageBox.information(
                self, "Parse Complete",
                f'"{book.title}" parsed successfully.\n'
                f'{len(book.chapters)} chapters found.',
            )

    def _on_parse_error(self, error_msg: str) -> None:
        self._status_state.setText("Ready")
        QMessageBox.critical(self, "Parse Error", f"Error parsing book:\n{error_msg}")

    # --- Navigation ---

    def _navigate_to_chapter(self, chapter_num: int) -> None:
        """Load and display a chapter."""
        if not self._current_book:
            return

        chapter = None
        for ch in self._current_book.chapters:
            if ch.chapter_num == chapter_num:
                chapter = ch
                break

        if not chapter:
            return

        self._current_chapter_num = chapter_num
        self._reader.display_blocks(chapter.content_blocks)
        self._toc.highlight_chapter(chapter_num)

        # Update status
        total = len(self._current_book.chapters)
        idx = next(
            (i for i, ch in enumerate(self._current_book.chapters)
             if ch.chapter_num == chapter_num), 0
        )
        self._status_chapter.setText(f"Chapter {chapter_num} of {total}")

        # Mark as in progress
        self._db.update_reading_progress(
            self._current_book.book_id, chapter_num, STATUS_IN_PROGRESS
        )
        self._toc.update_chapter_status(chapter_num, STATUS_IN_PROGRESS)

    def _navigate_to_section(self, chapter_num: int, block_index: int) -> None:
        """Navigate to a specific section within a chapter."""
        if self._current_chapter_num != chapter_num:
            self._navigate_to_chapter(chapter_num)

        # Find the block_id for scrolling
        if self._current_book:
            for ch in self._current_book.chapters:
                if ch.chapter_num == chapter_num and block_index < len(ch.content_blocks):
                    block = ch.content_blocks[block_index]
                    if block.block_id:
                        self._reader.scroll_to_block(block.block_id)
                    break

    def _prev_chapter(self) -> None:
        if not self._current_book:
            return
        chapters = self._current_book.chapters
        for i, ch in enumerate(chapters):
            if ch.chapter_num == self._current_chapter_num and i > 0:
                self._navigate_to_chapter(chapters[i - 1].chapter_num)
                return

    def _next_chapter(self) -> None:
        if not self._current_book:
            return
        chapters = self._current_book.chapters
        for i, ch in enumerate(chapters):
            if ch.chapter_num == self._current_chapter_num and i < len(chapters) - 1:
                self._navigate_to_chapter(chapters[i + 1].chapter_num)
                return

    def _on_visible_heading_changed(self, block_index: int) -> None:
        """Sync TOC highlight as the user scrolls through the reader."""
        if self._current_chapter_num > 0:
            self._toc.highlight_section(self._current_chapter_num, block_index)

    # --- External Editor ---

    def _open_external_editor(self) -> None:
        """Open current editor code in the external editor (Notepad++)."""
        if not self._editor_config.external_editor_enabled:
            QMessageBox.information(
                self, "Disabled",
                "External editor is disabled in editor_config.json."
            )
            return

        code = self._editor.get_code()
        language = getattr(self, "_current_language", "python")
        error = self._external_editor.open(
            code, language, self._editor_config.external_editor_path
        )
        if error:
            QMessageBox.warning(self, "External Editor", error)
        else:
            self._status_state.setText("Opened in external editor")

    # --- Code Operations ---

    def _copy_code_block(self, block_id: str) -> None:
        """Copy a code block to clipboard."""
        block = self._reader.get_block(block_id)
        if block:
            clipboard = QApplication.clipboard()
            clipboard.setText(block.text)
            self._status_state.setText("Code copied to clipboard")

    def _try_code_block(self, block_id: str) -> None:
        """Load a code block into the editor."""
        block = self._reader.get_block(block_id)
        if block:
            code = block.text
            # Strip REPL prompts if present
            if detect_repl_code(code):
                code = strip_repl_prompts(code)
            self._editor.append_code(code)
            self._status_state.setText("Code loaded into editor")

    def _run_code(self) -> None:
        """Execute the code in the editor."""
        code = self._editor.get_code().strip()
        if not code:
            return

        self._toolbar.set_running(True)
        self._console.show_running()
        lang = getattr(self, "_current_language", "python")
        if lang == "html":
            self._status_state.setText("Opening in browser...")
        elif lang in ("cpp", "c"):
            self._status_state.setText("Compiling and running...")
        else:
            self._status_state.setText("Running...")

        self._exec_worker = ExecuteWorker(code, self._session)
        self._exec_worker.finished.connect(self._on_execution_finished)
        self._exec_worker.start()

    def _on_execution_finished(self, result) -> None:
        self._toolbar.set_running(False)
        self._status_state.setText("Ready")
        output_html = self._output.format_result(result)
        self._console.append_html(self._output.format_separator())
        self._console.append_html(output_html)

    def _stop_code(self) -> None:
        """Stop the currently running code."""
        if self._session.stop():
            self._toolbar.set_running(False)
            self._status_state.setText("Stopped")
            self._console.append_html(
                self._output.format_status("Execution stopped by user.", "#ffa500")
            )

    def _reset_session(self) -> None:
        """Reset the execution session."""
        self._session.reset()
        self._console.clear_console()
        self._status_state.setText("Session reset")

    # --- File Operations ---

    def _save_code_to_file(self) -> None:
        lang = getattr(self, "_current_language", "python")
        if lang == "html":
            file_filter = "HTML Files (*.html *.htm);;CSS Files (*.css);;All Files (*)"
        elif lang in ("cpp", "c"):
            file_filter = "C++ Files (*.cpp *.cc *.h);;All Files (*)"
        else:
            file_filter = "Python Files (*.py);;All Files (*)"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Code", "", file_filter
        )
        if path:
            Path(path).write_text(self._editor.get_code(), encoding="utf-8")
            self._status_state.setText(f"Saved to {Path(path).name}")

    def _load_code_from_file(self) -> None:
        lang = getattr(self, "_current_language", "python")
        if lang == "html":
            file_filter = "HTML Files (*.html *.htm);;CSS Files (*.css);;All Files (*)"
        elif lang in ("cpp", "c"):
            file_filter = "C++ Files (*.cpp *.cc *.h);;All Files (*)"
        else:
            file_filter = "Python Files (*.py);;All Files (*)"
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Code", "", file_filter
        )
        if path:
            code = Path(path).read_text(encoding="utf-8")
            self._editor.set_code(code)
            self._status_state.setText(f"Loaded {Path(path).name}")

    # --- Bookmarks & Notes ---

    def _add_bookmark(self) -> None:
        if not self._current_book:
            return
        scroll_pos = self._reader.verticalScrollBar().value()
        add_bookmark_dialog(
            self, self._db, self._current_book.book_id,
            self._current_chapter_num, scroll_pos,
        )

    def _show_bookmarks(self) -> None:
        book_id = self._current_book.book_id if self._current_book else None
        dialog = BookmarkDialog(self._db, book_id, self)
        dialog.bookmark_selected.connect(self._goto_bookmark)
        dialog.exec()

    def _goto_bookmark(self, book_id: str, chapter_num: int, scroll_pos: int) -> None:
        if self._current_book and self._current_book.book_id != book_id:
            self._library.select_book(book_id)
        self._navigate_to_chapter(chapter_num)
        self._reader.verticalScrollBar().setValue(scroll_pos)

    def _add_note(self) -> None:
        if not self._current_book:
            return
        dialog = NotesDialog(
            self._db, self._current_book.book_id,
            self._current_chapter_num, self,
        )
        dialog.exec()

    def _show_notes(self) -> None:
        book_id = self._current_book.book_id if self._current_book else None
        dialog = NotesDialog(self._db, book_id, parent=self)
        dialog.exec()

    # --- Exercises ---

    def _show_exercises(self) -> None:
        if not self._current_book:
            QMessageBox.information(self, "No Book", "Please select a book first.")
            return
        # Show exercises in a dialog-like panel
        from PyQt6.QtWidgets import QDialog, QVBoxLayout
        dialog = QDialog(self)
        dialog.setWindowTitle("Exercises")
        dialog.setMinimumSize(500, 500)
        layout = QVBoxLayout(dialog)
        panel = ExercisePanel(self._db, dialog)
        panel.load_exercises(self._current_book.book_id)
        panel.load_code_requested.connect(self._editor.set_code)
        layout.addWidget(panel)
        dialog.exec()

    # --- View ---

    def _toggle_toc(self) -> None:
        self._toc.setVisible(not self._toc.isVisible())

    def _on_font_size_changed(self, size: int) -> None:
        self._reader.set_font_size(size)
        self._editor.set_font_size(size)
        self._app_config.reader_font_size = size
        self._editor_config.font_size = size

    def _on_theme_changed(self, theme_name: str) -> None:
        self.setStyleSheet(get_stylesheet(theme_name))
        self._reader.set_theme(theme_name)
        self._editor.set_theme(theme_name)
        self._console.set_theme(theme_name)
        self._app_config.theme = theme_name

    # --- Search ---

    def _show_search(self) -> None:
        book_ids = [b["book_id"] for b in self._books_config.books]
        dialog = SearchDialog(self._cache, book_ids, self)
        dialog.navigate_requested.connect(self._search_navigate)
        dialog.exec()

    def _search_navigate(self, book_id: str, chapter_num: int) -> None:
        if self._current_book and self._current_book.book_id != book_id:
            self._library.select_book(book_id)
        self._navigate_to_chapter(chapter_num)

    # --- Progress ---

    def _show_progress(self) -> None:
        dialog = ProgressDialog(self._db, self)
        dialog.exec()

    # --- About ---

    def _show_about(self) -> None:
        QMessageBox.about(
            self, f"About {APP_NAME}",
            f"<h2>{APP_NAME} v{APP_VERSION}</h2>"
            f"<p>Interactive Python Learning Desktop App</p>"
            f"<p>Read O'Reilly Python books with an integrated "
            f"code editor and execution console.</p>"
            f"<p>Built with PyQt6, QScintilla, PyMuPDF, and Pygments.</p>"
        )

    # --- Lifecycle ---

    def closeEvent(self, event: QCloseEvent) -> None:
        """Save state on close."""
        self._save_state()
        # Clean up external editor temp files
        self._external_editor.cleanup()
        # Stop any running processes
        self._session.stop()
        if self._parse_process and self._parse_process.is_running():
            self._parse_process.stop()
        if self._exec_worker and self._exec_worker.isRunning():
            self._exec_worker.quit()
            self._exec_worker.wait(3000)
        super().closeEvent(event)
