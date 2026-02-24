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
from pylearn.core.models import Book
from pylearn.parser.book_profiles import PROFILES, get_auto_profile, get_profile
from pylearn.parser.cache_manager import CacheManager
from pylearn.parser.code_extractor import CodeExtractor
from pylearn.parser.content_classifier import ContentClassifier
from pylearn.parser.exercise_extractor import ExerciseExtractor
from pylearn.parser.pdf_parser import PDFParser
from pylearn.parser.structure_detector import StructureDetector
from pylearn.utils.error_handler import setup_logging


def parse_book(book_info: dict) -> Book | None:
    book_id = book_info["book_id"]
    pdf_path = book_info["pdf_path"]
    profile_name = book_info.get("profile_name", "")
    language = book_info.get("language", "")
    if not language:
        # Migrate: derive language from named profile if available
        if profile_name and profile_name in PROFILES:
            language = PROFILES[profile_name].language
        else:
            language = "python"
    title = book_info["title"]

    if not Path(pdf_path).exists():
        print(f"  ERROR: PDF not found at {pdf_path}")
        return None

    # Dual-path: use named profile if it exists, otherwise auto-detect
    if profile_name and profile_name in PROFILES:
        profile = get_profile(profile_name)
        print(f"  Using named profile: {profile_name}")
    else:
        print("  Auto-detecting font thresholds...")
        profile = get_auto_profile(pdf_path, language)
        print(
            f"  Detected: body={profile.body_size}, code={profile.code_size}, "
            f"h1>={profile.heading1_min_size}, h2>={profile.heading2_min_size}, "
            f"h3>={profile.heading3_min_size}"
        )
        print(f"  Margins: top={profile.margin_top:.0f}, bottom={profile.margin_bottom:.0f}")
        print(f"  Skip pages: start={profile.skip_pages_start}, end={profile.skip_pages_end}")

    cache = CacheManager()
    image_dir = cache.image_dir(book_id)

    print(f"  Opening PDF ({pdf_path})...")

    start = time.time()
    with PDFParser(pdf_path, profile) as parser:
        total_pages = parser.total_pages
        print(f"  Total pages: {total_pages}")

        print("  Extracting text...")
        all_page_spans = parser.extract_all()

        print("  Extracting images...")
        page_images: dict[int, list[dict]] = {}
        start_pg = profile.skip_pages_start
        end_pg = total_pages - profile.skip_pages_end
        for pg in range(start_pg, end_pg):
            imgs = parser.extract_page_images(pg, image_dir)
            if imgs:
                page_images[pg] = imgs
        img_count = sum(len(v) for v in page_images.values())
        print(f"  {img_count} images extracted from {len(page_images)} pages")

    print(f"  Extracted {sum(len(p) for p in all_page_spans)} spans from {len(all_page_spans)} pages")

    print("  Classifying content...")
    classifier = ContentClassifier(profile)
    blocks = classifier.classify_all_pages(
        all_page_spans,
        start_page_offset=profile.skip_pages_start,
        page_images=page_images if page_images else None,
    )
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
    exercises = ex_extractor.extract_from_chapters(book_id, chapters)
    print(f"  {len(exercises)} exercises found")

    book = Book(
        book_id=book_id,
        title=title,
        pdf_path=pdf_path,
        profile_name=profile_name,
        language=language,
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
