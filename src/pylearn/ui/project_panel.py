# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Project panel for a book-spanning project built chapter by chapter."""

from __future__ import annotations

import html as html_mod

from PyQt6.Qsci import QsciLexerPython, QsciScintilla
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from pylearn.core.content_loader import ContentLoader
from pylearn.core.database import Database
from pylearn.core.models import ProjectMeta, ProjectStep
from pylearn.executor.session import Session
from pylearn.executor.test_runner import TestResult, TestRunner
from pylearn.ui.theme_registry import get_palette


class _ProjectTestWorker(QThread):
    """Background thread for running project step tests."""

    finished = pyqtSignal(object)  # TestResult

    def __init__(self, runner: TestRunner, user_code: str, test_code: str) -> None:
        super().__init__()
        self._runner = runner
        self._user_code = user_code
        self._test_code = test_code

    def run(self) -> None:
        result = self._runner.run_tests(self._user_code, self._test_code)
        self.finished.emit(result)


class ProjectPanel(QWidget):
    """Panel for the book-spanning project: step navigator, editor, test results."""

    def __init__(self, database: Database, content_loader: ContentLoader, session: Session, parent=None) -> None:
        super().__init__(parent)
        self._db = database
        self._content = content_loader
        self._session = session
        self._runner = TestRunner(session)
        self._meta: ProjectMeta | None = None
        self._steps: list[ProjectStep] = []
        self._current_step_index: int = -1
        self._book_id: str = ""
        self._project_id: str | None = None  # None = single project dir
        self._available_projects: list[ProjectMeta] = []
        self._theme = "light"
        self._worker: _ProjectTestWorker | None = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Project selector (shown when multiple projects exist)
        self._project_selector = QComboBox()
        self._project_selector.setVisible(False)
        self._project_selector.currentIndexChanged.connect(self._on_project_changed)
        layout.addWidget(self._project_selector)

        # Header
        self._title_label = QLabel("No Project Loaded")
        self._title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self._title_label)

        self._desc_label = QLabel("")
        self._desc_label.setWordWrap(True)
        self._desc_label.setStyleSheet("font-size: 11px;")
        layout.addWidget(self._desc_label)

        # Main content: step list (left) + step detail (right)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Step list
        self._step_list = QListWidget()
        self._step_list.setMaximumWidth(200)
        self._step_list.currentRowChanged.connect(self._on_step_selected)
        main_splitter.addWidget(self._step_list)

        # Right side: description + editor + results
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Step description + acceptance criteria
        self._step_browser = QTextBrowser()
        self._step_browser.setMaximumHeight(130)
        right_layout.addWidget(self._step_browser)

        # Hints
        self._hints_widget = QWidget()
        hints_layout = QHBoxLayout(self._hints_widget)
        hints_layout.setContentsMargins(0, 2, 0, 2)
        self._hint_btn = QPushButton("Show Hint")
        self._hint_btn.clicked.connect(self._show_next_hint)
        hints_layout.addWidget(self._hint_btn)
        self._hint_label = QLabel("")
        self._hint_label.setWordWrap(True)
        self._hint_label.setStyleSheet("font-size: 11px; font-style: italic;")
        hints_layout.addWidget(self._hint_label, 1)
        self._hints_widget.setVisible(False)
        right_layout.addWidget(self._hints_widget)

        # Code editor
        self._editor = QsciScintilla(self)
        self._setup_editor()
        right_layout.addWidget(self._editor, 1)

        # Results
        self._results_browser = QTextBrowser()
        self._results_browser.setMaximumHeight(100)
        right_layout.addWidget(self._results_browser)

        # Buttons
        btn_layout = QHBoxLayout()
        self._run_btn = QPushButton("Run Tests")
        self._run_btn.clicked.connect(self._run_tests)
        self._run_btn.setStyleSheet("font-weight: bold;")
        btn_layout.addWidget(self._run_btn)

        self._load_prev_btn = QPushButton("Load Previous Code")
        self._load_prev_btn.clicked.connect(self._load_previous_code)
        self._load_prev_btn.setToolTip("Load your saved code from the previous step as a starting point")
        btn_layout.addWidget(self._load_prev_btn)

        self._reset_btn = QPushButton("Reset to Starter")
        self._reset_btn.clicked.connect(self._reset_code)
        btn_layout.addWidget(self._reset_btn)

        btn_layout.addStretch()
        right_layout.addLayout(btn_layout)

        main_splitter.addWidget(right_widget)
        main_splitter.setSizes([160, 500])

        layout.addWidget(main_splitter, 1)

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

    def load_project(self, book_id: str) -> bool:
        """Load the project(s) for a book. Returns True if at least one project exists."""
        self._book_id = book_id
        self._available_projects = self._content.list_projects(book_id)

        if not self._available_projects:
            self._project_selector.setVisible(False)
            self._show_empty_state()
            return False

        # Show selector if multiple projects
        if len(self._available_projects) > 1:
            self._project_selector.blockSignals(True)
            self._project_selector.clear()
            for meta in self._available_projects:
                self._project_selector.addItem(meta.title, meta.project_id or "")
            self._project_selector.blockSignals(False)
            self._project_selector.setVisible(True)
        else:
            self._project_selector.setVisible(False)

        # Load first project
        first = self._available_projects[0]
        return self._load_single_project(first.project_id or None)

    def _on_project_changed(self, index: int) -> None:
        """Handle project selector change."""
        if index < 0 or index >= len(self._available_projects):
            return
        # Save current code before switching
        if self._current_step_index >= 0:
            self._save_current_code()
        meta = self._available_projects[index]
        self._load_single_project(meta.project_id or None)

    def _load_single_project(self, project_id: str | None) -> bool:
        """Load a specific project by its project_id."""
        self._project_id = project_id
        self._meta = self._content.load_project_meta(self._book_id, project_id)
        if not self._meta:
            self._show_empty_state()
            return False

        # Load all steps
        step_chapters = self._content.list_project_steps(self._book_id, project_id)
        self._steps = []
        for ch_num in step_chapters:
            step = self._content.load_project_step(self._book_id, ch_num, project_id)
            if step:
                self._steps.append(step)

        if not self._steps:
            self._show_empty_state()
            return False

        self._title_label.setText(self._meta.title)
        self._desc_label.setText(self._meta.description)

        # Populate step list
        self._step_list.clear()
        progress_map = {p["step_id"]: p for p in self._db.get_project_steps_progress(self._book_id)}
        for step in self._steps:
            prog = progress_map.get(step.step_id)
            done = prog and prog["completed"] if prog else False
            prefix = "[done]" if done else f"Ch {step.chapter_num}"
            item = QListWidgetItem(f"{prefix} — {step.title}")
            item.setData(Qt.ItemDataRole.UserRole, step.step_id)
            self._step_list.addItem(item)

        # Select first incomplete step, or first step
        first_incomplete = 0
        for i, step in enumerate(self._steps):
            prog = progress_map.get(step.step_id)
            if not prog or not prog["completed"]:
                first_incomplete = i
                break
        self._current_step_index = -1  # Reset before selecting
        self._step_list.setCurrentRow(first_incomplete)

        return True

    def _show_empty_state(self) -> None:
        self._title_label.setText("No Project Available")
        self._desc_label.setText("")
        self._step_list.clear()
        self._step_browser.setHtml("<p>No project for this book yet.</p>")
        self._editor.setText("")
        self._results_browser.clear()
        self._hints_widget.setVisible(False)
        self._run_btn.setEnabled(False)
        self._load_prev_btn.setEnabled(False)
        self._reset_btn.setEnabled(False)

    def _on_step_selected(self, row: int) -> None:
        """Handle step list selection."""
        if row < 0 or row >= len(self._steps):
            return
        # Save current code before switching
        if self._current_step_index >= 0:
            self._save_current_code()
        self._current_step_index = row
        self._display_step()

    def _display_step(self) -> None:
        if self._current_step_index < 0:
            return

        step = self._current_step

        # Description + acceptance criteria
        html = f"<p><b>Step {self._current_step_index + 1}: {html_mod.escape(step.title)}</b></p>"
        html += f"<p>{html_mod.escape(step.description)}</p>"
        if step.acceptance_criteria:
            html += "<p><b>Acceptance Criteria:</b></p><ul>"
            for criterion in step.acceptance_criteria:
                html += f"<li>{html_mod.escape(criterion)}</li>"
            html += "</ul>"
        self._step_browser.setHtml(html)

        # Hints
        self._hint_index = 0
        self._hint_label.setText("")
        if step.hints:
            self._hints_widget.setVisible(True)
            self._hint_btn.setEnabled(True)
            self._hint_btn.setText(f"Show Hint (1/{len(step.hints)})")
        else:
            self._hints_widget.setVisible(False)

        # Load saved code, or previous step's code, or starter code
        saved = self._db.get_project_progress(step.step_id)
        if saved and saved["user_code"]:
            self._editor.setText(saved["user_code"])
        else:
            self._editor.setText(step.starter_code)

        # Show previous results
        if saved and saved["completed"]:
            self._results_browser.setHtml('<p style="color: green; font-weight: bold;">Step completed!</p>')
        else:
            self._results_browser.clear()

        # Enable/disable load previous button
        self._load_prev_btn.setEnabled(self._current_step_index > 0)
        self._run_btn.setEnabled(True)
        self._reset_btn.setEnabled(True)

    def _load_previous_code(self) -> None:
        """Load saved code from the previous step into the editor."""
        if self._current_step_index <= 0:
            return
        prev_step = self._steps[self._current_step_index - 1]
        prev_prog = self._db.get_project_progress(prev_step.step_id)
        if prev_prog and prev_prog["user_code"]:
            self._editor.setText(prev_prog["user_code"])
        else:
            self._results_browser.setHtml('<p style="color: #888;">No saved code from previous step.</p>')

    def _show_next_hint(self) -> None:
        step = self._current_step
        if not step.hints or self._hint_index >= len(step.hints):
            return
        self._hint_label.setText(html_mod.escape(step.hints[self._hint_index]))
        self._hint_index += 1
        remaining = len(step.hints) - self._hint_index
        if remaining > 0:
            self._hint_btn.setText(f"Next Hint ({remaining} left)")
        else:
            self._hint_btn.setEnabled(False)
            self._hint_btn.setText("No more hints")

    def _run_tests(self) -> None:
        if self._current_step_index < 0 or (self._worker and self._worker.isRunning()):
            return

        step = self._current_step
        user_code = self._editor.text()

        self._run_btn.setEnabled(False)
        self._run_btn.setText("Running...")
        self._results_browser.setHtml('<p style="color: #888;">Running tests...</p>')

        if self._worker is not None:
            self._worker.wait(1000)
            self._worker.deleteLater()
        self._worker = _ProjectTestWorker(self._runner, user_code, step.test_code)
        self._worker.finished.connect(self._on_tests_finished)
        self._worker.start()

    def _on_tests_finished(self, result: TestResult) -> None:
        self._run_btn.setEnabled(True)
        self._run_btn.setText("Run Tests")

        if self._current_step_index < 0:
            return

        step = self._current_step
        user_code = self._editor.text()

        self._db.save_project_progress(step.step_id, self._book_id, step.chapter_num, result.passed, user_code)

        self._display_results(result)

        # Update step list item if completed
        if result.passed:
            item = self._step_list.item(self._current_step_index)
            if item:
                item.setText(f"[done] — {step.title}")

    def _display_results(self, result: TestResult) -> None:
        p = get_palette(self._theme)

        if result.timed_out:
            self._results_browser.setHtml(f'<p style="color: {p.warning_border}; font-weight: bold;">Timed out!</p>')
            return

        if result.error:
            error_esc = html_mod.escape(result.error)
            self._results_browser.setHtml(
                f'<p style="color: {p.warning_border}; font-weight: bold;">Error:</p>'
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
            f"{'  — Step complete!' if result.passed else ''}</p>"
        )

        self._results_browser.setHtml("".join(html_parts))

    def _reset_code(self) -> None:
        if self._current_step_index >= 0:
            self._editor.setText(self._current_step.starter_code)

    def _save_current_code(self) -> None:
        """Save current editor code to DB."""
        if self._current_step_index < 0:
            return
        step = self._current_step
        user_code = self._editor.text()
        if user_code.strip() and user_code.strip() != step.starter_code.strip():
            saved = self._db.get_project_progress(step.step_id)
            completed = saved["completed"] if saved else False
            self._db.save_project_progress(step.step_id, self._book_id, step.chapter_num, completed, user_code)

    def set_theme(self, theme_name: str) -> None:
        """Update project panel for the current theme."""
        self._theme = theme_name
        p = get_palette(theme_name)
        self._desc_label.setStyleSheet(f"font-size: 11px; color: {p.text_muted};")
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
    def _current_step(self) -> ProjectStep:
        assert 0 <= self._current_step_index < len(self._steps)
        return self._steps[self._current_step_index]
