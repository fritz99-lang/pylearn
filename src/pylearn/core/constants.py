"""Application constants and metadata."""

from pathlib import Path

APP_NAME = "PyLearn"
APP_VERSION = "0.1.0"
APP_AUTHOR = "Nathan Tritle"

# Directories
APP_DIR = Path(__file__).resolve().parent.parent.parent.parent
CONFIG_DIR = APP_DIR / "config"
DATA_DIR = APP_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
DB_PATH = DATA_DIR / "pylearn.db"

# Config files
APP_CONFIG_PATH = CONFIG_DIR / "app_config.json"
BOOKS_CONFIG_PATH = CONFIG_DIR / "books.json"
EDITOR_CONFIG_PATH = CONFIG_DIR / "editor_config.json"

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
