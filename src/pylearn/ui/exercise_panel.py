# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Exercise browser with completion tracking."""

from __future__ import annotations

import html as html_mod

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from pylearn.core.database import Database


class ExercisePanel(QWidget):
    """Panel for browsing and tracking exercises."""

    exercise_selected = pyqtSignal(str)  # exercise_id
    load_code_requested = pyqtSignal(str)  # code to load in editor

    def __init__(self, database: Database, parent=None) -> None:
        super().__init__(parent)
        self._db = database

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        header = QLabel("Exercises")
        header.setStyleSheet("font-size: 14px; font-weight: bold; padding: 4px;")
        layout.addWidget(header)

        splitter = QSplitter(Qt.Orientation.Vertical)

        # Exercise tree
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Exercise", "Status"])
        self._tree.setColumnWidth(0, 250)
        self._tree.itemClicked.connect(self._on_item_clicked)
        splitter.addWidget(self._tree)

        # Exercise detail view
        detail_widget = QWidget()
        detail_layout = QVBoxLayout(detail_widget)
        detail_layout.setContentsMargins(0, 0, 0, 0)

        self._detail = QTextBrowser()
        self._detail.setMaximumHeight(200)
        detail_layout.addWidget(self._detail)

        btn_layout = QHBoxLayout()
        self._mark_done_btn = QPushButton("Mark Complete")
        self._mark_done_btn.clicked.connect(self._mark_complete)
        self._mark_done_btn.setEnabled(False)
        btn_layout.addWidget(self._mark_done_btn)

        self._try_btn = QPushButton("Try in Editor")
        self._try_btn.clicked.connect(self._try_exercise)
        self._try_btn.setEnabled(False)
        btn_layout.addWidget(self._try_btn)

        btn_layout.addStretch()
        detail_layout.addLayout(btn_layout)

        splitter.addWidget(detail_widget)
        layout.addWidget(splitter)

        self._current_exercise_id: str | None = None
        self._book_id: str = ""

    def load_exercises(self, book_id: str) -> None:
        """Load exercises for a book from the database."""
        self._book_id = book_id
        self._tree.clear()
        exercises = self._db.get_exercises(book_id)

        # Group by chapter
        chapters: dict[int, list[dict]] = {}
        for ex in exercises:
            ch = ex["chapter_num"]
            chapters.setdefault(ch, []).append(ex)

        for ch_num in sorted(chapters.keys()):
            ch_item = QTreeWidgetItem(self._tree)
            ch_item.setText(0, f"Chapter {ch_num}")
            ch_item.setFlags(ch_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)

            for ex in chapters[ch_num]:
                progress = self._db.get_exercise_progress(ex["exercise_id"])
                status = "Done" if progress and progress["completed"] else ""

                item = QTreeWidgetItem(ch_item)
                item.setText(0, ex["title"])
                item.setText(1, status)
                item.setData(0, Qt.ItemDataRole.UserRole, ex["exercise_id"])

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        exercise_id = item.data(0, Qt.ItemDataRole.UserRole)
        if not exercise_id:
            return

        self._current_exercise_id = exercise_id
        self._mark_done_btn.setEnabled(True)
        self._try_btn.setEnabled(True)

        # Show exercise details from database
        exercise = self._db.get_exercise(exercise_id)

        if exercise:
            title_esc = html_mod.escape(exercise["title"])
            desc_esc = html_mod.escape(exercise.get("description", "")).replace("\n", "<br>")
            self._detail.setHtml(f"<p><b>{title_esc}</b></p><p>{desc_esc}</p>")
        else:
            self._detail.setHtml(
                f"<p><b>{html_mod.escape(item.text(0))}</b></p>"
                f'<p style="color:#666;">Exercise ID: {html_mod.escape(exercise_id)}</p>'
            )
        self.exercise_selected.emit(exercise_id)

    def _mark_complete(self) -> None:
        if self._current_exercise_id:
            self._db.update_exercise_progress(self._current_exercise_id, True)
            # Refresh the tree
            current_item = self._tree.currentItem()
            if current_item:
                current_item.setText(1, "Done")

    def _try_exercise(self) -> None:
        if self._current_exercise_id and self._book_id:
            # Find the exercise to get its description as starter code
            exercise = self._db.get_exercise(self._current_exercise_id)
            desc = exercise.get("description", "") if exercise else ""
            # Build starter code with exercise description as comments
            lines = [f"# Exercise: {self._current_exercise_id}"]
            if desc:
                for line in desc.splitlines():
                    lines.append(f"# {line}")
            lines.append("# Write your solution below\n\n")
            self.load_code_requested.emit("\n".join(lines))
