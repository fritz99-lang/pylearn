# PyLearn - Interactive Python Learning App

## Project Overview
Desktop app for learning Python from O'Reilly PDF books. Split-pane UI: book reader (left) + code editor/console (right).

## Tech Stack
- **UI:** PyQt6 + QScintilla (code editor)
- **PDF Parsing:** PyMuPDF (fitz) for text extraction with font metadata
- **Syntax Highlighting:** Pygments for reader panel code blocks
- **Database:** SQLite for progress tracking, bookmarks, notes
- **Type Checking:** mypy (strict mode for non-UI, relaxed for PyQt6 UI modules)
- **CI:** GitHub Actions — tests on Python 3.12+3.13, mypy on 3.13
- **Python:** 3.12+ (tested on 3.12 and 3.13)

## Key Architecture
- `src/pylearn/` — all source code
- `src/pylearn/parser/` — PDF → structured content (cached to JSON)
- `src/pylearn/renderer/` — content blocks → styled HTML
- `src/pylearn/executor/` — subprocess-based code execution
- `src/pylearn/ui/` — PyQt6 widgets
- `config/` — JSON config files (user-specific, not committed)
- `data/` — SQLite DB + parsed PDF cache (not committed)
- `conftest.py` — shared pytest fixtures
- `tests/unit/` — 500+ unit tests
- `tests/integration/` — 150+ integration tests

## Running
```bash
python -m pylearn
```

## Commands
- `python scripts/analyze_pdf_fonts.py <path.pdf>` — dump font info from a PDF
- `python scripts/parse_books.py` — pre-parse all registered books to cache
- `pytest tests/ -v` — run all 702 tests
- `pytest tests/ -v -m "not slow"` — skip timeout tests (~5s vs ~14s)
- `mypy src/pylearn/` — type check (should be 0 errors)

## Key Patterns
- PDF parsing uses font metadata (size, flags) to classify content (headings, body, code)
- Each book has a profile in `book_profiles.py` with font thresholds
- Parsed content cached as JSON — parse once, load fast
- Code execution via subprocess with 30s timeout
- Context manager pattern for database access
- `subprocess.CREATE_NO_WINDOW` accessed via `_CREATE_NO_WINDOW` constant (cross-platform)

## Current State (Feb 2026)
- 49 hardening fixes shipped, 702 tests passing, mypy clean, CI green
- Supports Python, C++, and HTML book profiles
- Three themes: light, dark, sepia
