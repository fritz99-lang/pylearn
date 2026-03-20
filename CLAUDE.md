# PyLearn - Interactive Python Learning App

**Version:** Latest
**Last Updated:** 2026-03-20
**Context Status:** Token-optimized (~8KB)

---

## Quick Start

**What:** Desktop app for learning from technical PDF books. Split-pane UI: book reader (left) + code editor/console (right). Supports Python, C++, HTML, and CSS. 6 books, multiple project choices per book.

**How to run:**
```bash
python -m pylearn
```

**Current state:** v1.1.0 with full learning features, 1136 tests pass ✅, mypy clean, CI green

---

## Project Status

| Metric | Status |
|--------|--------|
| Tests | 1136 pass, 85% coverage ✅ |
| Type Checking | mypy clean (0 errors, 52 files) ✅ |
| Supported Books | 6 books: Python (2), C++, HTML, CSS, HTML+CSS ✅ |
| Themes | Light, dark, sepia ✅ |
| UI | PyQt6 + QScintilla ✅ |
| CI | GitHub Actions (Python 3.12+3.13) ✅ |
| Builds | Windows, macOS, Linux via PyInstaller ✅ |
| Quizzes | 1078 questions across 6 books (130 chapters) ✅ |
| Code Challenges | 323 challenges across 6 books (130 chapters) ✅ |
| Book Projects | 13 projects, 128 steps total (multi-project selector) ✅ |
| Spaced Repetition | Review missed quiz questions (Ctrl+R) ✅ |
| Progress Export | File > Export Progress to markdown ✅ |
| Overall Grade | 0-100% weighted score on Progress Dashboard ✅ |

---

## Core Vision

Interactive learning environment that pairs technical PDF books with live code execution. Users read code examples, modify them, run them, and track progress all in one app. Includes chapter quizzes, code challenges, and book-spanning projects. Supports Python (subprocess), C++ (g++/clang++), and HTML/CSS (browser preview).

---

## Technical Stack

- **UI:** PyQt6 + QScintilla (syntax highlighting)
- **PDF Parsing:** PyMuPDF (fitz) with font metadata for structure recognition
- **Rendering:** Pygments for code highlighting
- **Database:** SQLite (progress, bookmarks, notes, quiz/challenge/project progress)
- **Execution:** Subprocess-based with 30s timeout (cross-platform)
- **Learning Content:** JSON files in `content/` directory (quizzes, challenges, project steps)
- **Test Runner:** Wraps assert statements for per-test pass/fail in challenges/project
- **Type Checking:** mypy (strict mode)
- **CI:** GitHub Actions (3.12+3.13)
- **Builds:** PyInstaller (Windows .exe, macOS .app, Linux binary)
- **Python:** 3.12+ minimum

---

## Quick Commands

```bash
# Run the app
python -m pylearn

# Run tests
pytest tests/ -v

# Fast tests (skip slow)
pytest tests/ -m "not slow"

# Type check
mypy src/pylearn/

# Analyze PDF fonts
python scripts/analyze_pdf_fonts.py <path.pdf>

# Pre-parse books to cache
python scripts/parse_books.py

# Build standalone executable
python scripts/build_exe.py

# Generate macOS icon (requires Pillow)
python scripts/generate_icns.py

# Validate quiz content
python scripts/generate_quizzes.py --book <book_id> --validate

# List chapters with quiz status
python scripts/generate_quizzes.py --book <book_id> --list
```

See shell aliases: `pylearn-*`

---

## Project Structure

```
PyLearn/
├── CLAUDE.md
├── README.md
├── src/pylearn/
│   ├── core/            # Models, database, config, content_loader
│   ├── parser/          # PDF → structured content
│   ├── renderer/        # Content → styled HTML
│   ├── executor/        # Subprocess code execution + test_runner
│   ├── ui/              # PyQt6 widgets (quiz_panel, challenge_panel, project_panel)
│   └── book_profiles.py # Font thresholds per book
├── content/             # Learning content (JSON, committed)
│   ├── learning_python_fifth_edition/   # 298q, 63c, 2 projects
│   ├── programming_python_fourth_edition/ # 120q, 40c, 6 projects
│   ├── gaddis_c++_starting/             # 120q, 40c, 3 projects
│   ├── html5_notes_for_professionals/   # 192q, 64c, 1 project
│   ├── css_notes_for_professionals/     # 282q, 94c, 1 project
│   └── how_to_code_in_html5_and_css3/   # 66q, 22c, 1 project
├── tests/
│   ├── unit/            # 800+ unit tests
│   └── integration/     # 330+ integration tests
├── scripts/
│   ├── analyze_pdf_fonts.py
│   ├── parse_books.py
│   ├── build_exe.py         # PyInstaller build helper
│   ├── generate_icns.py     # .ico → .icns for macOS
│   └── generate_quizzes.py  # Quiz content validation/listing
├── data/                # SQLite DB + PDF cache (not committed)
├── config/              # User config (not committed)
└── docs/
    ├── SESSION_HISTORY.md
    ├── SESSION_HANDOFF.md
    └── CODE_PATTERNS.md
```

---

## Key Patterns

- **PDF Parsing:** Font metadata (size, flags) classifies content (headings, body, code)
- **Book Profiles:** `book_profiles.py` defines font thresholds per book type
- **Caching:** Parse once → JSON cache → fast loads
- **Code Execution:** Subprocess with 30s timeout, cross-platform `CREATE_NO_WINDOW`
- **Database Access:** Context manager pattern for SQLite connections
- **Builds:** `pylearn.spec` with platform conditionals; macOS BUNDLE for `.app`. Content JSON bundled via `datas`; PDFs are NOT bundled (user-supplied)
- **Learning Content:** JSON files in `content/{book_id}/` — loaded by `ContentLoader`. In frozen (exe) mode, resolved from `sys._MEIPASS` bundle path
- **Test Runner:** Concatenates user code + assert statements, wraps each in try/except for individual pass/fail
- **Right Panel Tabs:** Editor | Quiz | Challenge | Project — all theme-aware

---

## Important Notes

- **Font-based structure:** PDF parsing relies on font metadata, not OCR
- **Hardening complete:** 49 fixes shipped, project production-ready
- **Cross-platform:** Works on Windows, macOS, Linux (tested via CI)
- **Type safety:** Strict mypy on core code, relaxed on PyQt6 UI (PyQt6 lacks stubs)

---

## References

- Full architecture: `docs/ARCHITECTURE.md` (if exists)
- Code patterns: `docs/CODE_PATTERNS.md`
- Session notes: `docs/SESSION_HANDOFF.md`
- Issue history: GitHub Issues

---

## Keyboard Shortcuts (Learning Features)

- `Ctrl+Q` — Take quiz for current chapter
- `Ctrl+R` — Review missed quiz questions (spaced repetition)
- `Ctrl+Shift+Q` — Code challenge for current chapter
- `Ctrl+P` — Open book project

---

**Updated Session 118 — Fixed PyInstaller build: bundled content/ directory in pylearn.spec, added frozen-mode content path resolution in content_loader.py. Exe build tested and verified working (quizzes, challenges, projects all load). PDFs configured separately via books.json in %LOCALAPPDATA%\pylearn\config\.**
