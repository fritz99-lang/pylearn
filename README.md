# PyLearn

An interactive desktop app for learning programming from PDF books. Split-pane interface with a book reader on the left and a code editor + console on the right — read the book, write code, and run it all in one place.

## Features

- **PDF Book Reader** — Parses PDF books into structured, styled HTML with headings, body text, and syntax-highlighted code blocks
- **Code Editor** — QScintilla-powered editor with syntax highlighting, line numbers, auto-indent, and configurable font/tab settings
- **Code Execution** — Run Python code directly from the editor with output displayed in an integrated console (30s timeout, sandboxed subprocess)
- **Table of Contents** — Auto-generated chapter navigation from PDF structure
- **Progress Tracking** — SQLite database tracks chapter completion status, bookmarks, and notes per book
- **Bookmarks & Notes** — Save bookmarks and attach notes to any page
- **Multiple Book Profiles** — Supports Python, C++, and HTML/CSS books with per-book font classification profiles
- **Themes** — Light, dark, and sepia themes for the reader panel
- **External Editor** — Launch code in Notepad++ or your preferred external editor
- **Parsed Content Caching** — PDF parsing results cached as JSON for fast subsequent loads

## Requirements

- Python 3.12+
- Windows, macOS, or Linux

## Installation

```bash
# Clone the repository
git clone https://github.com/your-username/pylearn.git
cd pylearn

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate    # Linux/macOS
.venv\Scripts\activate       # Windows

# Install in development mode
pip install -e ".[dev]"
```

## Setup

1. **Copy the example config files:**

   ```bash
   cp config/app_config.json.example config/app_config.json
   cp config/books.json.example config/books.json
   cp config/editor_config.json.example config/editor_config.json
   ```

2. **Register your books** by editing `config/books.json`:

   ```json
   {
     "books": [
       {
         "book_id": "learning_python",
         "title": "Learning Python",
         "pdf_path": "/path/to/your/book.pdf",
         "profile_name": "learning_python"
       }
     ]
   }
   ```

   Available `profile_name` values: `learning_python`, `cpp_generic`, or leave empty for auto-detection.

3. **Launch the app:**

   ```bash
   python -m pylearn
   ```

## Usage

| Area | What it does |
|------|-------------|
| **Left panel** | Book reader — navigate chapters via the table of contents sidebar |
| **Right panel (top)** | Code editor — write or paste code from the book |
| **Right panel (bottom)** | Console — see output from running your code |
| **Toolbar** | Theme switching, bookmarks, notes, progress tracking |

## Configuration

All config files live in `config/` and are JSON:

- **`app_config.json`** — Window size, theme, splitter positions, last opened book
- **`books.json`** — Registered books with PDF paths and profile names
- **`editor_config.json`** — Editor font size, tab width, line numbers, execution timeout

## Development

```bash
# Run all tests (214 tests)
pytest tests/ -v

# Skip slow tests
pytest tests/ -v -m "not slow"

# Type checking
mypy src/pylearn/

# Pre-parse books to cache
python scripts/parse_books.py

# Analyze PDF font metadata (useful for creating new book profiles)
python scripts/analyze_pdf_fonts.py path/to/book.pdf
```

## Project Structure

```
src/pylearn/
  parser/       PDF parsing, font analysis, content classification, caching
  renderer/     HTML rendering, syntax highlighting, themes
  executor/     Subprocess-based code execution with sandboxing
  ui/           PyQt6 widgets (main window, reader, editor, console, dialogs)
  core/         Config, database, models, constants
  utils/        Text utilities, error handling
config/         User-specific JSON config (not committed; see *.json.example)
data/           SQLite database + parsed PDF cache (not committed)
tests/          214 tests (167 unit + 47 integration)
scripts/        Utility scripts for PDF analysis and book parsing
```

## License

[MIT](LICENSE) - Copyright (c) 2026 Nate Tritle
