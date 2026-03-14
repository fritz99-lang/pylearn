#!/usr/bin/env python3
# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Generate quiz content from cached book data.

This script extracts chapter summaries from parsed book caches and outputs
them in a format suitable for creating quiz questions. It can also validate
existing quiz JSON files.

Usage:
    # List chapters for a book
    python scripts/generate_quizzes.py --book learning_python_fifth_edition --list

    # Extract chapter summary for quiz authoring
    python scripts/generate_quizzes.py --book learning_python_fifth_edition --chapter 6

    # Validate all quiz JSON files for a book
    python scripts/generate_quizzes.py --book learning_python_fifth_edition --validate
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from pylearn.core.constants import APP_DIR, CACHE_DIR  # noqa: E402
from pylearn.core.content_loader import ContentLoader  # noqa: E402
from pylearn.core.models import Book  # noqa: E402

CONTENT_DIR = APP_DIR / "content"


def list_chapters(book_id: str) -> None:
    """List all chapters in a cached book."""
    book = _load_book(book_id)
    if not book:
        return

    loader = ContentLoader(CONTENT_DIR)
    quiz_chapters = set(loader.list_quiz_chapters(book_id))

    print(f"\n{book.title} ({len(book.chapters)} chapters)")
    print("-" * 60)
    for ch in book.chapters:
        has_quiz = "  [quiz]" if ch.chapter_num in quiz_chapters else ""
        print(f"  Ch {ch.chapter_num:2d}: {ch.title}{has_quiz}")
    print()


def extract_summary(book_id: str, chapter_num: int) -> None:
    """Extract a chapter summary useful for writing quiz questions."""
    book = _load_book(book_id)
    if not book:
        return

    chapter = None
    for ch in book.chapters:
        if ch.chapter_num == chapter_num:
            chapter = ch
            break

    if not chapter:
        print(f"Chapter {chapter_num} not found in {book_id}")
        return

    print(f"\n## Chapter {chapter_num}: {chapter.title}")
    print(f"Pages {chapter.start_page}-{chapter.end_page}")
    print()

    # Extract headings
    print("### Headings:")
    for block in chapter.content_blocks:
        if block.block_type.value.startswith("heading"):
            indent = "  " * (int(block.block_type.value[-1]) - 1)
            print(f"{indent}- {block.text.strip()}")

    # Extract key concepts (body text, first ~500 chars per section)
    print("\n### Key Content Snippets:")
    current_heading = ""
    body_chars = 0
    for block in chapter.content_blocks:
        if block.block_type.value.startswith("heading"):
            current_heading = block.text.strip()
            body_chars = 0
        elif block.block_type.value == "body" and body_chars < 500:
            text = block.text.strip()
            if text and len(text) > 20:
                if body_chars == 0:
                    print(f"\n  [{current_heading}]")
                print(f"  {text[:200]}...")
                body_chars += len(text)

    # Extract code examples
    code_blocks = [b for b in chapter.content_blocks if b.block_type.value in ("code", "code_repl")]
    print(f"\n### Code Examples: {len(code_blocks)} blocks")
    for i, block in enumerate(code_blocks[:5]):
        preview = block.text.strip()[:100].replace("\n", " | ")
        print(f"  {i + 1}. {preview}")
    if len(code_blocks) > 5:
        print(f"  ... and {len(code_blocks) - 5} more")

    print()


def validate_quizzes(book_id: str) -> None:
    """Validate all quiz JSON files for a book."""
    loader = ContentLoader(CONTENT_DIR)
    chapters = loader.list_quiz_chapters(book_id)

    if not chapters:
        print(f"No quiz files found for {book_id}")
        return

    total_questions = 0
    errors = 0

    for ch_num in chapters:
        quiz = loader.load_quiz(book_id, ch_num)
        if quiz is None:
            print(f"  Ch {ch_num:2d}: FAILED to load")
            errors += 1
            continue

        n = len(quiz.questions)
        total_questions += n

        # Check for duplicate IDs
        ids = [q.question_id for q in quiz.questions]
        dupes = set(x for x in ids if ids.count(x) > 1)

        # Check MC questions have valid correct index
        mc_issues = []
        for q in quiz.questions:
            if q.question_type == "multiple_choice":
                if not isinstance(q.correct, int) or q.correct >= len(q.choices):
                    mc_issues.append(q.question_id)

        status = "OK"
        issues = []
        if dupes:
            issues.append(f"duplicate IDs: {dupes}")
        if mc_issues:
            issues.append(f"invalid correct index: {mc_issues}")
        if issues:
            status = "ISSUES: " + "; ".join(issues)
            errors += 1

        print(f"  Ch {ch_num:2d}: {n} questions - {status}")

    print(f"\nTotal: {total_questions} questions across {len(chapters)} chapters, {errors} issues")


def _load_book(book_id: str) -> Book | None:
    """Load a book from cache."""
    cache_path = CACHE_DIR / f"{book_id}.json"
    if not cache_path.exists():
        print(f"Cache not found: {cache_path}")
        print(f"Available caches: {[p.stem for p in CACHE_DIR.glob('*.json')]}")
        return None
    data = json.loads(cache_path.read_text(encoding="utf-8"))
    return Book.from_dict(data)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate and validate quiz content")
    parser.add_argument("--book", required=True, help="Book ID (e.g., learning_python_fifth_edition)")
    parser.add_argument("--list", action="store_true", help="List chapters")
    parser.add_argument("--chapter", type=int, help="Extract chapter summary")
    parser.add_argument("--validate", action="store_true", help="Validate quiz JSON files")

    args = parser.parse_args()

    if args.list:
        list_chapters(args.book)
    elif args.chapter:
        extract_summary(args.book, args.chapter)
    elif args.validate:
        validate_quizzes(args.book)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
