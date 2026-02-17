# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Full-text search dialog across book content."""

from __future__ import annotations

import logging

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QTreeWidget, QTreeWidgetItem, QLabel,
    QProgressBar,
)
from PyQt6.QtCore import pyqtSignal, Qt, QThread

from pylearn.core.models import Book
from pylearn.parser.cache_manager import CacheManager

logger = logging.getLogger("pylearn.ui")


class SearchWorker(QThread):
    """Background thread for searching book content."""
    result_found = pyqtSignal(str, int, str, str)  # book_id, chapter_num, title, snippet
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
                                chapter.title, snippet
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
    """Dialog for searching across all book content."""

    navigate_requested = pyqtSignal(str, int)  # book_id, chapter_num

    def __init__(self, cache_manager: CacheManager, book_ids: list[str],
                 parent=None) -> None:
        super().__init__(parent)
        self._cache = cache_manager
        self._book_ids = book_ids
        self._worker: SearchWorker | None = None

        # Pre-load all books once instead of re-parsing JSON per search
        self._books: list[Book] = []
        for bid in book_ids:
            book = cache_manager.load(bid)
            if book:
                self._books.append(book)

        self.setWindowTitle("Search Books")
        self.setMinimumSize(600, 500)

        layout = QVBoxLayout(self)

        # Search input
        search_layout = QHBoxLayout()
        self._input = QLineEdit()
        self._input.setPlaceholderText("Search across all books...")
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
        self._results.setHeaderLabels(["Chapter", "Match"])
        self._results.setColumnWidth(0, 200)
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

    def _search(self) -> None:
        query = self._input.text().strip()
        if not query or len(query) < 2:
            return

        self._results.clear()
        self._progress.show()
        self._status.setText("Searching...")

        if self._worker:
            self._worker.stop()
            self._worker.wait()

        self._worker = SearchWorker(query, self._books)
        self._worker.result_found.connect(self._add_result)
        self._worker.finished.connect(self._search_done)
        self._worker.start()

    def _add_result(self, book_id: str, chapter_num: int,
                    title: str, snippet: str) -> None:
        item = QTreeWidgetItem(self._results)
        item.setText(0, f"[{book_id}] Ch {chapter_num}")
        item.setText(1, snippet)
        item.setData(0, Qt.ItemDataRole.UserRole, (book_id, chapter_num))

    def _search_done(self, total: int) -> None:
        self._progress.hide()
        self._status.setText(f"Found {total} results")

    def _on_result_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data:
            self.navigate_requested.emit(data[0], data[1])
            self.close()

    def closeEvent(self, event) -> None:
        if self._worker:
            self._worker.stop()
            self._worker.wait()
        super().closeEvent(event)
