# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Export notes and bookmarks to Markdown format."""

from __future__ import annotations

from datetime import datetime

from pylearn.core.database import Database


def _fmt_timestamp(iso: str | None) -> str:
    """Format an ISO datetime string as 'YYYY-MM-DD at HH:MM'."""
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%Y-%m-%d at %H:%M")
    except ValueError:
        return iso


def export_to_markdown(db: Database, book_id: str | None = None) -> str | None:
    """Export notes and/or bookmarks to a formatted Markdown string.

    Args:
        db: Database instance to query.
        book_id: If given, export only this book. If None, export all books.

    Returns:
        Formatted Markdown string, or None if there are no notes or bookmarks.
    """
    books = db.get_books()
    if book_id:
        books = [b for b in books if b["book_id"] == book_id]

    if not books:
        return None

    # Build a lookup: book_id → {chapter_num → title}
    book_titles: dict[str, str] = {b["book_id"]: b["title"] for b in books}
    chapter_titles: dict[str, dict[int, str]] = {}
    for b in books:
        chapters = db.get_chapters(b["book_id"])
        chapter_titles[b["book_id"]] = {c["chapter_num"]: c["title"] for c in chapters}

    multi_book = len(books) > 1
    sections: list[str] = []
    today = datetime.now().strftime("%Y-%m-%d")

    for b in books:
        bid = b["book_id"]
        title = book_titles[bid]
        ch_titles = chapter_titles.get(bid, {})

        notes = db.get_notes(bid)
        bookmarks = db.get_bookmarks(bid)

        if not notes and not bookmarks:
            continue

        # Sort by chapter_num ASC, then created_at ASC
        notes.sort(key=lambda n: (n["chapter_num"], n.get("created_at") or ""))
        bookmarks.sort(key=lambda bm: (bm["chapter_num"], bm.get("created_at") or ""))

        book_parts: list[str] = []

        if multi_book:
            book_parts.append(f"# {title} \u2014 Notes & Bookmarks")
        else:
            book_parts.append(f"# {title} \u2014 Notes & Bookmarks")
        book_parts.append(f"*Exported from PyLearn on {today}*")
        book_parts.append("")
        book_parts.append("---")

        # --- Notes section ---
        if notes:
            book_parts.append("")
            book_parts.append("## Notes")

            current_chapter: int | None = None
            for note in notes:
                ch = note["chapter_num"]
                if ch != current_chapter:
                    current_chapter = ch
                    ch_title = ch_titles.get(ch, f"Chapter {ch}")
                    book_parts.append("")
                    book_parts.append(f"### Chapter {ch}: {ch_title}")

                section = note.get("section_title") or f"Note {note['note_id']}"
                ts = _fmt_timestamp(note.get("created_at"))
                book_parts.append("")
                book_parts.append(f"#### {section}")
                if ts:
                    book_parts.append(f"*Added {ts}*")
                book_parts.append("")
                book_parts.append(note["content"])

            book_parts.append("")
            book_parts.append("---")

        # --- Bookmarks section ---
        if bookmarks:
            book_parts.append("")
            book_parts.append("## Bookmarks")

            current_chapter = None
            for bm in bookmarks:
                ch = bm["chapter_num"]
                if ch != current_chapter:
                    current_chapter = ch
                    ch_title = ch_titles.get(ch, f"Chapter {ch}")
                    book_parts.append("")
                    book_parts.append(f"### Chapter {ch}: {ch_title}")

                label = bm["label"]
                ts = _fmt_timestamp(bm.get("created_at"))
                ts_part = f" *(added {ts})*" if ts else ""
                book_parts.append(f"- **{label}**{ts_part}")

        sections.append("\n".join(book_parts))

    if not sections:
        return None

    return "\n\n".join(sections) + "\n"
