# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Full-text search dialog with block-level navigation."""

from __future__ import annotations

import logging

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QTreeWidget, QTreeWidgetItem, QLabel,
    QProgressBar, QComboBox,
)
from PyQt6.QtCore import pyqtSignal, Qt, QThread
from PyQt6.QtGui import QFont

from pylearn.core.models import BlockType, Book
from pylearn.parser.cache_manager import CacheManager
from pylearn.ui.theme_registry import get_palette

logger = logging.getLogger("pylearn.ui")


def _block_type_label(block_type: BlockType) -> str:
    """Return a human-readable label for a block type."""
    labels: dict[BlockType, str] = {
        BlockType.HEADING1: "Heading",
        BlockType.HEADING2: "Heading",
        BlockType.HEADING3: "Heading",
        BlockType.BODY: "Body",
        BlockType.CODE: "Code",
        BlockType.CODE_REPL: "Code",
        BlockType.NOTE: "Note",
        BlockType.WARNING: "Warning",
        BlockType.TIP: "Tip",
        BlockType.EXERCISE: "Exercise",
        BlockType.EXERCISE_ANSWER: "Exercise",
        BlockType.TABLE: "Table",
        BlockType.LIST_ITEM: "List",
        BlockType.FIGURE: "Figure",
        BlockType.FIGURE_CAPTION: "Figure",
        BlockType.PAGE_HEADER: "Header",
        BlockType.PAGE_FOOTER: "Footer",
    }
    return labels.get(block_type, "Body")


class SearchWorker(QThread):
    """Background thread for searching book content."""
    # book_id, chapter_num, title, snippet, block_id, block_type_label
    result_found = pyqtSignal(str, int, str, str, str, str)
    finished = pyqtSignal(int)  # total results

    def __init__(self, query: str, books: list[Book]) -> None:
        super().__init__()
        self.query = query.lower()
        self.books = books
        self._stop = False

    def run(self) -> None:
        total = 0
        try:
            for book in self.books:
                if self._stop:
                    break

                book_id = book.book_id
                for chapter in book.chapters:
                    if self._stop:
                        break
                    for block in chapter.content_blocks:
                        if self.query in block.text.lower():
                            # Create a snippet around the match
                            idx = block.text.lower().index(self.query)
                            start = max(0, idx - 40)
                            end = min(len(block.text), idx + len(self.query) + 40)
                            snippet = block.text[start:end]
                            if start > 0:
                                snippet = "..." + snippet
                            if end < len(block.text):
                                snippet = snippet + "..."

                            self.result_found.emit(
                                book_id, chapter.chapter_num,
                                chapter.title, snippet,
                                block.block_id,
                                _block_type_label(block.block_type),
                            )
                            total += 1
                            if total >= 200:  # cap results
                                return
        except Exception:
            logger.exception("SearchWorker encountered an error")
        finally:
            self.finished.emit(total)

    def stop(self) -> None:
        self._stop = True


class SearchDialog(QDialog):
    """Dialog for searching across book content with block-level navigation."""

    navigate_requested = pyqtSignal(str, int, str)  # book_id, chapter_num, block_id

    def __init__(self, cache_manager: CacheManager, book_ids: list[str],
                 current_book_id: str | None = None,
                 theme_name: str = "light",
                 parent: object = None) -> None:
        super().__init__(parent)
        self._cache = cache_manager
        self._book_ids = book_ids
        self._current_book_id = current_book_id
        self._theme_name = theme_name
        self._worker: SearchWorker | None = None
        self._query: str = ""

        # Pre-load all books once instead of re-parsing JSON per search
        self._books: list[Book] = []
        for bid in book_ids:
            book = cache_manager.load(bid)
            if book:
                self._books.append(book)

        # Track chapter parent items for grouping
        self._chapter_items: dict[str, QTreeWidgetItem] = {}

        self.setWindowTitle("Search Books")
        self.setMinimumSize(700, 550)

        layout = QVBoxLayout(self)

        # Search input row
        search_layout = QHBoxLayout()

        self._scope = QComboBox()
        if current_book_id:
            self._scope.addItems(["Current Book", "All Books"])
        else:
            self._scope.addItems(["All Books"])
        search_layout.addWidget(self._scope)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Search book content...")
        self._input.returnPressed.connect(self._search)
        search_layout.addWidget(self._input)

        self._search_btn = QPushButton("Search")
        self._search_btn.clicked.connect(self._search)
        search_layout.addWidget(self._search_btn)

        layout.addLayout(search_layout)

        # Progress
        self._progress = QProgressBar()
        self._progress.setMaximum(0)
        self._progress.hide()
        layout.addWidget(self._progress)

        # Results
        self._status = QLabel("")
        layout.addWidget(self._status)

        self._results = QTreeWidget()
        self._results.setHeaderLabels(["Location", "Type", "Match"])
        self._results.setColumnWidth(0, 220)
        self._results.setColumnWidth(1, 60)
        self._results.itemDoubleClicked.connect(self._on_result_clicked)
        layout.addWidget(self._results)

        # Close
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        close_layout.addWidget(close_btn)
        layout.addLayout(close_layout)

        self._input.setFocus()

    def _get_scoped_books(self) -> list[Book]:
        """Return books filtered by the current scope selection."""
        if self._scope.currentText() == "Current Book" and self._current_book_id:
            return [b for b in self._books if b.book_id == self._current_book_id]
        return list(self._books)

    def _search(self) -> None:
        query = self._input.text().strip()
        if not query or len(query) < 2:
            return

        self._query = query
        self._results.clear()
        self._chapter_items.clear()
        self._progress.show()
        self._status.setText("Searching...")

        if self._worker:
            self._worker.stop()
            self._worker.wait()

        scoped_books = self._get_scoped_books()
        self._worker = SearchWorker(query, scoped_books)
        self._worker.result_found.connect(self._add_result)
        self._worker.finished.connect(self._search_done)
        self._worker.start()

    def _add_result(self, book_id: str, chapter_num: int,
                    title: str, snippet: str,
                    block_id: str, block_type: str) -> None:
        # Create or reuse a chapter-level parent item
        chapter_key = f"{book_id}:{chapter_num}"
        if chapter_key not in self._chapter_items:
            parent = QTreeWidgetItem(self._results)
            chapter_label = f"[{book_id}] Ch {chapter_num}: {title}"
            parent.setText(0, chapter_label)
            bold_font = parent.font(0)
            bold_font.setBold(True)
            parent.setFont(0, bold_font)
            # No UserRole data on chapter items — they aren't navigable
            parent.setExpanded(True)
            self._chapter_items[chapter_key] = parent

        parent_item = self._chapter_items[chapter_key]

        # Create the child match item
        child = QTreeWidgetItem(parent_item)
        child.setText(1, block_type)
        child.setData(0, Qt.ItemDataRole.UserRole, (book_id, chapter_num, block_id))

        # Highlighted snippet as widget
        palette = get_palette(self._theme_name)
        highlighted = self._highlight_snippet(snippet, self._query, palette.accent)
        label = QLabel(highlighted)
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setWordWrap(True)
        self._results.setItemWidget(child, 2, label)

    @staticmethod
    def _highlight_snippet(snippet: str, query: str, accent_color: str) -> str:
        """Return HTML with the matched term bold+colored."""
        import html as html_mod
        escaped = html_mod.escape(snippet)
        query_lower = query.lower()

        # Find match position in escaped text (case-insensitive)
        lower_escaped = escaped.lower()
        idx = lower_escaped.find(query_lower)
        if idx == -1:
            return escaped

        matched_text = escaped[idx:idx + len(query)]
        highlighted = (
            escaped[:idx]
            + f'<b style="color:{accent_color}">{matched_text}</b>'
            + escaped[idx + len(query):]
        )
        return highlighted

    def _search_done(self, total: int) -> None:
        self._progress.hide()
        self._status.setText(f"Found {total} results")

    def _on_result_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data:
            self.navigate_requested.emit(data[0], data[1], data[2])
            self.close()

    def closeEvent(self, event: object) -> None:
        if self._worker:
            self._worker.stop()
            self._worker.wait()
        super().closeEvent(event)
