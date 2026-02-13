"""CLI script: pre-parse all registered books to cache.

Usage: python scripts/parse_books.py [--book BOOK_ID]
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pylearn.core.config import BooksConfig
from pylearn.parser.book_profiles import get_profile
from pylearn.parser.pdf_parser import PDFParser
from pylearn.parser.content_classifier import ContentClassifier
from pylearn.parser.code_extractor import CodeExtractor
from pylearn.parser.structure_detector import StructureDetector
from pylearn.parser.exercise_extractor import ExerciseExtractor
from pylearn.parser.cache_manager import CacheManager
from pylearn.core.models import Book
from pylearn.utils.error_handler import setup_logging


def parse_book(book_info: dict) -> Book | None:
    book_id = book_info["book_id"]
    pdf_path = book_info["pdf_path"]
    profile_name = book_info["profile_name"]
    title = book_info["title"]

    if not Path(pdf_path).exists():
        print(f"  ERROR: PDF not found at {pdf_path}")
        return None

    profile = get_profile(profile_name)
    print(f"  Opening PDF ({pdf_path})...")

    start = time.time()
    parser = PDFParser(pdf_path, profile)
    parser.open()
    total_pages = parser.total_pages
    print(f"  Total pages: {total_pages}")

    print("  Extracting text...")
    all_page_spans = parser.extract_all()
    parser.close()
    print(f"  Extracted {sum(len(p) for p in all_page_spans)} spans from {len(all_page_spans)} pages")

    print("  Classifying content...")
    classifier = ContentClassifier(profile)
    blocks = classifier.classify_all_pages(all_page_spans, start_page_offset=profile.skip_pages_start)
    print(f"  {len(blocks)} content blocks")

    print("  Processing code blocks...")
    extractor = CodeExtractor()
    blocks = extractor.process(blocks)
    code_blocks = [b for b in blocks if b.block_type.value.startswith("code")]
    print(f"  {len(code_blocks)} code blocks found")

    print("  Detecting structure...")
    detector = StructureDetector(profile)
    chapters = detector.detect_chapters(blocks)
    print(f"  {len(chapters)} chapters detected")

    print("  Extracting exercises...")
    ex_extractor = ExerciseExtractor()
    exercises = ex_extractor.extract_from_chapters(book_id, chapters, profile_name)
    print(f"  {len(exercises)} exercises found")

    book = Book(
        book_id=book_id,
        title=title,
        pdf_path=pdf_path,
        profile_name=profile_name,
        total_pages=total_pages,
        chapters=chapters,
    )

    elapsed = time.time() - start
    print(f"  Parsed in {elapsed:.1f}s")

    return book


def main() -> None:
    setup_logging()
    config = BooksConfig()
    cache = CacheManager()

    # Filter by --book flag
    target_book = None
    if "--book" in sys.argv:
        idx = sys.argv.index("--book")
        if idx + 1 < len(sys.argv):
            target_book = sys.argv[idx + 1]

    books = config.books
    if target_book:
        books = [b for b in books if b["book_id"] == target_book]

    if not books:
        print("No books registered. Add books via the app or edit config/books.json")
        return

    for book_info in books:
        print(f"\nParsing: {book_info['title']}")

        if cache.has_cache(book_info["book_id"]) and "--force" not in sys.argv:
            print("  Already cached (use --force to re-parse)")
            continue

        book = parse_book(book_info)
        if book:
            cache.save(book)
            print(f"  Cached to data/cache/{book.book_id}.json")

    print("\nDone!")


if __name__ == "__main__":
    main()
