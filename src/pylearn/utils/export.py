# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Export notes, bookmarks, and learning progress to Markdown format."""

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


def export_progress_to_markdown(db: Database, book_id: str | None = None) -> str | None:
    """Export learning progress (reading, quizzes, challenges, project) to Markdown.

    Args:
        db: Database instance to query.
        book_id: If given, export only this book. If None, export all books.

    Returns:
        Formatted Markdown string, or None if there are no books.
    """
    books = db.get_books()
    if book_id:
        books = [b for b in books if b["book_id"] == book_id]

    if not books:
        return None

    today = datetime.now().strftime("%Y-%m-%d")
    sections: list[str] = []

    for b in books:
        bid = b["book_id"]
        title = b["title"]

        parts: list[str] = [
            f"# {title} — Learning Progress",
            f"*Exported from PyLearn on {today}*",
            "",
            "---",
        ]

        # --- Reading Progress ---
        completion = db.get_completion_stats(bid)
        parts.append("")
        parts.append("## Reading Progress")
        parts.append("")
        pct = completion["percent"]
        bar = _progress_bar(pct)
        parts.append(f"{bar} **{pct}%**")
        parts.append("")
        parts.append(f"- **Completed:** {completion['completed']} / {completion['total']} chapters")
        parts.append(f"- **In Progress:** {completion['in_progress']}")
        parts.append(f"- **Not Started:** {completion['not_started']}")

        # --- Quiz Scores ---
        quiz_stats = db.get_quiz_stats(bid)
        if quiz_stats["total"] > 0:
            parts.append("")
            parts.append("---")
            parts.append("")
            parts.append("## Quiz Scores")
            parts.append("")
            parts.append(
                f"**Overall:** {quiz_stats['correct']}/{quiz_stats['total']} correct"
                f" ({_pct(quiz_stats['correct'], quiz_stats['total'])}%)"
            )

            # Per-chapter breakdown
            chapters = db.get_chapters(bid)
            ch_titles = {c["chapter_num"]: c["title"] for c in chapters}

            ch_rows: list[tuple[int, dict]] = []
            for ch_num in sorted(ch_titles.keys()):
                ch_stat = db.get_quiz_stats(bid, ch_num)
                if ch_stat["total"] > 0:
                    ch_rows.append((ch_num, ch_stat))

            if ch_rows:
                parts.append("")
                parts.append("| Chapter | Score | Result |")
                parts.append("|---------|-------|--------|")
                for ch_num, ch_stat in ch_rows:
                    ch_title = ch_titles.get(ch_num, f"Chapter {ch_num}")
                    score = f"{ch_stat['correct']}/{ch_stat['total']}"
                    pct_ch = _pct(ch_stat["correct"], ch_stat["total"])
                    result = _score_emoji(pct_ch)
                    parts.append(f"| Ch {ch_num}: {ch_title} | {score} | {result} |")

        # --- Challenge Progress ---
        challenge_stats = db.get_challenge_stats(bid)
        if challenge_stats["total"] > 0:
            parts.append("")
            parts.append("---")
            parts.append("")
            parts.append("## Code Challenges")
            parts.append("")
            parts.append(
                f"**Passed:** {challenge_stats['passed']}/{challenge_stats['total']}"
                f" ({_pct(challenge_stats['passed'], challenge_stats['total'])}%)"
            )

        # --- Project Progress ---
        project_stats = db.get_project_stats(bid)
        if project_stats["total"] > 0:
            parts.append("")
            parts.append("---")
            parts.append("")
            parts.append("## Book Project")
            parts.append("")
            parts.append(f"**Steps Completed:** {project_stats['completed']}/{project_stats['total']}")

        # --- Exercise Completion ---
        completed_ex, total_ex = db.get_exercise_completion_count(bid)
        if total_ex > 0:
            parts.append("")
            parts.append("---")
            parts.append("")
            parts.append("## Exercises")
            parts.append("")
            parts.append(f"**Completed:** {completed_ex}/{total_ex} ({_pct(completed_ex, total_ex)}%)")

        sections.append("\n".join(parts))

    if not sections:
        return None

    return "\n\n".join(sections) + "\n"


def _progress_bar(percent: int, width: int = 20) -> str:
    """Render a text progress bar like [████████░░░░░░░░░░░░]."""
    filled = round(width * percent / 100)
    empty = width - filled
    return f"[{'█' * filled}{'░' * empty}]"


def _pct(numerator: int, denominator: int) -> int:
    """Calculate percentage, safe for zero denominator."""
    if denominator == 0:
        return 0
    return round(numerator * 100 / denominator)


def _score_emoji(pct: int) -> str:
    """Return a text indicator for a score percentage."""
    if pct == 100:
        return "Perfect"
    if pct >= 80:
        return "Great"
    if pct >= 60:
        return "Good"
    return "Needs Review"
