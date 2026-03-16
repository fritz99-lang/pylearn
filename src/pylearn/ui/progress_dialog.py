# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Progress overview dialog."""

from __future__ import annotations

from PyQt6.QtCore import Qt
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
from pylearn.utils.export import compute_overall_grade


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

            # Overall grade
            grade_data = compute_overall_grade(self._db, book_id)
            grade = grade_data["grade"]
            label = grade_data["label"]

            grade_bar = QProgressBar()
            grade_bar.setMinimum(0)
            grade_bar.setMaximum(100)
            grade_bar.setValue(grade)
            grade_bar.setFormat(f"Overall: {grade}% ({label})")
            grade_bar.setMinimumHeight(28)
            grade_bar.setStyleSheet(self._grade_bar_style(grade))
            group_layout.addWidget(grade_bar, 0, 0, 1, 2)

            # Breakdown
            breakdown = grade_data["breakdown"]
            row = 1
            for cat, info in breakdown.items():
                cat_label = _CATEGORY_LABELS.get(cat, cat.title())
                text = f"{cat_label}: {info['numerator']}/{info['denominator']} ({info['score']}%)"
                group_layout.addWidget(QLabel(text), row, 0)
                weight_label = QLabel(f"{info['weight']}% of grade")
                weight_label.setAlignment(Qt.AlignmentFlag.AlignRight)
                weight_label.setStyleSheet("color: gray; font-size: 11px;")
                group_layout.addWidget(weight_label, row, 1)
                row += 1

            # Reading detail
            group_layout.addWidget(
                QLabel(
                    f"Chapters: {stats['completed']} done, {stats['in_progress']} in progress, "
                    f"{stats['not_started']} not started"
                ),
                row,
                0,
                1,
                2,
            )
            row += 1

            # Exercise stats
            completed_ex, total_ex = self._db.get_exercise_completion_count(book_id)
            if total_ex:
                group_layout.addWidget(
                    QLabel(f"Exercises: {completed_ex} / {total_ex} completed"),
                    row,
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

    @staticmethod
    def _grade_bar_style(grade: int) -> str:
        """Return a QSS snippet that colors the progress bar by grade."""
        if grade >= 90:
            color = "#27ae60"  # green
        elif grade >= 70:
            color = "#2980b9"  # blue
        elif grade >= 50:
            color = "#f39c12"  # orange
        else:
            color = "#c0392b"  # red
        return (
            f"QProgressBar::chunk {{ background-color: {color}; border-radius: 3px; }}"
            f"QProgressBar {{ text-align: center; font-weight: bold; }}"
        )


_CATEGORY_LABELS = {
    "reading": "Reading",
    "quizzes": "Quizzes",
    "challenges": "Challenges",
    "project": "Project",
}
