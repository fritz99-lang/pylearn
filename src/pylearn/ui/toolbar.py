# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Main toolbar with run/stop/font/theme controls."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QToolBar, QToolButton, QSpinBox, QComboBox, QLabel, QWidget, QHBoxLayout,
)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence


class MainToolBar(QToolBar):
    """Application toolbar with execution controls and settings."""

    run_requested = pyqtSignal()
    stop_requested = pyqtSignal()
    clear_console_requested = pyqtSignal()
    font_size_changed = pyqtSignal(int)
    theme_changed = pyqtSignal(str)
    external_editor_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__("Main Toolbar", parent)
        self.setMovable(False)

        # Run button (F5 shortcut is on the menu action to avoid ambiguity)
        self._run_action = QAction("Run", self)
        self._run_action.setToolTip("Run code (F5)")
        self._run_action.triggered.connect(self.run_requested.emit)
        self.addAction(self._run_action)

        # Stop button (Shift+F5 shortcut is on the menu action)
        self._stop_action = QAction("Stop", self)
        self._stop_action.setToolTip("Stop execution (Shift+F5)")
        self._stop_action.triggered.connect(self.stop_requested.emit)
        self._stop_action.setEnabled(False)
        self.addAction(self._stop_action)

        # Clear console
        self._clear_action = QAction("Clear", self)
        self._clear_action.setToolTip("Clear console output")
        self._clear_action.triggered.connect(self.clear_console_requested.emit)
        self.addAction(self._clear_action)

        self.addSeparator()

        # External editor (Ctrl+E shortcut is on the menu action)
        self._external_editor_action = QAction("Notepad++", self)
        self._external_editor_action.setToolTip("Edit in Notepad++ (Ctrl+E)")
        self._external_editor_action.triggered.connect(self.external_editor_requested.emit)
        self.addAction(self._external_editor_action)

        self.addSeparator()

        # Font size control
        font_widget = QWidget()
        font_layout = QHBoxLayout(font_widget)
        font_layout.setContentsMargins(4, 0, 4, 0)
        font_layout.addWidget(QLabel("Font:"))

        self._font_spin = QSpinBox()
        self._font_spin.setRange(8, 24)
        self._font_spin.setValue(12)
        self._font_spin.setSuffix("pt")
        self._font_spin.valueChanged.connect(self.font_size_changed.emit)
        font_layout.addWidget(self._font_spin)

        self.addWidget(font_widget)

        self.addSeparator()

        # Theme selector
        theme_widget = QWidget()
        theme_layout = QHBoxLayout(theme_widget)
        theme_layout.setContentsMargins(4, 0, 4, 0)
        theme_layout.addWidget(QLabel("Theme:"))

        self._theme_combo = QComboBox()
        self._theme_combo.addItems(["Light", "Dark", "Sepia"])
        self._theme_combo.currentTextChanged.connect(
            lambda text: self.theme_changed.emit(text.lower())
        )
        theme_layout.addWidget(self._theme_combo)

        self.addWidget(theme_widget)

    def set_running(self, running: bool) -> None:
        """Update toolbar state based on execution status."""
        self._run_action.setEnabled(not running)
        self._stop_action.setEnabled(running)

    def set_font_size(self, size: int) -> None:
        """Set the font size spinner value."""
        self._font_spin.blockSignals(True)
        self._font_spin.setValue(size)
        self._font_spin.blockSignals(False)

    def set_theme(self, theme: str) -> None:
        """Set the theme combo value."""
        self._theme_combo.blockSignals(True)
        self._theme_combo.setCurrentText(theme.capitalize())
        self._theme_combo.blockSignals(False)
