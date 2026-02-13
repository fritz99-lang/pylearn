# PyLearn - Interactive Python Learning App

## Project Overview
Desktop app for learning Python from O'Reilly PDF books. Split-pane UI: book reader (left) + code editor/console (right).

## Tech Stack
- **UI:** PyQt6 + QScintilla (code editor)
- **PDF Parsing:** PyMuPDF (fitz) for text extraction with font metadata
- **Syntax Highlighting:** Pygments for reader panel code blocks
- **Database:** SQLite for progress tracking, bookmarks, notes
- **Python:** 3.13

## Key Architecture
- `src/pylearn/` — all source code
- `src/pylearn/parser/` — PDF → structured content (cached to JSON)
- `src/pylearn/renderer/` — content blocks → styled HTML
- `src/pylearn/executor/` — subprocess-based code execution
- `src/pylearn/ui/` — PyQt6 widgets
- `config/` — JSON config files
- `data/` — SQLite DB + parsed PDF cache

## Running
```bash
python -m pylearn
```

## Commands
- `python scripts/analyze_pdf_fonts.py <path.pdf>` — dump font info from a PDF
- `python scripts/parse_books.py` — pre-parse all registered books to cache

## Key Patterns
- PDF parsing uses font metadata (size, flags) to classify content (headings, body, code)
- Each book has a profile in `book_profiles.py` with font thresholds
- Parsed content cached as JSON — parse once, load fast
- Code execution via subprocess with 30s timeout
- Context manager pattern for database access
