# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Application constants and metadata."""

import os
import shutil
import sys
from pathlib import Path

APP_NAME = "PyLearn"
APP_VERSION = "1.0.1"
APP_AUTHOR = "Nathan Tritle"

# Frozen-mode detection (PyInstaller sets sys.frozen)
IS_FROZEN = getattr(sys, "frozen", False)


def _user_data_dir() -> Path:
    """Return the platform-appropriate user data directory for PyLearn."""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / APP_NAME.lower()


def _detect_app_dir() -> Path:
    """Resolve the application root directory (three modes).

    1. Frozen (PyInstaller): user data dir (%LOCALAPPDATA%/pylearn etc.)
    2. Dev (git clone): project root where pyproject.toml + scripts/ exist
    3. Pip-installed (fallback): user data dir (same layout as frozen)
    """
    if IS_FROZEN:
        return _user_data_dir()

    # Check if we're in a dev checkout: 4 parents up from this file should
    # contain pyproject.toml and scripts/
    candidate = Path(__file__).resolve().parent.parent.parent.parent
    if (candidate / "pyproject.toml").exists() and (candidate / "scripts").is_dir():
        return candidate

    # Pip-installed: __file__ is in site-packages, fall back to user data dir
    return _user_data_dir()


# Directories — three-mode resolution
APP_DIR = _detect_app_dir()
IS_DEV = not IS_FROZEN and (APP_DIR / "pyproject.toml").exists()
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

# In dev mode, auto-copy config/*.json.example → config/*.json if missing
if IS_DEV:
    for _example in APP_DIR.glob("config/*.json.example"):
        _target = _example.with_suffix("")  # strip .example
        if not _target.exists():
            try:
                shutil.copy2(_example, _target)
            except OSError:
                pass

# In frozen mode, seed config files from bundled examples in _MEIPASS
if IS_FROZEN:
    _bundle_dir = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    for _example in _bundle_dir.glob("config/*.json.example"):
        _target = CONFIG_DIR / _example.stem  # e.g., "books.json"
        if not _target.exists():
            try:
                shutil.copy2(_example, _target)
            except OSError:
                pass

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
