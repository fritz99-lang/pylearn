"""Book state management extracted from MainWindow.

Owns book loading, parsing, navigation, and progress tracking.
Emits signals so MainWindow can update UI without coupling logic to widgets.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from pylearn.core.constants import STATUS_IN_PROGRESS, STATUS_COMPLETED
from pylearn.core.models import Book, ContentBlock
from pylearn.core.config import BooksConfig
from pylearn.core.database import Database
from pylearn.parser.cache_manager import CacheManager

logger = logging.getLogger("pylearn.ui.book_controller")


class BookController(QObject):
    """Manages book state, navigation, and progress — no direct UI references."""

    # Signals
    book_loaded = pyqtSignal(object)          # Book
    chapter_changed = pyqtSignal(int, list)   # chapter_num, content_blocks
    language_changed = pyqtSignal(str)         # language name
    status_message = pyqtSignal(str)           # status bar text
    error_message = pyqtSignal(str, str)       # (title, message) for QMessageBox
    progress_updated = pyqtSignal(str)         # e.g. "42% complete"
    chapter_status_changed = pyqtSignal(int, str)  # chapter_num, status
    parse_requested = pyqtSignal(dict)         # book_info dict
    scroll_to_position = pyqtSignal(int)       # scroll position (deferred)

    def __init__(
        self,
        db: Database,
        cache: CacheManager,
        books_config: BooksConfig,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._db = db
        self._cache = cache
        self._books_config = books_config

        self._current_book: Book | None = None
        self._current_chapter_num: int = 0
        self._current_language: str = "python"

    # --- Properties ---

    @property
    def current_book(self) -> Book | None:
        return self._current_book

    @property
    def current_chapter_num(self) -> int:
        return self._current_chapter_num

    @property
    def current_language(self) -> str:
        return self._current_language

    @property
    def image_dir(self) -> str:
        """Image directory for the current book."""
        if self._current_book:
            return str(self._cache.image_dir(self._current_book.book_id))
        return ""

    # --- Book Loading ---

    def on_book_selected(self, book_id: str) -> None:
        """Handle book selection — load from cache or request parse."""
        book_info = self._books_config.get_book(book_id)
        if not book_info:
            return

        book = self._cache.load(book_id)
        if book:
            self.load_book(book)
        else:
            if not Path(book_info["pdf_path"]).exists():
                self.status_message.emit(
                    f"PDF not found: {book_info['pdf_path']}"
                )
                self.error_message.emit(
                    "PDF Not Found",
                    f"Could not find the PDF file:\n{book_info['pdf_path']}\n\n"
                    "Please check the file path in Book > Manage Library.",
                )
                return
            self.parse_requested.emit(book_info)

    def load_book(self, book: Book) -> None:
        """Load a parsed book — update state and emit signals."""
        self._current_book = book
        self._current_language = book.language

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

        self.language_changed.emit(book.language)
        self.book_loaded.emit(book)

        # Emit progress
        stats = self._db.get_completion_stats(book.book_id)
        self.progress_updated.emit(f"{stats['percent']}% complete")

        # Navigate to last position or first chapter
        last_pos = self._db.get_last_position(book.book_id)
        if last_pos:
            self.navigate_to_chapter(last_pos["chapter_num"])
            scroll_pos = last_pos.get("scroll_position", 0)
            if scroll_pos:
                self.scroll_to_position.emit(scroll_pos)
        elif book.chapters:
            self.navigate_to_chapter(book.chapters[0].chapter_num)

    # --- Navigation ---

    def navigate_to_chapter(self, chapter_num: int) -> None:
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
        self.chapter_changed.emit(chapter_num, chapter.content_blocks)

        total = len(self._current_book.chapters)
        self.status_message.emit(f"Chapter {chapter_num} of {total}")

        # Mark as in progress
        self._db.update_reading_progress(
            self._current_book.book_id, chapter_num, STATUS_IN_PROGRESS
        )
        self.chapter_status_changed.emit(chapter_num, STATUS_IN_PROGRESS)

    def navigate_to_section(self, chapter_num: int, block_index: int) -> str | None:
        """Navigate to a section; returns block_id to scroll to, or None."""
        if self._current_chapter_num != chapter_num:
            self.navigate_to_chapter(chapter_num)

        if self._current_book:
            for ch in self._current_book.chapters:
                if ch.chapter_num == chapter_num and block_index < len(ch.content_blocks):
                    block = ch.content_blocks[block_index]
                    return block.block_id
        return None

    def prev_chapter(self) -> None:
        if not self._current_book:
            return
        chapters = self._current_book.chapters
        for i, ch in enumerate(chapters):
            if ch.chapter_num == self._current_chapter_num and i > 0:
                self.navigate_to_chapter(chapters[i - 1].chapter_num)
                return

    def next_chapter(self) -> None:
        if not self._current_book:
            return
        chapters = self._current_book.chapters
        for i, ch in enumerate(chapters):
            if ch.chapter_num == self._current_chapter_num and i < len(chapters) - 1:
                self.navigate_to_chapter(chapters[i + 1].chapter_num)
                return

    def mark_chapter_complete(self) -> None:
        """Mark the current chapter as completed."""
        if not self._current_book or self._current_chapter_num == 0:
            return
        self._db.update_reading_progress(
            self._current_book.book_id, self._current_chapter_num, STATUS_COMPLETED,
        )
        self.chapter_status_changed.emit(self._current_chapter_num, STATUS_COMPLETED)

        stats = self._db.get_completion_stats(self._current_book.book_id)
        self.progress_updated.emit(f"{stats['percent']}% complete")
        self.status_message.emit(f"Chapter {self._current_chapter_num} marked complete")

    # --- Progress Helpers ---

    def get_progress_data(self) -> dict[int, str]:
        """Get chapter progress for the current book (chapter_num -> status)."""
        if not self._current_book:
            return {}
        result = {}
        for p in self._db.get_all_progress(self._current_book.book_id):
            result[p["chapter_num"]] = p["status"]
        return result

    def save_position(self, scroll_pos: int) -> None:
        """Save current reading position to the database."""
        if self._current_book and self._current_chapter_num > 0:
            self._db.save_last_position(
                self._current_book.book_id, self._current_chapter_num, scroll_pos
            )
            self._db.update_reading_progress(
                self._current_book.book_id, self._current_chapter_num,
                STATUS_IN_PROGRESS, scroll_pos,
            )

    def current_chapter_title(self) -> str:
        """Get the title of the current chapter."""
        if not self._current_book:
            return ""
        for ch in self._current_book.chapters:
            if ch.chapter_num == self._current_chapter_num:
                return ch.title
        return ""
