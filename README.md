# PyLearn

[![CI](https://github.com/fritz99-lang/pylearn/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/fritz99-lang/pylearn/actions/workflows/ci.yml)
[![Build](https://github.com/fritz99-lang/pylearn/actions/workflows/build.yml/badge.svg)](https://github.com/fritz99-lang/pylearn/actions/workflows/build.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-green.svg)](https://www.python.org/)
[![mypy](https://img.shields.io/badge/type--checked-mypy-blue.svg)](https://mypy-lang.org/)

An interactive desktop app for learning programming from PDF books. Split-pane interface with a book reader on the left and a code editor + console on the right — read the book, write code, and run it all in one place.

## Screenshots

**Light mode** — reading with Book menu open:

![Light mode](docs/screenshots/light-mode.png)

**Dark mode** — reading with code execution:

![Dark mode](docs/screenshots/dark-mode.png)

**Sepia mode** — reading view:

![Sepia mode](docs/screenshots/sepia-mode.png)

**Sepia mode** — running code (Zen of Python):

![Code execution](docs/screenshots/sepia-code-execution.png)

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

## Standalone Builds (no Python required)

Pre-built executables for Windows, macOS, and Linux are available from [GitHub Actions](https://github.com/fritz99-lang/pylearn/actions/workflows/build.yml):

1. Go to the latest successful build run
2. Download the artifact for your platform: **PyLearn-Windows**, **PyLearn-macOS**, or **PyLearn-Linux**
3. Extract and run

| Platform | Output | Notes |
|----------|--------|-------|
| Windows | `PyLearn.exe` | Run directly |
| macOS | `PyLearn.app` | May need: `xattr -cr PyLearn.app` (unsigned app) |
| Linux | `PyLearn` | `chmod +x PyLearn` then run |

## Requirements

- Python 3.12 or newer (not needed for standalone builds above)
- Windows, macOS, or Linux

### Platform Notes

| Platform | Notes |
|----------|-------|
| **Windows** | Works out of the box with Python 3.12+ |
| **Linux** | Install system deps first: `sudo apt-get install libegl1 libxkbcommon0` |
| **macOS** | May need Xcode command line tools: `xcode-select --install` |

## Installation

Pick **one** of the methods below.

### Option A: Install from PyPI (simplest)

```bash
pip install pylearn-reader
```

### Option B: Install from GitHub (latest code)

```bash
pip install git+https://github.com/fritz99-lang/pylearn.git
```

### Option C: Clone the repo (for development)

```bash
git clone https://github.com/fritz99-lang/pylearn.git
cd pylearn

# Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate    # Linux/macOS
.venv\Scripts\activate       # Windows

pip install -e .             # editable install
pip install -e ".[dev]"      # or include pytest + mypy
```

## Registering a Book

PyLearn reads PDF books, but it needs to know where your PDFs are. You do this by editing a single config file called `books.json`.

### Step 1 — Find your config directory

Where `books.json` lives depends on how you installed:

| Install method | Config location |
|----------------|-----------------|
| **Git clone** (Option C) | `config/` folder inside the repo — configs are created automatically from the `.json.example` files on first launch |
| **pip install** (Option A or B) | A `config/` folder inside your system's app-data directory (see table below) |

**App-data directory by platform** (pip installs only):

| Platform | Path |
|----------|------|
| Windows | `%LOCALAPPDATA%\pylearn\config\` (typically `C:\Users\<you>\AppData\Local\pylearn\config\`) |
| macOS | `~/Library/Application Support/pylearn/config/` |
| Linux | `~/.local/share/pylearn/config/` |

> **Tip:** Launch the app once (`python -m pylearn`) and it will create the config directory for you. Then you just need to add your `books.json` file inside it.

### Step 2 — Create (or edit) `books.json`

If the file doesn't exist yet, create it. Add one entry per book:

```json
{
  "books": [
    {
      "book_id": "learning_python",
      "title": "Learning Python, 5th Edition",
      "pdf_path": "C:/Users/you/Documents/Learning_Python.pdf",
      "language": "python",
      "profile_name": "learning_python"
    }
  ]
}
```

**Field reference:**

| Field | Required | Description |
|-------|----------|-------------|
| `book_id` | Yes | A short unique ID you make up — no spaces, lowercase with underscores (e.g. `"my_python_book"`) |
| `title` | Yes | Display name shown in the app |
| `pdf_path` | Yes | **Absolute path** to the PDF file on your computer. Use forward slashes even on Windows (`C:/Users/...`) |
| `language` | No | `"python"` (default), `"cpp"`, or `"html"` — controls syntax highlighting in the editor |
| `profile_name` | No | A named parsing profile that fine-tunes how PDF fonts are classified. Leave it as `""` (empty string) for auto-detection, which works well for most books |

**Available named profiles** (only needed if auto-detection doesn't work well for your book):

| `profile_name` | Best for |
|-----------------|----------|
| `learning_python` | *Learning Python* by Mark Lutz |
| `python_cookbook` | *Python Cookbook* by Beazley & Jones |
| `programming_python` | *Programming Python* by Mark Lutz |
| `cpp_generic` | General C++ textbooks |
| `cpp_primer` | *C++ Primer* by Lippman et al. |
| `effective_cpp` | *Effective C++* by Scott Meyers |
| *(empty string)* | Auto-detect from the PDF — **try this first** |

### Step 3 — Launch and parse

```bash
python -m pylearn
```

On first launch for each book, the app will ask if you want to parse the PDF. Click **Yes** — this takes a minute or two depending on the book size. After parsing, the book content is cached so subsequent launches are instant.

## Usage

| Area | What it does |
|------|-------------|
| **Left panel** | Book reader — navigate chapters via the table of contents sidebar |
| **Right panel (top)** | Code editor — write or paste code from the book |
| **Right panel (bottom)** | Console — see output from running your code |
| **Toolbar** | Theme switching, bookmarks, notes, progress tracking |

## Keyboard Shortcuts

| Category | Shortcut | Action |
|----------|----------|--------|
| **Navigation** | `Alt+Left` / `Alt+Right` | Previous / next chapter |
| | `Ctrl+M` | Mark chapter complete |
| | `Ctrl+T` | Toggle TOC panel |
| **Search** | `Ctrl+F` | Find in current chapter |
| | `Ctrl+Shift+F` | Search all books |
| **Code** | `F5` | Run code |
| | `Shift+F5` | Stop execution |
| | `Ctrl+S` | Save code to file |
| | `Ctrl+O` | Load code from file |
| | `Ctrl+E` | Open in external editor |
| **View** | `Ctrl+=` / `Ctrl+-` | Increase / decrease font size |
| | `Ctrl+1` / `2` / `3` | Focus TOC / reader / editor |
| **Notes** | `Ctrl+B` | Add bookmark |
| | `Ctrl+N` | Add note |
| **Help** | `Ctrl+/` | Show shortcuts dialog |

## Configuration

Config files are JSON. For git-clone installs they live in `config/` inside the repo. For pip installs they live in your app-data directory (see [Registering a Book](#registering-a-book) for the exact path).

- **`app_config.json`** — Window size, theme, splitter positions, last opened book
- **`books.json`** — Registered books with PDF paths and profile names
- **`editor_config.json`** — Editor font size, tab width, line numbers, execution timeout

## Development

```bash
# Run all tests (749 tests)
pytest tests/ -v

# Skip slow tests
pytest tests/ -v -m "not slow"

# Type checking
mypy src/pylearn/

# Pre-parse books to cache
python scripts/parse_books.py

# Analyze PDF font metadata (useful for creating new book profiles)
python scripts/analyze_pdf_fonts.py path/to/book.pdf

# Build standalone executable (requires PyInstaller)
python scripts/build_exe.py
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
tests/          749 tests (500+ unit + 150+ integration)
scripts/        Utility scripts for PDF analysis, book parsing, and builds
```

## Troubleshooting

**App won't start**
- Make sure PyQt6 is installed: `pip install PyQt6 PyQt6-QScintilla`
- Verify Python 3.12+: `python --version`
- On Linux, install system deps: `sudo apt-get install libegl1 libxkbcommon0`

**"No books registered" or no books appear**
- Make sure `books.json` exists in the correct config directory (see [Registering a Book](#registering-a-book) above)
- Open the file and check for JSON syntax errors (missing commas, unclosed braces)
- Make sure each entry has at least `book_id`, `title`, and `pdf_path`

**"PDF not found" error during parsing**
- The `pdf_path` in `books.json` must be an **absolute path** — relative paths won't work
- Use forward slashes, even on Windows: `"C:/Users/you/Documents/book.pdf"`
- Double-check the file actually exists at that path

**Book not parsing correctly**
- Try auto-detection first: set `"profile_name": ""` in your book entry
- Use **Book > Re-parse (clear cache)** from the menu bar to force a fresh parse
- If auto-detection gives poor results, try a named profile (see the profile table above)
- For dev installs: run `python scripts/analyze_pdf_fonts.py path/to/book.pdf` to inspect font metadata

**Code execution timeout**
- Default timeout is 30 seconds
- Increase it in `editor_config.json` by setting `"execution_timeout"` to a higher value (in seconds)

## Acknowledgments

Built in partnership with [Claude Code](https://claude.ai/claude-code) (Anthropic) — architecture, implementation, testing, and code review.

## License

[MIT](LICENSE) - Copyright (c) 2026 Nathan Tritle
