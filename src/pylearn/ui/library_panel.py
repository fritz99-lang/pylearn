"""Book library panel: book selector and manager."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton,
    QLabel, QFileDialog, QInputDialog, QMessageBox,
)
from PyQt6.QtCore import pyqtSignal

from pylearn.core.config import BooksConfig


class LibraryPanel(QWidget):
    """Book selector with add/remove capabilities."""

    book_selected = pyqtSignal(str)  # book_id

    def __init__(self, books_config: BooksConfig, parent=None) -> None:
        super().__init__(parent)
        self._config = books_config

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        layout.addWidget(QLabel("Book:"))

        self._combo = QComboBox()
        self._combo.setMinimumWidth(250)
        self._combo.currentIndexChanged.connect(self._on_selection_changed)
        layout.addWidget(self._combo, stretch=1)

        self._add_btn = QPushButton("Add Book...")
        self._add_btn.clicked.connect(self._add_book)
        layout.addWidget(self._add_btn)

        self._refresh_combo()

    def _refresh_combo(self) -> None:
        """Reload the book list from config."""
        self._combo.blockSignals(True)
        self._combo.clear()
        for book in self._config.books:
            self._combo.addItem(book["title"], book["book_id"])
        self._combo.blockSignals(False)

    def select_book(self, book_id: str) -> None:
        """Select a book by ID."""
        for i in range(self._combo.count()):
            if self._combo.itemData(i) == book_id:
                self._combo.setCurrentIndex(i)
                return

    def current_book_id(self) -> str | None:
        """Get the currently selected book ID."""
        idx = self._combo.currentIndex()
        if idx >= 0:
            return self._combo.itemData(idx)
        return None

    def _on_selection_changed(self, index: int) -> None:
        if index >= 0:
            book_id = self._combo.itemData(index)
            if book_id:
                self.book_selected.emit(book_id)

    def _add_book(self) -> None:
        """Add a new book via file dialog."""
        pdf_path, _ = QFileDialog.getOpenFileName(
            self, "Select PDF Book", "", "PDF Files (*.pdf)"
        )
        if not pdf_path:
            return

        # Ask for book title
        filename = Path(pdf_path).stem
        title, ok = QInputDialog.getText(
            self, "Book Title", "Enter the book title:", text=filename
        )
        if not ok or not title:
            return

        # Ask for profile
        profiles = ["learning_python", "python_cookbook", "programming_python", "generic"]
        profile, ok = QInputDialog.getItem(
            self, "Book Profile", "Select a parsing profile:", profiles, 0, False
        )
        if not ok:
            return

        # Generate book_id from title
        book_id = title.lower().replace(" ", "_").replace(",", "").replace(".", "")[:30]

        self._config.add_book(book_id, title, pdf_path, profile)
        self._config.save()
        self._refresh_combo()
        self.select_book(book_id)

        QMessageBox.information(
            self, "Book Added",
            f'"{title}" has been added to the library.\n'
            f'It needs to be parsed before reading. Use Book > Parse Current Book.'
        )
