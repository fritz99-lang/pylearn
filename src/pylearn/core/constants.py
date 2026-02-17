# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Application constants and metadata."""

import os
import shutil
import sys
from pathlib import Path

APP_NAME = "PyLearn"
APP_VERSION = "0.1.0"
APP_AUTHOR = "Nathan Tritle"

# Frozen-mode detection (PyInstaller sets sys.frozen)
IS_FROZEN = getattr(sys, "frozen", False)

# Directories — dual-mode resolution
if IS_FROZEN:
    # Frozen (PyInstaller): use %LOCALAPPDATA%\PyLearn for writable data
    _LOCAL_APP_DATA = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    APP_DIR = _LOCAL_APP_DATA / APP_NAME
    CONFIG_DIR = APP_DIR / "config"
    DATA_DIR = APP_DIR / "data"
else:
    # Dev mode: project root relative to this file
    APP_DIR = Path(__file__).resolve().parent.parent.parent.parent
    CONFIG_DIR = APP_DIR / "config"
    DATA_DIR = APP_DIR / "data"

CACHE_DIR = DATA_DIR / "cache"
DB_PATH = DATA_DIR / "pylearn.db"

# Ensure writable directories exist on first launch
for _d in (CONFIG_DIR, DATA_DIR, CACHE_DIR):
    try:
        _d.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass  # Components will create as needed

# Config files
APP_CONFIG_PATH = CONFIG_DIR / "app_config.json"
BOOKS_CONFIG_PATH = CONFIG_DIR / "books.json"
EDITOR_CONFIG_PATH = CONFIG_DIR / "editor_config.json"


def get_python_executable() -> str | None:
    """Return the path to a working Python interpreter.

    In dev mode, returns sys.executable (the venv Python).
    In frozen mode, searches PATH for python.exe since sys.executable
    is the PyLearn.exe bundle.
    """
    if not IS_FROZEN:
        return sys.executable
    # Frozen: find Python on PATH
    python = shutil.which("python3") or shutil.which("python")
    return python

# Defaults
DEFAULT_WINDOW_WIDTH = 1400
DEFAULT_WINDOW_HEIGHT = 900
DEFAULT_FONT_SIZE = 11
DEFAULT_EDITOR_FONT_SIZE = 12
DEFAULT_TAB_WIDTH = 4
DEFAULT_EXECUTION_TIMEOUT = 30
DEFAULT_THEME = "light"

# Reader panel
READER_SPLITTER_RATIO = [55, 45]
EDITOR_CONSOLE_RATIO = [60, 40]
TOC_WIDTH = 220

# Chapter status
STATUS_NOT_STARTED = "not_started"
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"
