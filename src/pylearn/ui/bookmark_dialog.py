# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Bookmark manager dialog."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QInputDialog, QMessageBox,
)
from PyQt6.QtCore import pyqtSignal, Qt

from pylearn.core.database import Database


class BookmarkDialog(QDialog):
    """Dialog for managing bookmarks."""

    bookmark_selected = pyqtSignal(str, int, int)  # book_id, chapter_num, scroll_pos

    def __init__(self, database: Database, book_id: str | None = None,
                 parent=None) -> None:
        super().__init__(parent)
        self._db = database
        self._book_id = book_id

        self.setWindowTitle("Bookmarks")
        self.setMinimumSize(500, 400)

        layout = QVBoxLayout(self)

        header = QLabel("Your Bookmarks")
        header.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 8px;")
        layout.addWidget(header)

        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Label", "Book", "Chapter"])
        self._tree.setColumnWidth(0, 200)
        self._tree.setColumnWidth(1, 150)
        self._tree.itemDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self._tree)

        btn_layout = QHBoxLayout()

        self._go_btn = QPushButton("Go To")
        self._go_btn.clicked.connect(self._go_to_bookmark)
        btn_layout.addWidget(self._go_btn)

        self._delete_btn = QPushButton("Delete")
        self._delete_btn.clicked.connect(self._delete_bookmark)
        btn_layout.addWidget(self._delete_btn)

        btn_layout.addStretch()

        self._close_btn = QPushButton("Close")
        self._close_btn.clicked.connect(self.close)
        btn_layout.addWidget(self._close_btn)

        layout.addLayout(btn_layout)

        self._load_bookmarks()

    def _load_bookmarks(self) -> None:
        self._tree.clear()
        bookmarks = self._db.get_bookmarks(self._book_id)

        for bm in bookmarks:
            item = QTreeWidgetItem(self._tree)
            item.setText(0, bm["label"])
            item.setText(1, bm["book_id"])
            item.setText(2, f"Chapter {bm['chapter_num']}")
            item.setData(0, Qt.ItemDataRole.UserRole, bm)

    def _on_double_click(self, item: QTreeWidgetItem, column: int) -> None:
        self._go_to_bookmark()

    def _go_to_bookmark(self) -> None:
        item = self._tree.currentItem()
        if not item:
            return
        bm = item.data(0, Qt.ItemDataRole.UserRole)
        self.bookmark_selected.emit(bm["book_id"], bm["chapter_num"], bm["scroll_position"])
        self.close()

    def _delete_bookmark(self) -> None:
        item = self._tree.currentItem()
        if not item:
            return
        bm = item.data(0, Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(
            self, "Delete Bookmark",
            f'Delete bookmark "{bm["label"]}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._db.delete_bookmark(bm["bookmark_id"])
            self._load_bookmarks()


def add_bookmark_dialog(parent, database: Database, book_id: str,
                        chapter_num: int, scroll_position: int) -> bool:
    """Show a quick dialog to add a bookmark."""
    label, ok = QInputDialog.getText(
        parent, "Add Bookmark", "Bookmark label:"
    )
    if ok and label:
        database.add_bookmark(book_id, chapter_num, scroll_position, label)
        return True
    return False
