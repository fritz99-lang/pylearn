# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""SQLite database manager with persistent connection and context manager support."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Generator

from pylearn.core.constants import DB_PATH


class Database:
    """SQLite database for tracking progress, bookmarks, notes, and saved code.

    Opens a persistent connection on construction. Use as a context manager
    or call close() explicitly when done::

        with Database() as db:
            db.upsert_book(...)

        # or
        db = Database()
        try:
            db.upsert_book(...)
        finally:
            db.close()
    """

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Open a persistent connection and configure it once
        self._conn = sqlite3.connect(str(self.db_path), timeout=10)
        self._conn.row_factory = sqlite3.Row
        # WAL mode is persistent and handles crash recovery automatically --
        # if the app crashes mid-write, SQLite replays the WAL on next open.
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")

        self._init_db()

    def __enter__(self) -> Database:
        return self

    def __exit__(self, exc_type: type | None, exc_val: BaseException | None,
                 exc_tb: object) -> None:
        self.close()

    def close(self) -> None:
        """Close the persistent database connection."""
        if self._conn:
            self._conn.close()

    def _init_db(self) -> None:
        with self._transaction() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """Yield the persistent connection, committing on success or rolling back on error."""
        try:
            yield self._conn
            self._conn.commit()
        except sqlite3.Error:
            self._conn.rollback()
            raise

    # --- Books ---

    def upsert_book(self, book_id: str, title: str, pdf_path: str,
                    total_pages: int, total_chapters: int) -> None:
        with self._transaction() as conn:
            conn.execute(
                """INSERT INTO books (book_id, title, pdf_path, total_pages, total_chapters)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(book_id) DO UPDATE SET
                       title=excluded.title, pdf_path=excluded.pdf_path,
                       total_pages=excluded.total_pages, total_chapters=excluded.total_chapters""",
                (book_id, title, pdf_path, total_pages, total_chapters),
            )

    def get_books(self) -> list[dict]:
        with self._transaction() as conn:
            rows = conn.execute("SELECT * FROM books").fetchall()
            return [dict(r) for r in rows]

    # --- Chapters ---

    def upsert_chapter(self, book_id: str, chapter_num: int, title: str,
                       start_page: int, end_page: int) -> None:
        with self._transaction() as conn:
            conn.execute(
                """INSERT INTO chapters (book_id, chapter_num, title, start_page, end_page)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(book_id, chapter_num) DO UPDATE SET
                       title=excluded.title, start_page=excluded.start_page,
                       end_page=excluded.end_page""",
                (book_id, chapter_num, title, start_page, end_page),
            )

    def upsert_chapters_batch(self, book_id: str,
                              chapters: list[tuple[int, str, int, int]]) -> None:
        """Batch-upsert multiple chapters in a single transaction.

        Args:
            book_id: The book these chapters belong to.
            chapters: List of (chapter_num, title, start_page, end_page) tuples.
        """
        with self._transaction() as conn:
            conn.executemany(
                """INSERT INTO chapters (book_id, chapter_num, title, start_page, end_page)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(book_id, chapter_num) DO UPDATE SET
                       title=excluded.title, start_page=excluded.start_page,
                       end_page=excluded.end_page""",
                [(book_id, ch_num, title, start, end)
                 for ch_num, title, start, end in chapters],
            )

    def get_chapters(self, book_id: str) -> list[dict]:
        with self._transaction() as conn:
            rows = conn.execute(
                "SELECT * FROM chapters WHERE book_id = ? ORDER BY chapter_num",
                (book_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    # --- Reading Progress ---

    def get_reading_progress(self, book_id: str, chapter_num: int) -> dict | None:
        with self._transaction() as conn:
            row = conn.execute(
                "SELECT * FROM reading_progress WHERE book_id = ? AND chapter_num = ?",
                (book_id, chapter_num),
            ).fetchone()
            return dict(row) if row else None

    def update_reading_progress(self, book_id: str, chapter_num: int,
                                status: str, scroll_position: int = 0) -> None:
        now = datetime.now().isoformat()
        with self._transaction() as conn:
            conn.execute(
                """INSERT INTO reading_progress (book_id, chapter_num, status, scroll_position, updated_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(book_id, chapter_num) DO UPDATE SET
                       status=excluded.status, scroll_position=excluded.scroll_position,
                       updated_at=excluded.updated_at""",
                (book_id, chapter_num, status, scroll_position, now),
            )

    def get_all_progress(self, book_id: str) -> list[dict]:
        with self._transaction() as conn:
            rows = conn.execute(
                "SELECT * FROM reading_progress WHERE book_id = ? ORDER BY chapter_num",
                (book_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_completion_stats(self, book_id: str) -> dict:
        """Get chapter completion statistics for a book.

        Uses a single query with conditional aggregation instead of three
        separate COUNT queries.
        """
        with self._transaction() as conn:
            row = conn.execute(
                """SELECT
                       COALESCE(c.total, 0) AS total,
                       COALESCE(rp.completed, 0) AS completed,
                       COALESCE(rp.in_progress, 0) AS in_progress
                   FROM
                       (SELECT COUNT(*) AS total FROM chapters WHERE book_id = ?) c,
                       (SELECT
                            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed,
                            SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) AS in_progress
                        FROM reading_progress WHERE book_id = ?) rp""",
                (book_id, book_id),
            ).fetchone()
            total = row[0] if row else 0
            completed = row[1] if row else 0
            in_progress = row[2] if row else 0
            return {
                "total": total,
                "completed": completed,
                "in_progress": in_progress,
                "not_started": total - completed - in_progress,
                "percent": round(completed / total * 100) if total > 0 else 0,
            }

    # --- Last Position ---

    def save_last_position(self, book_id: str, chapter_num: int,
                           scroll_position: int) -> None:
        with self._transaction() as conn:
            conn.execute(
                """INSERT INTO last_position (book_id, chapter_num, scroll_position, updated_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(book_id) DO UPDATE SET
                       chapter_num=excluded.chapter_num,
                       scroll_position=excluded.scroll_position,
                       updated_at=excluded.updated_at""",
                (book_id, chapter_num, scroll_position, datetime.now().isoformat()),
            )

    def get_last_position(self, book_id: str) -> dict | None:
        with self._transaction() as conn:
            row = conn.execute(
                "SELECT * FROM last_position WHERE book_id = ?", (book_id,)
            ).fetchone()
            return dict(row) if row else None

    # --- Bookmarks ---

    def add_bookmark(self, book_id: str, chapter_num: int,
                     scroll_position: int, label: str) -> int:
        with self._transaction() as conn:
            cursor = conn.execute(
                """INSERT INTO bookmarks (book_id, chapter_num, scroll_position, label, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (book_id, chapter_num, scroll_position, label, datetime.now().isoformat()),
            )
            return cursor.lastrowid or 0

    def get_bookmarks(self, book_id: str | None = None) -> list[dict]:
        with self._transaction() as conn:
            if book_id:
                rows = conn.execute(
                    "SELECT * FROM bookmarks WHERE book_id = ? ORDER BY created_at DESC",
                    (book_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM bookmarks ORDER BY created_at DESC"
                ).fetchall()
            return [dict(r) for r in rows]

    def delete_bookmark(self, bookmark_id: int) -> None:
        with self._transaction() as conn:
            conn.execute("DELETE FROM bookmarks WHERE bookmark_id = ?", (bookmark_id,))

    # --- Notes ---

    def add_note(self, book_id: str, chapter_num: int,
                 section_title: str, content: str) -> int:
        now = datetime.now().isoformat()
        with self._transaction() as conn:
            cursor = conn.execute(
                """INSERT INTO notes (book_id, chapter_num, section_title, content, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (book_id, chapter_num, section_title, content, now, now),
            )
            return cursor.lastrowid or 0

    def update_note(self, note_id: int, content: str) -> None:
        with self._transaction() as conn:
            conn.execute(
                "UPDATE notes SET content = ?, updated_at = ? WHERE note_id = ?",
                (content, datetime.now().isoformat(), note_id),
            )

    def get_notes(self, book_id: str | None = None, chapter_num: int | None = None) -> list[dict]:
        with self._transaction() as conn:
            if book_id and chapter_num is not None:
                rows = conn.execute(
                    "SELECT * FROM notes WHERE book_id = ? AND chapter_num = ? ORDER BY created_at DESC",
                    (book_id, chapter_num),
                ).fetchall()
            elif book_id:
                rows = conn.execute(
                    "SELECT * FROM notes WHERE book_id = ? ORDER BY created_at DESC",
                    (book_id,),
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM notes ORDER BY created_at DESC").fetchall()
            return [dict(r) for r in rows]

    def delete_note(self, note_id: int) -> None:
        with self._transaction() as conn:
            conn.execute("DELETE FROM notes WHERE note_id = ?", (note_id,))

    # --- Exercises ---

    def upsert_exercise(self, exercise_id: str, book_id: str, chapter_num: int,
                        title: str, description: str, exercise_type: str,
                        answer: str | None = None) -> None:
        with self._transaction() as conn:
            conn.execute(
                """INSERT INTO exercises (exercise_id, book_id, chapter_num, title, description, exercise_type, answer)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(exercise_id) DO UPDATE SET
                       title=excluded.title, description=excluded.description,
                       exercise_type=excluded.exercise_type, answer=excluded.answer""",
                (exercise_id, book_id, chapter_num, title, description, exercise_type, answer),
            )

    def get_exercises(self, book_id: str, chapter_num: int | None = None) -> list[dict]:
        with self._transaction() as conn:
            if chapter_num is not None:
                rows = conn.execute(
                    "SELECT * FROM exercises WHERE book_id = ? AND chapter_num = ? ORDER BY exercise_id",
                    (book_id, chapter_num),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM exercises WHERE book_id = ? ORDER BY chapter_num, exercise_id",
                    (book_id,),
                ).fetchall()
            return [dict(r) for r in rows]

    def get_exercise(self, exercise_id: str) -> dict | None:
        """Fetch a single exercise by its ID.

        Args:
            exercise_id: The unique exercise identifier.

        Returns:
            Exercise dict, or None if not found.
        """
        with self._transaction() as conn:
            row = conn.execute(
                "SELECT * FROM exercises WHERE exercise_id = ?", (exercise_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_exercise_completion_count(self, book_id: str) -> tuple[int, int]:
        """Return (completed, total) exercise counts for a book.

        Uses a single LEFT JOIN query instead of N+1 individual lookups.

        Args:
            book_id: The book to count exercises for.

        Returns:
            Tuple of (completed_count, total_count).
        """
        with self._transaction() as conn:
            row = conn.execute(
                """SELECT
                       COUNT(*) AS total,
                       SUM(CASE WHEN ep.completed = 1 THEN 1 ELSE 0 END) AS completed
                   FROM exercises e
                   LEFT JOIN exercise_progress ep ON e.exercise_id = ep.exercise_id
                   WHERE e.book_id = ?""",
                (book_id,),
            ).fetchone()
            total = row[0] if row else 0
            completed = row[1] if row else 0
            return (completed, total)

    def update_exercise_progress(self, exercise_id: str, completed: bool,
                                 user_code: str = "") -> None:
        now = datetime.now().isoformat()
        with self._transaction() as conn:
            conn.execute(
                """INSERT INTO exercise_progress (exercise_id, completed, user_code, attempts, updated_at)
                   VALUES (?, ?, ?, 1, ?)
                   ON CONFLICT(exercise_id) DO UPDATE SET
                       completed=excluded.completed, user_code=excluded.user_code,
                       attempts=exercise_progress.attempts + 1, updated_at=excluded.updated_at""",
                (exercise_id, completed, user_code, now),
            )

    def get_exercise_progress(self, exercise_id: str) -> dict | None:
        with self._transaction() as conn:
            row = conn.execute(
                "SELECT * FROM exercise_progress WHERE exercise_id = ?", (exercise_id,)
            ).fetchone()
            return dict(row) if row else None

    # --- Saved Code ---

    def save_code(self, book_id: str, chapter_num: int, code: str,
                  label: str = "") -> int:
        with self._transaction() as conn:
            cursor = conn.execute(
                """INSERT INTO saved_code (book_id, chapter_num, code, label, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (book_id, chapter_num, code, label, datetime.now().isoformat()),
            )
            return cursor.lastrowid or 0

    def get_saved_code(self, book_id: str, chapter_num: int | None = None) -> list[dict]:
        with self._transaction() as conn:
            if chapter_num is not None:
                rows = conn.execute(
                    "SELECT * FROM saved_code WHERE book_id = ? AND chapter_num = ? ORDER BY created_at DESC",
                    (book_id, chapter_num),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM saved_code WHERE book_id = ? ORDER BY created_at DESC",
                    (book_id,),
                ).fetchall()
            return [dict(r) for r in rows]

    def delete_saved_code(self, code_id: int) -> None:
        with self._transaction() as conn:
            conn.execute("DELETE FROM saved_code WHERE code_id = ?", (code_id,))


SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    book_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    pdf_path TEXT NOT NULL,
    total_pages INTEGER DEFAULT 0,
    total_chapters INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS chapters (
    book_id TEXT NOT NULL,
    chapter_num INTEGER NOT NULL,
    title TEXT NOT NULL,
    start_page INTEGER NOT NULL,
    end_page INTEGER NOT NULL,
    PRIMARY KEY (book_id, chapter_num),
    FOREIGN KEY (book_id) REFERENCES books(book_id)
);

CREATE TABLE IF NOT EXISTS reading_progress (
    book_id TEXT NOT NULL,
    chapter_num INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'not_started',
    scroll_position INTEGER DEFAULT 0,
    updated_at TEXT,
    PRIMARY KEY (book_id, chapter_num),
    FOREIGN KEY (book_id) REFERENCES books(book_id)
);

CREATE TABLE IF NOT EXISTS last_position (
    book_id TEXT PRIMARY KEY,
    chapter_num INTEGER NOT NULL,
    scroll_position INTEGER DEFAULT 0,
    updated_at TEXT,
    FOREIGN KEY (book_id) REFERENCES books(book_id)
);

CREATE TABLE IF NOT EXISTS bookmarks (
    bookmark_id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id TEXT NOT NULL,
    chapter_num INTEGER NOT NULL,
    scroll_position INTEGER DEFAULT 0,
    label TEXT NOT NULL,
    created_at TEXT,
    FOREIGN KEY (book_id) REFERENCES books(book_id)
);

CREATE TABLE IF NOT EXISTS notes (
    note_id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id TEXT NOT NULL,
    chapter_num INTEGER NOT NULL,
    section_title TEXT DEFAULT '',
    content TEXT NOT NULL,
    created_at TEXT,
    updated_at TEXT,
    FOREIGN KEY (book_id) REFERENCES books(book_id)
);

CREATE TABLE IF NOT EXISTS exercises (
    exercise_id TEXT PRIMARY KEY,
    book_id TEXT NOT NULL,
    chapter_num INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    exercise_type TEXT NOT NULL,
    answer TEXT,
    FOREIGN KEY (book_id) REFERENCES books(book_id)
);

CREATE TABLE IF NOT EXISTS exercise_progress (
    exercise_id TEXT PRIMARY KEY,
    completed BOOLEAN DEFAULT 0,
    user_code TEXT DEFAULT '',
    attempts INTEGER DEFAULT 0,
    updated_at TEXT,
    FOREIGN KEY (exercise_id) REFERENCES exercises(exercise_id)
);

CREATE TABLE IF NOT EXISTS saved_code (
    code_id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id TEXT NOT NULL,
    chapter_num INTEGER NOT NULL,
    code TEXT NOT NULL,
    label TEXT DEFAULT '',
    created_at TEXT,
    FOREIGN KEY (book_id) REFERENCES books(book_id)
);

CREATE INDEX IF NOT EXISTS idx_bookmarks_book ON bookmarks(book_id);
CREATE INDEX IF NOT EXISTS idx_notes_book ON notes(book_id, chapter_num);
CREATE INDEX IF NOT EXISTS idx_exercises_book ON exercises(book_id, chapter_num);
CREATE INDEX IF NOT EXISTS idx_exercise_progress_exercise ON exercise_progress(exercise_id);
CREATE INDEX IF NOT EXISTS idx_saved_code_book ON saved_code(book_id, chapter_num);
CREATE INDEX IF NOT EXISTS idx_reading_progress_book ON reading_progress(book_id);
"""
