"""Exercise browser with completion tracking."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLabel, QPushButton, QHBoxLayout, QTextBrowser,
    QSplitter,
)
from PyQt6.QtCore import pyqtSignal, Qt

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

    def load_exercises(self, book_id: str) -> None:
        """Load exercises for a book from the database."""
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

        # Show exercise details
        exercises = self._db.get_exercises(book_id="")  # Need book_id context
        # For now, just show the exercise ID
        self._detail.setHtml(
            f'<p><b>{item.text(0)}</b></p>'
            f'<p style="color:#666;">Exercise ID: {exercise_id}</p>'
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
        if self._current_exercise_id:
            # Emit signal to load starter code
            self.load_code_requested.emit(
                f"# Exercise: {self._current_exercise_id}\n# Write your solution below\n\n"
            )
