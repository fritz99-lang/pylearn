# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Progress overview dialog."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from pylearn.core.database import Database


class ProgressDialog(QDialog):
    """Dialog showing reading progress across all books."""

    def __init__(self, database: Database, parent=None) -> None:
        super().__init__(parent)
        self._db = database

        self.setWindowTitle("Reading Progress")
        self.setMinimumSize(500, 400)

        layout = QVBoxLayout(self)

        header = QLabel("Your Reading Progress")
        header.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 12px;")
        layout.addWidget(header)

        # Load stats for each book
        books = self._db.get_books()
        for book in books:
            book_id = book["book_id"]
            stats = self._db.get_completion_stats(book_id)

            group = QGroupBox(book["title"])
            group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 13px; }")
            group_layout = QGridLayout(group)

            # Progress bar
            progress = QProgressBar()
            progress.setMinimum(0)
            progress.setMaximum(100)
            progress.setValue(stats["percent"])
            progress.setFormat(f"{stats['percent']}%")
            progress.setMinimumHeight(25)
            group_layout.addWidget(progress, 0, 0, 1, 2)

            # Stats
            group_layout.addWidget(
                QLabel(f"Completed: {stats['completed']} / {stats['total']} chapters"),
                1,
                0,
            )
            group_layout.addWidget(
                QLabel(f"In Progress: {stats['in_progress']}"),
                1,
                1,
            )

            # Exercise stats
            completed_ex, total_ex = self._db.get_exercise_completion_count(book_id)
            if total_ex:
                group_layout.addWidget(
                    QLabel(f"Exercises: {completed_ex} / {total_ex} completed"),
                    2,
                    0,
                    1,
                    2,
                )

            layout.addWidget(group)

        if not books:
            layout.addWidget(QLabel("No books registered yet.\nAdd books via Book > Manage Library."))

        layout.addStretch()

        # Close
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        close_layout.addWidget(close_btn)
        layout.addLayout(close_layout)
