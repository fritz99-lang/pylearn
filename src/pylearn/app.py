# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""QApplication setup and configuration."""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont

from pylearn.core.constants import APP_NAME
from pylearn.ui.main_window import MainWindow
from pylearn.utils.error_handler import setup_logging


def create_app(debug: bool = False) -> tuple[QApplication, MainWindow]:
    """Create and configure the application."""
    setup_logging(debug=debug)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")

    # Default font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = MainWindow()
    return app, window


def run_app(debug: bool = False) -> int:
    """Create and run the application."""
    app, window = create_app(debug=debug)
    window.show()
    return app.exec()
