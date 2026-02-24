# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Entry point for PyLearn application."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the src directory is in the path
src_dir = Path(__file__).resolve().parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))


def _run_parse() -> None:
    """Handle --parse flag: run book parsing without GUI.

    Exit codes:
        0  — success
        10 — config load failed
        11 — cache init failed
        12 — no matching books in config
        13 — all books failed to parse
    """
    import time

    from pylearn.utils.error_handler import setup_logging

    setup_logging()

    try:
        from pylearn.core.config import BooksConfig

        config = BooksConfig()
    except Exception as e:
        print(f"ERROR: Failed to load books config: {e}")
        print("Hint: Ensure config/books.json exists and contains valid JSON.")
        sys.exit(10)

    try:
        from pylearn.parser.cache_manager import CacheManager

        cache = CacheManager()
    except Exception as e:
        print(f"ERROR: Failed to initialize cache: {e}")
        sys.exit(11)

    from pylearn.core.models import Book
    from pylearn.parser.book_profiles import PROFILES, get_auto_profile, get_profile
    from pylearn.parser.code_extractor import CodeExtractor
    from pylearn.parser.content_classifier import ContentClassifier
    from pylearn.parser.exercise_extractor import ExerciseExtractor
    from pylearn.parser.pdf_parser import PDFParser
    from pylearn.parser.structure_detector import StructureDetector

    # Parse --book and --force flags
    target_book = None
    if "--book" in sys.argv:
        idx = sys.argv.index("--book")
        if idx + 1 < len(sys.argv):
            target_book = sys.argv[idx + 1]
    force = "--force" in sys.argv

    books = config.books
    if target_book:
        books = [b for b in books if b["book_id"] == target_book]

    if not books:
        if target_book:
            print(f"ERROR: No book with id '{target_book}' found in config.")
            print("Hint: Check config/books.json — registered book IDs are:")
            for b in config.books:
                print(f"  - {b['book_id']}: {b['title']}")
        else:
            print("ERROR: No books registered in config/books.json.")
            print("Hint: Add a book entry to config/books.json with book_id, title, and pdf_path.")
        sys.exit(12)

    success_count = 0
    for book_info in books:
        try:
            book_id = book_info["book_id"]
            print(f"\nParsing: {book_info['title']}")

            if cache.has_cache(book_id) and not force:
                print("  Already cached (use --force to re-parse)")
                success_count += 1
                continue

            pdf_path = book_info["pdf_path"]
            profile_name = book_info.get("profile_name", "")
            language = book_info.get("language", "")
            if not language:
                # Migrate: derive language from named profile if available
                if profile_name and profile_name in PROFILES:
                    language = PROFILES[profile_name].language
                else:
                    language = "python"

            if not Path(pdf_path).exists():
                print(f"  ERROR: PDF not found at {pdf_path}")
                continue

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
                print(f"  {img_count} images extracted")

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
                title=book_info["title"],
                pdf_path=pdf_path,
                profile_name=profile_name,
                language=language,
                total_pages=total_pages,
                chapters=chapters,
            )

            elapsed = time.time() - start
            print(f"  Parsed in {elapsed:.1f}s")

            cache.save(book)
            print("  Cached successfully")
            success_count += 1
        except Exception as e:
            print(f"  ERROR parsing {book_info.get('title', '?')}: {e}")
            continue

    if success_count == 0 and len(books) > 0:
        print("\nERROR: All books failed to parse.")
        sys.exit(13)

    print("\nDone!")


def main() -> None:
    """Launch the PyLearn application (or run parse subprocess)."""
    # Handle --parse flag for frozen subprocess spawning
    if "--parse" in sys.argv:
        _run_parse()
        return

    debug = "--debug" in sys.argv
    from pylearn.app import run_app

    sys.exit(run_app(debug=debug))


if __name__ == "__main__":
    main()
