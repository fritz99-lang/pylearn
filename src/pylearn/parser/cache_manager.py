"""Cache parsed book content to JSON for fast loading."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pylearn.core.constants import CACHE_DIR
from pylearn.core.models import Book

logger = logging.getLogger("pylearn.parser")


class CacheManager:
    """Manage JSON cache files for parsed book content."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, book_id: str) -> Path:
        return self.cache_dir / f"{book_id}.json"

    def has_cache(self, book_id: str) -> bool:
        return self._cache_path(book_id).exists()

    def save(self, book: Book) -> None:
        """Save parsed book to JSON cache."""
        path = self._cache_path(book.book_id)
        data = book.to_dict()
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=1),
            encoding="utf-8",
        )
        logger.info(f"Cached {book.book_id} to {path} ({path.stat().st_size / 1024:.0f} KB)")

    def load(self, book_id: str) -> Book | None:
        """Load parsed book from JSON cache."""
        path = self._cache_path(book_id)
        if not path.exists():
            logger.info(f"No cache found for {book_id}")
            return None

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            book = Book.from_dict(data)
            logger.info(f"Loaded {book_id} from cache ({len(book.chapters)} chapters)")
            return book
        except Exception as e:
            logger.error(f"Error loading cache for {book_id}: {e}")
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
            path.unlink()
        logger.info("Invalidated all caches")

    def get_cache_info(self) -> list[dict]:
        """Get info about cached books."""
        info = []
        for path in self.cache_dir.glob("*.json"):
            info.append({
                "book_id": path.stem,
                "size_kb": round(path.stat().st_size / 1024),
                "modified": path.stat().st_mtime,
            })
        return info
