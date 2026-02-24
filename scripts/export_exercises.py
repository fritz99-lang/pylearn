"""Export exercises from cached books to markdown.

Usage: python scripts/export_exercises.py [--book BOOK_ID] [--output FILE]
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pylearn.core.config import BooksConfig
from pylearn.parser.cache_manager import CacheManager
from pylearn.parser.exercise_extractor import ExerciseExtractor


def main() -> None:
    config = BooksConfig()
    cache = CacheManager()

    target_book = None
    output_path = None

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--book" and i + 1 < len(args):
            target_book = args[i + 1]
            i += 2
        elif args[i] == "--output" and i + 1 < len(args):
            output_path = args[i + 1]
            i += 2
        else:
            i += 1

    books_to_process = config.books
    if target_book:
        books_to_process = [b for b in books_to_process if b["book_id"] == target_book]

    lines: list[str] = ["# PyLearn - Exercises\n"]
    extractor = ExerciseExtractor()

    for book_info in books_to_process:
        book = cache.load(book_info["book_id"])
        if not book:
            print(f"No cache for {book_info['book_id']}, skipping")
            continue

        exercises = extractor.extract_from_chapters(book.book_id, book.chapters, book_info["profile_name"])

        if not exercises:
            continue

        lines.append(f"\n## {book.title}\n")
        current_chapter = -1

        for ex in exercises:
            if ex.chapter_num != current_chapter:
                current_chapter = ex.chapter_num
                lines.append(f"\n### Chapter {current_chapter}\n")

            lines.append(f"#### {ex.title}\n")
            lines.append(f"{ex.description}\n")
            if ex.answer:
                lines.append(f"\n<details><summary>Answer</summary>\n\n{ex.answer}\n\n</details>\n")
            lines.append("")

    content = "\n".join(lines)

    if output_path:
        Path(output_path).write_text(content, encoding="utf-8")
        print(f"Exported to {output_path}")
    else:
        print(content)


if __name__ == "__main__":
    main()
