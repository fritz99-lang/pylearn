"""SQLite database manager with context manager pattern."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Generator, Optional

from pylearn.core.constants import DB_PATH, STATUS_NOT_STARTED


class Database:
    """SQLite database for tracking progress, bookmarks, notes, and saved code."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        # WAL mode is persistent and handles crash recovery automatically —
        # if the app crashes mid-write, SQLite replays the WAL on next open.
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except sqlite3.Error:
            conn.rollback()
            raise
        finally:
            conn.close()

    # --- Books ---

    def upsert_book(self, book_id: str, title: str, pdf_path: str,
                    total_pages: int, total_chapters: int) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO books (book_id, title, pdf_path, total_pages, total_chapters)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(book_id) DO UPDATE SET
                       title=excluded.title, pdf_path=excluded.pdf_path,
                       total_pages=excluded.total_pages, total_chapters=excluded.total_chapters""",
                (book_id, title, pdf_path, total_pages, total_chapters),
            )

    def get_books(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM books").fetchall()
            return [dict(r) for r in rows]

    # --- Chapters ---

    def upsert_chapter(self, book_id: str, chapter_num: int, title: str,
                       start_page: int, end_page: int) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO chapters (book_id, chapter_num, title, start_page, end_page)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(book_id, chapter_num) DO UPDATE SET
                       title=excluded.title, start_page=excluded.start_page,
                       end_page=excluded.end_page""",
                (book_id, chapter_num, title, start_page, end_page),
            )

    def get_chapters(self, book_id: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM chapters WHERE book_id = ? ORDER BY chapter_num",
                (book_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    # --- Reading Progress ---

    def get_reading_progress(self, book_id: str, chapter_num: int) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM reading_progress WHERE book_id = ? AND chapter_num = ?",
                (book_id, chapter_num),
            ).fetchone()
            return dict(row) if row else None

    def update_reading_progress(self, book_id: str, chapter_num: int,
                                status: str, scroll_position: int = 0) -> None:
        now = datetime.now().isoformat()
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO reading_progress (book_id, chapter_num, status, scroll_position, updated_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(book_id, chapter_num) DO UPDATE SET
                       status=excluded.status, scroll_position=excluded.scroll_position,
                       updated_at=excluded.updated_at""",
                (book_id, chapter_num, status, scroll_position, now),
            )

    def get_all_progress(self, book_id: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM reading_progress WHERE book_id = ? ORDER BY chapter_num",
                (book_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_completion_stats(self, book_id: str) -> dict:
        with self._connect() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM chapters WHERE book_id = ?", (book_id,)
            ).fetchone()[0]
            completed = conn.execute(
                "SELECT COUNT(*) FROM reading_progress WHERE book_id = ? AND status = 'completed'",
                (book_id,),
            ).fetchone()[0]
            in_progress = conn.execute(
                "SELECT COUNT(*) FROM reading_progress WHERE book_id = ? AND status = 'in_progress'",
                (book_id,),
            ).fetchone()[0]
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
        with self._connect() as conn:
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
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM last_position WHERE book_id = ?", (book_id,)
            ).fetchone()
            return dict(row) if row else None

    # --- Bookmarks ---

    def add_bookmark(self, book_id: str, chapter_num: int,
                     scroll_position: int, label: str) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """INSERT INTO bookmarks (book_id, chapter_num, scroll_position, label, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (book_id, chapter_num, scroll_position, label, datetime.now().isoformat()),
            )
            return cursor.lastrowid or 0

    def get_bookmarks(self, book_id: str | None = None) -> list[dict]:
        with self._connect() as conn:
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
        with self._connect() as conn:
            conn.execute("DELETE FROM bookmarks WHERE bookmark_id = ?", (bookmark_id,))

    # --- Notes ---

    def add_note(self, book_id: str, chapter_num: int,
                 section_title: str, content: str) -> int:
        now = datetime.now().isoformat()
        with self._connect() as conn:
            cursor = conn.execute(
                """INSERT INTO notes (book_id, chapter_num, section_title, content, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (book_id, chapter_num, section_title, content, now, now),
            )
            return cursor.lastrowid or 0

    def update_note(self, note_id: int, content: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE notes SET content = ?, updated_at = ? WHERE note_id = ?",
                (content, datetime.now().isoformat(), note_id),
            )

    def get_notes(self, book_id: str | None = None, chapter_num: int | None = None) -> list[dict]:
        with self._connect() as conn:
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
        with self._connect() as conn:
            conn.execute("DELETE FROM notes WHERE note_id = ?", (note_id,))

    # --- Exercises ---

    def upsert_exercise(self, exercise_id: str, book_id: str, chapter_num: int,
                        title: str, description: str, exercise_type: str,
                        answer: str | None = None) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO exercises (exercise_id, book_id, chapter_num, title, description, exercise_type, answer)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(exercise_id) DO UPDATE SET
                       title=excluded.title, description=excluded.description,
                       exercise_type=excluded.exercise_type, answer=excluded.answer""",
                (exercise_id, book_id, chapter_num, title, description, exercise_type, answer),
            )

    def get_exercises(self, book_id: str, chapter_num: int | None = None) -> list[dict]:
        with self._connect() as conn:
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

    def update_exercise_progress(self, exercise_id: str, completed: bool,
                                 user_code: str = "") -> None:
        now = datetime.now().isoformat()
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO exercise_progress (exercise_id, completed, user_code, attempts, updated_at)
                   VALUES (?, ?, ?, 1, ?)
                   ON CONFLICT(exercise_id) DO UPDATE SET
                       completed=excluded.completed, user_code=excluded.user_code,
                       attempts=exercise_progress.attempts + 1, updated_at=excluded.updated_at""",
                (exercise_id, completed, user_code, now),
            )

    def get_exercise_progress(self, exercise_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM exercise_progress WHERE exercise_id = ?", (exercise_id,)
            ).fetchone()
            return dict(row) if row else None

    # --- Saved Code ---

    def save_code(self, book_id: str, chapter_num: int, code: str,
                  label: str = "") -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """INSERT INTO saved_code (book_id, chapter_num, code, label, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (book_id, chapter_num, code, label, datetime.now().isoformat()),
            )
            return cursor.lastrowid or 0

    def get_saved_code(self, book_id: str, chapter_num: int | None = None) -> list[dict]:
        with self._connect() as conn:
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
        with self._connect() as conn:
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
"""
