# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Challenge panel for code challenges with test validation."""

from __future__ import annotations

import html as html_mod

from PyQt6.Qsci import QsciLexerPython, QsciScintilla
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from pylearn.core.content_loader import ContentLoader
from pylearn.core.database import Database
from pylearn.core.models import ChallengeSet, ChallengeSpec
from pylearn.executor.session import Session
from pylearn.executor.test_runner import TestResult, TestRunner
from pylearn.ui.theme_registry import get_palette


class _TestWorker(QThread):
    """Background thread for running challenge tests."""

    finished = pyqtSignal(object)  # TestResult

    def __init__(self, runner: TestRunner, user_code: str, test_code: str) -> None:
        super().__init__()
        self._runner = runner
        self._user_code = user_code
        self._test_code = test_code

    def run(self) -> None:
        result = self._runner.run_tests(self._user_code, self._test_code)
        self.finished.emit(result)


class ChallengePanel(QWidget):
    """Panel for code challenges: description, editor, test results."""

    def __init__(self, database: Database, content_loader: ContentLoader, session: Session, parent=None) -> None:
        super().__init__(parent)
        self._db = database
        self._content = content_loader
        self._session = session
        self._runner = TestRunner(session)
        self._challenges: ChallengeSet | None = None
        self._current_index: int = 0
        self._theme = "light"
        self._worker: _TestWorker | None = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Header
        header_layout = QHBoxLayout()
        self._title_label = QLabel("No Challenge Loaded")
        self._title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        header_layout.addWidget(self._title_label)
        header_layout.addStretch()
        self._progress_label = QLabel("")
        self._progress_label.setStyleSheet("font-size: 12px;")
        header_layout.addWidget(self._progress_label)
        layout.addLayout(header_layout)

        # Score
        self._score_label = QLabel("")
        self._score_label.setStyleSheet("font-size: 11px;")
        layout.addWidget(self._score_label)

        # Main splitter: description+hints on top, editor+results on bottom
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Top: Description + hints
        desc_widget = QWidget()
        desc_layout = QVBoxLayout(desc_widget)
        desc_layout.setContentsMargins(0, 0, 0, 0)

        self._desc_browser = QTextBrowser()
        self._desc_browser.setMaximumHeight(150)
        desc_layout.addWidget(self._desc_browser)

        # Hints
        self._hints_widget = QWidget()
        hints_layout = QHBoxLayout(self._hints_widget)
        hints_layout.setContentsMargins(0, 4, 0, 0)
        self._hint_btn = QPushButton("Show Hint")
        self._hint_btn.clicked.connect(self._show_next_hint)
        hints_layout.addWidget(self._hint_btn)
        self._hint_label = QLabel("")
        self._hint_label.setWordWrap(True)
        self._hint_label.setStyleSheet("font-size: 11px; font-style: italic; padding: 4px;")
        hints_layout.addWidget(self._hint_label, 1)
        desc_layout.addWidget(self._hints_widget)

        splitter.addWidget(desc_widget)

        # Bottom: Code editor + results
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)

        self._editor = QsciScintilla(self)
        self._setup_editor()
        bottom_layout.addWidget(self._editor, 1)

        # Results area
        self._results_browser = QTextBrowser()
        self._results_browser.setMaximumHeight(120)
        bottom_layout.addWidget(self._results_browser)

        splitter.addWidget(bottom_widget)
        splitter.setSizes([180, 400])

        layout.addWidget(splitter, 1)

        # Buttons
        btn_layout = QHBoxLayout()
        self._prev_btn = QPushButton("Previous")
        self._prev_btn.clicked.connect(self._prev_challenge)
        btn_layout.addWidget(self._prev_btn)

        self._run_btn = QPushButton("Run Tests")
        self._run_btn.clicked.connect(self._run_tests)
        self._run_btn.setStyleSheet("font-weight: bold;")
        btn_layout.addWidget(self._run_btn)

        self._next_btn = QPushButton("Next")
        self._next_btn.clicked.connect(self._next_challenge)
        btn_layout.addWidget(self._next_btn)

        btn_layout.addStretch()

        self._reset_btn = QPushButton("Reset Code")
        self._reset_btn.clicked.connect(self._reset_code)
        btn_layout.addWidget(self._reset_btn)

        layout.addLayout(btn_layout)

        self._show_empty_state()

    def _setup_editor(self) -> None:
        editor = self._editor
        lexer = QsciLexerPython(editor)
        font = QFont("Consolas", 12)
        lexer.setDefaultFont(font)
        lexer.setFont(font)
        editor.setLexer(lexer)
        editor.setMarginType(0, QsciScintilla.MarginType.NumberMargin)
        editor.setMarginWidth(0, "0000")
        editor.setCaretLineVisible(True)
        editor.setIndentationsUseTabs(False)
        editor.setTabWidth(4)
        editor.setAutoIndent(True)
        editor.setBraceMatching(QsciScintilla.BraceMatch.SloppyBraceMatch)
        editor.setWrapMode(QsciScintilla.WrapMode.WrapNone)

    def load_challenges(self, book_id: str, chapter_num: int) -> bool:
        """Load challenges for the given chapter. Returns True if challenges exist."""
        self._challenges = self._content.load_challenges(book_id, chapter_num)
        if not self._challenges or not self._challenges.challenges:
            self._show_empty_state()
            return False

        self._current_index = 0
        self._title_label.setText(f"Chapter {chapter_num} Challenges")
        self._display_challenge()
        self._update_score()
        return True

    def _show_empty_state(self) -> None:
        self._title_label.setText("No Challenges Available")
        self._progress_label.setText("")
        self._score_label.setText("")
        self._desc_browser.setHtml("<p>No challenges for this chapter yet.</p>")
        self._editor.setText("")
        self._results_browser.clear()
        self._hints_widget.setVisible(False)
        self._prev_btn.setEnabled(False)
        self._next_btn.setEnabled(False)
        self._run_btn.setEnabled(False)
        self._reset_btn.setEnabled(False)

    def _display_challenge(self) -> None:
        if not self._challenges:
            return

        c = self._current_challenge
        total = len(self._challenges.challenges)

        self._progress_label.setText(f"Challenge {self._current_index + 1} of {total}")

        # Description
        diff_badge = {"easy": "Easy", "medium": "Medium", "hard": "Hard"}.get(c.difficulty, c.difficulty)
        desc_html = f"<p><b>{html_mod.escape(c.title)}</b> [{diff_badge}]</p>"
        desc_html += f"<p>{html_mod.escape(c.description)}</p>"
        if c.concepts_new:
            desc_html += f"<p><small>New concepts: {', '.join(c.concepts_new)}</small></p>"
        self._desc_browser.setHtml(desc_html)

        # Hints
        self._hint_index = 0
        self._hint_label.setText("")
        if c.hints:
            self._hints_widget.setVisible(True)
            self._hint_btn.setEnabled(True)
            self._hint_btn.setText(f"Show Hint (1/{len(c.hints)})")
        else:
            self._hints_widget.setVisible(False)

        # Load saved code or starter code
        saved = self._db.get_challenge_progress(c.challenge_id)
        if saved and saved["user_code"]:
            self._editor.setText(saved["user_code"])
        else:
            self._editor.setText(c.starter_code)

        # Show previous results if passed
        if saved and saved["passed"]:
            self._results_browser.setHtml('<p style="color: green; font-weight: bold;">Previously completed!</p>')
        else:
            self._results_browser.clear()

        # Navigation
        self._prev_btn.setEnabled(self._current_index > 0)
        self._next_btn.setEnabled(self._current_index < total - 1)
        self._run_btn.setEnabled(True)
        self._reset_btn.setEnabled(True)

    def _show_next_hint(self) -> None:
        c = self._current_challenge
        if not c.hints or self._hint_index >= len(c.hints):
            return
        self._hint_label.setText(html_mod.escape(c.hints[self._hint_index]))
        self._hint_index += 1
        remaining = len(c.hints) - self._hint_index
        if remaining > 0:
            self._hint_btn.setText(f"Next Hint ({remaining} left)")
        else:
            self._hint_btn.setEnabled(False)
            self._hint_btn.setText("No more hints")

    def _run_tests(self) -> None:
        if not self._challenges or (self._worker and self._worker.isRunning()):
            return

        c = self._current_challenge
        user_code = self._editor.text()

        self._run_btn.setEnabled(False)
        self._run_btn.setText("Running...")
        self._results_browser.setHtml('<p style="color: #888;">Running tests...</p>')

        # Run in background thread
        if self._worker is not None:
            self._worker.wait(1000)
            self._worker.deleteLater()
        self._worker = _TestWorker(self._runner, user_code, c.test_code)
        self._worker.finished.connect(self._on_tests_finished)
        self._worker.start()

    def _on_tests_finished(self, result: TestResult) -> None:
        self._run_btn.setEnabled(True)
        self._run_btn.setText("Run Tests")

        if not self._challenges:
            return

        c = self._current_challenge
        user_code = self._editor.text()

        # Save progress
        self._db.save_challenge_progress(
            c.challenge_id,
            self._challenges.book_id,
            self._challenges.chapter_num,
            result.passed,
            user_code,
        )

        # Display results
        self._display_results(result)
        self._update_score()

    def _display_results(self, result: TestResult) -> None:
        p = get_palette(self._theme)

        if result.timed_out:
            self._results_browser.setHtml(f'<p style="color: {p.warning_border}; font-weight: bold;">Timed out!</p>')
            return

        if result.error:
            error_esc = html_mod.escape(result.error)
            self._results_browser.setHtml(
                f'<p style="color: {p.warning_border}; font-weight: bold;">Error in your code:</p>'
                f'<pre style="color: {p.warning_border};">{error_esc}</pre>'
            )
            return

        html_parts = []
        for r in result.results:
            if r["passed"]:
                html_parts.append(f'<p style="color: {p.tip_border};">[PASS] {html_mod.escape(r["name"])}</p>')
            else:
                html_parts.append(f'<p style="color: {p.warning_border};">[FAIL] {html_mod.escape(r["message"])}</p>')

        summary_color = p.tip_border if result.passed else p.warning_border
        html_parts.append(
            f'<p style="font-weight: bold; color: {summary_color};">'
            f"{result.passed_tests}/{result.total_tests} tests passed"
            f"{'  — Challenge complete!' if result.passed else ''}</p>"
        )

        # Show stdout if any (user's print output)
        user_stdout = "\n".join(
            line
            for line in result.stdout.splitlines()
            if not line.strip().startswith("[PASS]")
            and not line.strip().startswith("[FAIL]")
            and not line.strip().startswith("[ERROR]")
            and "tests passed" not in line
        ).strip()
        if user_stdout:
            html_parts.append(
                f'<pre style="color: {p.text_muted}; margin-top: 4px;">{html_mod.escape(user_stdout)}</pre>'
            )

        self._results_browser.setHtml("".join(html_parts))

    def _update_score(self) -> None:
        if not self._challenges:
            return
        stats = self._db.get_challenge_stats(self._challenges.book_id, self._challenges.chapter_num)
        total_c = len(self._challenges.challenges)
        attempted = stats["total"]
        passed = stats["passed"]
        p = get_palette(self._theme)
        self._score_label.setStyleSheet(f"font-size: 11px; color: {p.text_muted};")
        self._score_label.setText(f"Progress: {passed}/{total_c} completed ({attempted} attempts)")

    def _next_challenge(self) -> None:
        if self._challenges and self._current_index < len(self._challenges.challenges) - 1:
            self._save_current_code()
            self._current_index += 1
            self._display_challenge()

    def _prev_challenge(self) -> None:
        if self._current_index > 0:
            self._save_current_code()
            self._current_index -= 1
            self._display_challenge()

    def _reset_code(self) -> None:
        if self._challenges:
            self._editor.setText(self._current_challenge.starter_code)

    def _save_current_code(self) -> None:
        """Save the current editor code to DB before navigating away."""
        if not self._challenges:
            return
        c = self._current_challenge
        user_code = self._editor.text()
        if user_code.strip() and user_code.strip() != c.starter_code.strip():
            saved = self._db.get_challenge_progress(c.challenge_id)
            passed = saved["passed"] if saved else False
            self._db.save_challenge_progress(
                c.challenge_id,
                self._challenges.book_id,
                self._challenges.chapter_num,
                passed,
                user_code,
            )

    def set_theme(self, theme_name: str) -> None:
        """Update challenge panel for the current theme."""
        self._theme = theme_name
        p = get_palette(theme_name)
        self._score_label.setStyleSheet(f"font-size: 11px; color: {p.text_muted};")

        # Editor theme
        from PyQt6.QtGui import QColor

        self._editor.setPaper(QColor(p.bg))
        self._editor.setColor(QColor(p.text))
        self._editor.setMarginsBackgroundColor(QColor(p.bg_alt))
        self._editor.setMarginsForegroundColor(QColor(p.text_muted))
        self._editor.setCaretLineBackgroundColor(QColor(p.border))
        self._editor.setCaretForegroundColor(QColor(p.text))

        lexer = self._editor.lexer()
        if lexer:
            lexer.setPaper(QColor(p.bg))
            lexer.setColor(QColor(p.text))

    @property
    def _current_challenge(self) -> ChallengeSpec:
        assert self._challenges is not None
        return self._challenges.challenges[self._current_index]
