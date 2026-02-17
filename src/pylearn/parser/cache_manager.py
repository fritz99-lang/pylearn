# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Cache parsed book content to JSON for fast loading."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from pylearn.core.constants import CACHE_DIR
from pylearn.core.models import Book

logger = logging.getLogger("pylearn.parser")


def sanitize_book_id(book_id: str) -> str:
    """Sanitize book_id to prevent path traversal — alphanumeric + underscore only."""
    return re.sub(r"[^a-z0-9_]", "", book_id.lower())[:60]


class CacheManager:
    """Manage JSON cache files for parsed book content."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, book_id: str) -> Path:
        return self.cache_dir / f"{sanitize_book_id(book_id)}.json"

    def image_dir(self, book_id: str) -> Path:
        """Return (and create) the image cache directory for a book."""
        d = self.cache_dir / f"{sanitize_book_id(book_id)}_images"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def has_cache(self, book_id: str) -> bool:
        return self._cache_path(book_id).exists()

    def save(self, book: Book) -> None:
        """Save parsed book to JSON cache (atomic write-then-rename)."""
        path = self._cache_path(book.book_id)
        data = book.to_dict()
        tmp = path.with_suffix(".tmp")
        try:
            tmp.write_text(
                json.dumps(data, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8",
            )
            tmp.replace(path)
        finally:
            tmp.unlink(missing_ok=True)
        logger.info(f"Cached {book.book_id} to {path} ({path.stat().st_size / 1024:.0f} KB)")

    def load(self, book_id: str) -> Book | None:
        """Load parsed book from JSON cache."""
        path = self._cache_path(book_id)
        if not path.exists():
            logger.info(f"No cache found for {book_id}")
            return None

        try:
            if path.stat().st_size > 200 * 1024 * 1024:
                logger.warning("Cache file too large, skipping: %s", path)
                return None

            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            book = Book.from_dict(data)
            logger.info(f"Loaded {book_id} from cache ({len(book.chapters)} chapters)")
            return book
        except Exception as e:
            logger.error(f"Error loading cache for {book_id}: {e}", exc_info=True)
            return None

    def invalidate(self, book_id: str) -> None:
        """Delete cache for a book."""
        path = self._cache_path(book_id)
        if path.exists():
            path.unlink()
            logger.info(f"Invalidated cache for {book_id}")

    def invalidate_all(self) -> None:
        """Delete all cached data."""
        for path in self.cache_dir.glob("*.json"):
            try:
                path.unlink()
            except OSError as e:
                logger.warning("Could not delete cache file %s: %s", path, e)
        logger.info("Invalidated all caches")

    def get_cache_info(self) -> list[dict]:
        """Get info about cached books."""
        info = []
        for path in self.cache_dir.glob("*.json"):
            st = path.stat()
            info.append({
                "book_id": path.stem,
                "size_kb": round(st.st_size / 1024),
                "modified": st.st_mtime,
            })
        return info
