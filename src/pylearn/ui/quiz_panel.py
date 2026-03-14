# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Quiz panel for chapter-end quizzes (multiple choice and fill-in-the-blank)."""

from __future__ import annotations

import html as html_mod

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from pylearn.core.content_loader import ContentLoader
from pylearn.core.database import Database
from pylearn.core.models import QuizQuestion, QuizSet
from pylearn.ui.theme_registry import get_palette


class QuizPanel(QWidget):
    """Panel for taking chapter quizzes with MC and fill-in-the-blank questions."""

    def __init__(self, database: Database, content_loader: ContentLoader, parent=None) -> None:
        super().__init__(parent)
        self._db = database
        self._content = content_loader
        self._quiz: QuizSet | None = None
        self._current_index: int = 0
        self._answered: bool = False
        self._theme = "light"

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Header with progress
        header_layout = QHBoxLayout()
        self._title_label = QLabel("No Quiz Loaded")
        self._title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        header_layout.addWidget(self._title_label)
        header_layout.addStretch()
        self._progress_label = QLabel("")
        self._progress_label.setStyleSheet("font-size: 12px;")
        header_layout.addWidget(self._progress_label)
        layout.addLayout(header_layout)

        # Score summary
        self._score_label = QLabel("")
        self._score_label.setStyleSheet("font-size: 11px; color: #666;")
        layout.addWidget(self._score_label)

        # Scrollable question area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        self._question_widget = QWidget()
        self._question_layout = QVBoxLayout(self._question_widget)
        self._question_layout.setContentsMargins(0, 8, 0, 8)
        self._question_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Question text
        self._question_label = QLabel("")
        self._question_label.setWordWrap(True)
        self._question_label.setStyleSheet("font-size: 13px; padding: 8px 0;")
        self._question_layout.addWidget(self._question_label)

        # MC choices container
        self._choices_widget = QWidget()
        self._choices_layout = QVBoxLayout(self._choices_widget)
        self._choices_layout.setContentsMargins(8, 0, 0, 0)
        self._choices_layout.setSpacing(6)
        self._button_group = QButtonGroup(self)
        self._question_layout.addWidget(self._choices_widget)

        # Fill-in-blank input
        self._fill_input = QLineEdit()
        self._fill_input.setPlaceholderText("Type your answer here...")
        self._fill_input.returnPressed.connect(self._check_answer)
        self._question_layout.addWidget(self._fill_input)

        # Explanation / feedback
        self._feedback_label = QLabel("")
        self._feedback_label.setWordWrap(True)
        self._feedback_label.setStyleSheet("font-size: 12px; padding: 8px; border-radius: 4px;")
        self._feedback_label.setVisible(False)
        self._question_layout.addWidget(self._feedback_label)

        self._question_layout.addStretch()
        scroll.setWidget(self._question_widget)
        layout.addWidget(scroll, 1)

        # Navigation buttons
        btn_layout = QHBoxLayout()
        self._prev_btn = QPushButton("Previous")
        self._prev_btn.clicked.connect(self._prev_question)
        btn_layout.addWidget(self._prev_btn)

        self._check_btn = QPushButton("Check Answer")
        self._check_btn.clicked.connect(self._check_answer)
        self._check_btn.setStyleSheet("font-weight: bold;")
        btn_layout.addWidget(self._check_btn)

        self._next_btn = QPushButton("Next")
        self._next_btn.clicked.connect(self._next_question)
        btn_layout.addWidget(self._next_btn)

        btn_layout.addStretch()

        self._retry_btn = QPushButton("Retry Quiz")
        self._retry_btn.clicked.connect(self._retry_quiz)
        self._retry_btn.setVisible(False)
        btn_layout.addWidget(self._retry_btn)

        layout.addLayout(btn_layout)

        # Start with empty state
        self._show_empty_state()

    def load_quiz(self, book_id: str, chapter_num: int) -> bool:
        """Load a quiz for the given chapter. Returns True if quiz exists."""
        self._quiz = self._content.load_quiz(book_id, chapter_num)
        if not self._quiz or not self._quiz.questions:
            self._show_empty_state()
            return False

        self._current_index = 0
        self._answered = False
        self._title_label.setText(f"Chapter {chapter_num} Quiz")
        self._retry_btn.setVisible(False)
        self._display_question()
        self._update_score()
        return True

    def _show_empty_state(self) -> None:
        self._title_label.setText("No Quiz Available")
        self._progress_label.setText("")
        self._score_label.setText("")
        self._question_label.setText("No quiz content for this chapter yet.")
        self._choices_widget.setVisible(False)
        self._fill_input.setVisible(False)
        self._feedback_label.setVisible(False)
        self._prev_btn.setEnabled(False)
        self._next_btn.setEnabled(False)
        self._check_btn.setEnabled(False)
        self._retry_btn.setVisible(False)

    def _display_question(self) -> None:
        if not self._quiz:
            return

        q = self._current_question
        total = len(self._quiz.questions)

        self._progress_label.setText(f"Question {self._current_index + 1} of {total}")
        self._question_label.setText(html_mod.escape(q.question))

        # Check if already answered
        saved = self._db.get_quiz_answer(q.question_id)
        self._answered = saved is not None

        # Show appropriate input type
        if q.question_type == "multiple_choice":
            self._show_mc_choices(q, saved)
            self._fill_input.setVisible(False)
        else:
            self._choices_widget.setVisible(False)
            self._fill_input.setVisible(True)
            if saved:
                self._fill_input.setText(saved["user_answer"])
                self._fill_input.setReadOnly(True)
            else:
                self._fill_input.clear()
                self._fill_input.setReadOnly(False)

        # Show feedback if already answered
        if saved:
            self._show_feedback(saved["correct"])
            self._check_btn.setEnabled(False)
        else:
            self._feedback_label.setVisible(False)
            self._check_btn.setEnabled(True)

        # Navigation
        self._prev_btn.setEnabled(self._current_index > 0)
        self._next_btn.setEnabled(self._current_index < total - 1)

    def _show_mc_choices(self, q: QuizQuestion, saved: dict | None) -> None:
        # Clear old choices
        for btn in self._button_group.buttons():
            self._button_group.removeButton(btn)
            btn.deleteLater()
        while self._choices_layout.count():
            item = self._choices_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._choices_widget.setVisible(True)

        for i, choice in enumerate(q.choices):
            radio = QRadioButton(html_mod.escape(choice))
            radio.setStyleSheet("font-size: 12px; padding: 4px;")
            self._button_group.addButton(radio, i)
            self._choices_layout.addWidget(radio)

            if saved:
                radio.setEnabled(False)
                try:
                    if str(i) == str(saved["user_answer"]):
                        radio.setChecked(True)
                except (ValueError, KeyError):
                    pass

    def set_theme(self, theme_name: str) -> None:
        """Update quiz panel colors for the current theme."""
        self._theme = theme_name
        p = get_palette(theme_name)
        self._score_label.setStyleSheet(f"font-size: 11px; color: {p.text_muted};")
        # Re-display feedback if visible to pick up new theme colors
        if self._feedback_label.isVisible() and self._quiz:
            saved = self._db.get_quiz_answer(self._current_question.question_id)
            if saved:
                self._show_feedback(saved["correct"])

    def _show_feedback(self, correct: bool) -> None:
        q = self._current_question
        p = get_palette(self._theme)
        if correct:
            style = f"background-color: {p.tip_bg}; color: {p.tip_border}; padding: 8px; border-radius: 4px;"
            text = "Correct!"
        else:
            style = f"background-color: {p.warning_bg}; color: {p.warning_border}; padding: 8px; border-radius: 4px;"
            if q.question_type == "multiple_choice" and isinstance(q.correct, int):
                correct_text = q.choices[q.correct] if q.correct < len(q.choices) else "?"
                text = f"Incorrect. The answer is: {html_mod.escape(correct_text)}"
            else:
                text = f"Incorrect. The answer is: {html_mod.escape(str(q.correct))}"

        if q.explanation:
            text += f"<br><br><i>{html_mod.escape(q.explanation)}</i>"

        self._feedback_label.setStyleSheet(style)
        self._feedback_label.setText(text)
        self._feedback_label.setVisible(True)

    def _check_answer(self) -> None:
        if not self._quiz or self._answered:
            return

        q = self._current_question

        if q.question_type == "multiple_choice":
            checked = self._button_group.checkedId()
            if checked < 0:
                return  # Nothing selected
            user_answer = str(checked)
            correct = checked == q.correct
        else:
            user_answer = self._fill_input.text().strip()
            if not user_answer:
                return
            correct = user_answer.lower() == str(q.correct).lower()

        # Save to database
        self._db.save_quiz_answer(q.question_id, self._quiz.book_id, self._quiz.chapter_num, correct, user_answer)
        self._answered = True

        # Update UI
        self._show_feedback(correct)
        self._check_btn.setEnabled(False)
        self._update_score()

        # Disable inputs
        if q.question_type == "multiple_choice":
            for btn in self._button_group.buttons():
                btn.setEnabled(False)
        else:
            self._fill_input.setReadOnly(True)

        # Show retry button if all questions answered
        if self._quiz:
            all_answered = all(self._db.get_quiz_answer(qq.question_id) is not None for qq in self._quiz.questions)
            if all_answered:
                self._retry_btn.setVisible(True)

    def _update_score(self) -> None:
        if not self._quiz:
            return
        stats = self._db.get_quiz_stats(self._quiz.book_id, self._quiz.chapter_num)
        total_q = len(self._quiz.questions)
        answered = stats["total"]
        correct = stats["correct"]
        self._score_label.setText(f"Score: {correct}/{answered} correct ({answered}/{total_q} answered)")

    def _next_question(self) -> None:
        if self._quiz and self._current_index < len(self._quiz.questions) - 1:
            self._current_index += 1
            self._display_question()

    def _prev_question(self) -> None:
        if self._current_index > 0:
            self._current_index -= 1
            self._display_question()

    def _retry_quiz(self) -> None:
        """Reset all answers for this quiz and start over."""
        if not self._quiz:
            return
        self._db.reset_quiz_progress([q.question_id for q in self._quiz.questions])

        self._current_index = 0
        self._answered = False
        self._retry_btn.setVisible(False)
        self._display_question()
        self._update_score()

    @property
    def _current_question(self) -> QuizQuestion:
        assert self._quiz is not None
        return self._quiz.questions[self._current_index]
