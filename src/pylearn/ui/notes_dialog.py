# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Notes manager dialog."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter, QWidget,
    QTreeWidget, QTreeWidgetItem, QTextEdit,
    QPushButton, QLabel, QMessageBox,
)
from PyQt6.QtCore import pyqtSignal, Qt

from pylearn.core.database import Database

import logging
logger = logging.getLogger("pylearn.ui.notes_dialog")


class NotesDialog(QDialog):
    """Dialog for viewing and editing notes."""

    def __init__(self, database: Database, book_id: str | None = None,
                 chapter_num: int | None = None, parent=None,
                 section_title: str = "") -> None:
        super().__init__(parent)
        self._db = database
        self._book_id = book_id
        self._chapter_num = chapter_num
        self._section_title = section_title
        self._current_note_id: int | None = None

        self.setWindowTitle("Notes")
        self.setMinimumSize(700, 500)

        layout = QVBoxLayout(self)

        header = QLabel("Your Notes")
        header.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 8px;")
        layout.addWidget(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Note list
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Section", "Preview"])
        self._tree.setColumnWidth(0, 150)
        self._tree.itemClicked.connect(self._on_note_selected)
        splitter.addWidget(self._tree)

        # Note editor
        editor_widget = QWidget()
        editor_layout = QVBoxLayout(editor_widget)
        editor_layout.setContentsMargins(0, 0, 0, 0)

        self._editor = QTextEdit()
        self._editor.setPlaceholderText("Select a note or create a new one...")
        editor_layout.addWidget(self._editor)

        edit_btns = QHBoxLayout()
        self._save_btn = QPushButton("Save")
        self._save_btn.clicked.connect(self._save_note)
        edit_btns.addWidget(self._save_btn)

        self._new_btn = QPushButton("New Note")
        self._new_btn.clicked.connect(self._new_note)
        edit_btns.addWidget(self._new_btn)

        self._delete_btn = QPushButton("Delete")
        self._delete_btn.clicked.connect(self._delete_note)
        edit_btns.addWidget(self._delete_btn)

        edit_btns.addStretch()
        editor_layout.addLayout(edit_btns)

        splitter.addWidget(editor_widget)
        splitter.setSizes([250, 450])

        layout.addWidget(splitter)

        # Close button
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        close_layout.addWidget(close_btn)
        layout.addLayout(close_layout)

        logger.debug("NotesDialog: constructor done, calling _load_notes")
        self._load_notes()

    def _load_notes(self) -> None:
        self._tree.clear()
        logger.debug("_load_notes: querying db for book=%s chapter=%s",
                      self._book_id, self._chapter_num)
        notes = self._db.get_notes(self._book_id, self._chapter_num)
        logger.debug("_load_notes: got %d notes", len(notes))

        for note in notes:
            item = QTreeWidgetItem(self._tree)
            item.setText(0, note.get("section_title", "General"))
            preview = note["content"][:50].replace("\n", " ")
            item.setText(1, preview)
            item.setData(0, Qt.ItemDataRole.UserRole, note)
        logger.debug("_load_notes: tree populated")

    def _on_note_selected(self, item: QTreeWidgetItem, column: int) -> None:
        note = item.data(0, Qt.ItemDataRole.UserRole)
        if note:
            self._current_note_id = note["note_id"]
            self._editor.setText(note["content"])

    def _save_note(self) -> None:
        content = self._editor.toPlainText().strip()
        if not content:
            return

        if self._current_note_id:
            self._db.update_note(self._current_note_id, content)
        elif self._book_id:
            self._current_note_id = self._db.add_note(
                self._book_id, self._chapter_num or 0,
                self._section_title, content,
            )
        self._load_notes()

    def _new_note(self) -> None:
        self._current_note_id = None
        self._editor.clear()
        self._editor.setFocus()

    def _delete_note(self) -> None:
        if not self._current_note_id:
            return
        reply = QMessageBox.question(
            self, "Delete Note", "Delete this note?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._db.delete_note(self._current_note_id)
            self._current_note_id = None
            self._editor.clear()
            self._load_notes()
