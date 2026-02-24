# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""JSON configuration loading and saving."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pylearn.core.constants import (
    APP_CONFIG_PATH,
    BOOKS_CONFIG_PATH,
    DEFAULT_EDITOR_FONT_SIZE,
    DEFAULT_EXECUTION_TIMEOUT,
    DEFAULT_FONT_SIZE,
    DEFAULT_TAB_WIDTH,
    DEFAULT_THEME,
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_WINDOW_WIDTH,
    EDITOR_CONFIG_PATH,
    EDITOR_CONSOLE_RATIO,
    READER_SPLITTER_RATIO,
    TOC_WIDTH,
)

logger = logging.getLogger("pylearn.config")


def _safe_int(value: Any, default: int) -> int:
    """Convert value to int, returning default on failure."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _load_json(path: Path) -> dict[str, Any]:
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
            logger.error(f"Corrupt config file {path}: {e} — using defaults")
    return {}


def _save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)
    except OSError:
        try:
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass
    finally:
        tmp.unlink(missing_ok=True)


class AppConfig:
    """Application-level configuration."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        self._data = _load_json(APP_CONFIG_PATH)

    def save(self) -> None:
        _save_json(APP_CONFIG_PATH, self._data)

    @property
    def window_width(self) -> int:
        return _safe_int(self._data.get("window_width", DEFAULT_WINDOW_WIDTH), DEFAULT_WINDOW_WIDTH)

    @window_width.setter
    def window_width(self, value: int) -> None:
        self._data["window_width"] = value

    @property
    def window_height(self) -> int:
        return _safe_int(self._data.get("window_height", DEFAULT_WINDOW_HEIGHT), DEFAULT_WINDOW_HEIGHT)

    @window_height.setter
    def window_height(self, value: int) -> None:
        self._data["window_height"] = value

    @property
    def window_x(self) -> int | None:
        return self._data.get("window_x")

    @window_x.setter
    def window_x(self, value: int) -> None:
        self._data["window_x"] = value

    @property
    def window_y(self) -> int | None:
        return self._data.get("window_y")

    @window_y.setter
    def window_y(self, value: int) -> None:
        self._data["window_y"] = value

    @property
    def window_maximized(self) -> bool:
        return bool(self._data.get("window_maximized", False))

    @window_maximized.setter
    def window_maximized(self, value: bool) -> None:
        self._data["window_maximized"] = value

    @property
    def theme(self) -> str:
        return str(self._data.get("theme", DEFAULT_THEME))

    @theme.setter
    def theme(self, value: str) -> None:
        self._data["theme"] = value

    @property
    def reader_font_size(self) -> int:
        val = _safe_int(self._data.get("reader_font_size", DEFAULT_FONT_SIZE), DEFAULT_FONT_SIZE)
        return max(6, min(72, val))

    @reader_font_size.setter
    def reader_font_size(self, value: int) -> None:
        self._data["reader_font_size"] = max(6, min(72, value))

    @property
    def last_book_id(self) -> str | None:
        return self._data.get("last_book_id")

    @last_book_id.setter
    def last_book_id(self, value: str) -> None:
        self._data["last_book_id"] = value

    @property
    def splitter_sizes(self) -> list[int]:
        return list(self._data.get("splitter_sizes", READER_SPLITTER_RATIO))

    @splitter_sizes.setter
    def splitter_sizes(self, value: list[int]) -> None:
        self._data["splitter_sizes"] = value

    @property
    def editor_console_sizes(self) -> list[int]:
        return list(self._data.get("editor_console_sizes", EDITOR_CONSOLE_RATIO))

    @editor_console_sizes.setter
    def editor_console_sizes(self, value: list[int]) -> None:
        self._data["editor_console_sizes"] = value

    @property
    def toc_width(self) -> int:
        return _safe_int(self._data.get("toc_width", TOC_WIDTH), TOC_WIDTH)

    @toc_width.setter
    def toc_width(self, value: int) -> None:
        self._data["toc_width"] = value

    @property
    def toc_visible(self) -> bool:
        return bool(self._data.get("toc_visible", True))

    @toc_visible.setter
    def toc_visible(self, value: bool) -> None:
        self._data["toc_visible"] = value


class BooksConfig:
    """Book registry configuration."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        self._data = _load_json(BOOKS_CONFIG_PATH)
        # Ensure "books" is a list (guard against corrupted JSON)
        if not isinstance(self._data.get("books"), list):
            self._data["books"] = []
        # Migrate: ensure all entries have required keys
        for book in self._data.get("books", []):
            book.setdefault("language", "python")
            book.setdefault("profile_name", "")

    def save(self) -> None:
        _save_json(BOOKS_CONFIG_PATH, self._data)

    @property
    def books(self) -> list[dict[str, Any]]:
        return list(self._data.get("books", []))

    def add_book(
        self, book_id: str, title: str, pdf_path: str, language: str = "python", profile_name: str = ""
    ) -> None:
        books = self.books
        for b in books:
            if b["book_id"] == book_id:
                b.update(title=title, pdf_path=pdf_path, language=language, profile_name=profile_name)
                self._data["books"] = books
                return
        books.append(
            {
                "book_id": book_id,
                "title": title,
                "pdf_path": pdf_path,
                "language": language,
                "profile_name": profile_name,
            }
        )
        self._data["books"] = books

    def get_book(self, book_id: str) -> dict | None:
        for b in self.books:
            if b["book_id"] == book_id:
                return b
        return None

    def remove_book(self, book_id: str) -> None:
        self._data["books"] = [b for b in self.books if b["book_id"] != book_id]


class EditorConfig:
    """Code editor configuration."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        self._data = _load_json(EDITOR_CONFIG_PATH)

    def save(self) -> None:
        _save_json(EDITOR_CONFIG_PATH, self._data)

    @property
    def font_size(self) -> int:
        val = _safe_int(self._data.get("font_size", DEFAULT_EDITOR_FONT_SIZE), DEFAULT_EDITOR_FONT_SIZE)
        return max(6, min(72, val))

    @font_size.setter
    def font_size(self, value: int) -> None:
        self._data["font_size"] = max(6, min(72, value))

    @property
    def tab_width(self) -> int:
        val = _safe_int(self._data.get("tab_width", DEFAULT_TAB_WIDTH), DEFAULT_TAB_WIDTH)
        return max(1, min(16, val))

    @tab_width.setter
    def tab_width(self, value: int) -> None:
        self._data["tab_width"] = max(1, min(16, value))

    @property
    def show_line_numbers(self) -> bool:
        return bool(self._data.get("show_line_numbers", True))

    @show_line_numbers.setter
    def show_line_numbers(self, value: bool) -> None:
        self._data["show_line_numbers"] = value

    @property
    def auto_indent(self) -> bool:
        return bool(self._data.get("auto_indent", True))

    @auto_indent.setter
    def auto_indent(self, value: bool) -> None:
        self._data["auto_indent"] = value

    @property
    def word_wrap(self) -> bool:
        return bool(self._data.get("word_wrap", False))

    @word_wrap.setter
    def word_wrap(self, value: bool) -> None:
        self._data["word_wrap"] = value

    @property
    def execution_timeout(self) -> int:
        val = _safe_int(self._data.get("execution_timeout", DEFAULT_EXECUTION_TIMEOUT), DEFAULT_EXECUTION_TIMEOUT)
        return max(5, min(300, val))

    @execution_timeout.setter
    def execution_timeout(self, value: int) -> None:
        self._data["execution_timeout"] = max(5, min(300, value))

    @property
    def external_editor_path(self) -> str:
        return str(self._data.get("external_editor_path", "notepad++.exe"))

    @external_editor_path.setter
    def external_editor_path(self, value: str) -> None:
        self._data["external_editor_path"] = value

    @property
    def external_editor_enabled(self) -> bool:
        return bool(self._data.get("external_editor_enabled", True))

    @external_editor_enabled.setter
    def external_editor_enabled(self, value: bool) -> None:
        self._data["external_editor_enabled"] = value
