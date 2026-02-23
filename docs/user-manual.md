# PyLearn User Manual

**Version 1.0** | Last updated: February 2026

---

## Table of Contents

1. [Getting Started](#1-getting-started)
   - [What is PyLearn?](#what-is-pylearn)
   - [Installing on Windows](#installing-on-windows)
   - [Installing on Mac or Linux](#installing-on-mac-or-linux)
   - [First-Time Setup](#first-time-setup)
   - [Launching the App](#launching-the-app)
2. [The Interface](#2-the-interface)
   - [Overview](#overview)
   - [Table of Contents Sidebar](#table-of-contents-sidebar)
   - [Toolbar](#toolbar)
   - [Status Bar](#status-bar)
3. [Reading Books](#3-reading-books)
   - [Navigating Chapters](#navigating-chapters)
   - [Finding Text in a Chapter](#finding-text-in-a-chapter)
   - [Searching Across All Books](#searching-across-all-books)
   - [Changing Themes](#changing-themes)
   - [Adjusting Font Size](#adjusting-font-size)
4. [Writing and Running Code](#4-writing-and-running-code)
   - [Loading Code from the Book](#loading-code-from-the-book)
   - [Writing Your Own Code](#writing-your-own-code)
   - [Running Code](#running-code)
   - [Stopping Long-Running Code](#stopping-long-running-code)
   - [Resetting the Session](#resetting-the-session)
   - [Opening Code in an External Editor](#opening-code-in-an-external-editor)
   - [Saving and Loading Code Files](#saving-and-loading-code-files)
5. [Tracking Your Progress](#5-tracking-your-progress)
   - [How Progress Tracking Works](#how-progress-tracking-works)
   - [Marking a Chapter Complete](#marking-a-chapter-complete)
   - [Viewing the Progress Overview](#viewing-the-progress-overview)
   - [Bookmarks](#bookmarks)
   - [Notes](#notes)
6. [Adding New Books](#6-adding-new-books)
   - [Registering a Book](#registering-a-book)
   - [Available Book Profiles](#available-book-profiles)
   - [Parsing a Book for the First Time](#parsing-a-book-for-the-first-time)
   - [Re-Parsing a Book](#re-parsing-a-book)
   - [Using the Font Analyzer Script](#using-the-font-analyzer-script)
7. [Configuration Reference](#7-configuration-reference)
   - [app_config.json](#app_configjson)
   - [editor_config.json](#editor_configjson)
   - [books.json](#booksjson)
8. [Keyboard Shortcuts](#8-keyboard-shortcuts)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Getting Started

### What is PyLearn?

PyLearn is a desktop app for learning programming from PDF books. Instead of juggling a PDF reader and a code editor in separate windows, PyLearn combines them into a single split-pane interface:

- The **left side** shows the book, formatted for easy reading with syntax-highlighted code blocks.
- The **right side** has a code editor on top and a console on the bottom, so you can write code and see the output without leaving the app.

PyLearn works with O'Reilly-style programming books in PDF format. It parses the PDF once, converts it into structured content, and caches the result so subsequent loads are fast.

[screenshot: main interface showing book on left, editor and console on right]

---

### Installing on Windows

You will need Python 3.12 or newer. You can check your version by opening a Command Prompt and running:

```
python --version
```

If Python is not installed, download it from [python.org](https://www.python.org/downloads/).

**Step-by-step installation:**

- [ ] **Step 1 — Download PyLearn.**
  Open a Command Prompt. Navigate to the folder where you want to install PyLearn, for example your Documents folder:
  ```
  cd %USERPROFILE%\Documents
  ```
  Then clone the repository:
  ```
  git clone https://github.com/fritz99-lang/pylearn.git
  cd pylearn
  ```
  If you don't have Git installed, you can [download it from git-scm.com](https://git-scm.com/download/win) or download PyLearn as a ZIP from GitHub and extract it.

- [ ] **Step 2 — Create a virtual environment.**
  This keeps PyLearn's dependencies separate from other Python projects on your machine:
  ```
  python -m venv .venv
  ```

- [ ] **Step 3 — Activate the virtual environment.**
  ```
  .venv\Scripts\activate
  ```
  Your Command Prompt prompt should now show `(.venv)` at the start.

- [ ] **Step 4 — Install PyLearn and its dependencies.**
  ```
  pip install -e .
  ```
  This step installs PyQt6, PyMuPDF, QScintilla, Pygments, and other required packages. It may take a minute or two.

- [ ] **Step 5 — Copy the example config files.**
  ```
  copy config\app_config.json.example config\app_config.json
  copy config\books.json.example config\books.json
  copy config\editor_config.json.example config\editor_config.json
  ```

You are now ready to register your first book. See [First-Time Setup](#first-time-setup) below.

---

### Installing on Mac or Linux

You will need Python 3.12 or newer. Check your version in a terminal:

```
python3 --version
```

**Linux note:** PyQt6 requires some system libraries. On Ubuntu/Debian, install them first:
```
sudo apt install python3-dev libgl1-mesa-glx libglib2.0-0
```
On Fedora/RHEL:
```
sudo dnf install python3-devel mesa-libGL glib2
```

**macOS note:** You may need Xcode command-line tools. Install them with:
```
xcode-select --install
```

**Step-by-step installation:**

- [ ] **Step 1 — Download PyLearn.**
  ```
  git clone https://github.com/fritz99-lang/pylearn.git
  cd pylearn
  ```

- [ ] **Step 2 — Create a virtual environment.**
  ```
  python3 -m venv .venv
  ```

- [ ] **Step 3 — Activate the virtual environment.**
  ```
  source .venv/bin/activate
  ```
  Your terminal prompt should now show `(.venv)`.

- [ ] **Step 4 — Install PyLearn and its dependencies.**
  ```
  pip install -e .
  ```

- [ ] **Step 5 — Copy the example config files.**
  ```
  cp config/app_config.json.example config/app_config.json
  cp config/books.json.example config/books.json
  cp config/editor_config.json.example config/editor_config.json
  ```

---

### First-Time Setup

Before launching PyLearn, you need to register at least one PDF book. Open `config/books.json` in any text editor (Notepad on Windows, TextEdit on Mac, or any code editor).

You will see a placeholder entry:

```json
{
  "books": [
    {
      "book_id": "example_book",
      "title": "Example Book Title",
      "pdf_path": "/path/to/your/book.pdf",
      "profile_name": "learning_python"
    }
  ]
}
```

Replace this with your actual book information:

- `book_id` — a short, unique identifier with no spaces (e.g., `learning_python`, `my_cpp_book`). You will use this to identify the book internally.
- `title` — the display name that appears in the app.
- `pdf_path` — the full path to your PDF file on disk.
  - Windows example: `C:\\Users\\YourName\\Documents\\LearningPython.pdf`
  - Mac/Linux example: `/home/yourname/books/LearningPython.pdf`
  - Note: On Windows, use double backslashes (`\\`) or forward slashes (`/`) in JSON paths.
- `profile_name` — the parsing profile to use. See [Available Book Profiles](#available-book-profiles) for options.

**Example for a Python book:**

```json
{
  "books": [
    {
      "book_id": "learning_python",
      "title": "Learning Python",
      "pdf_path": "C:/Users/YourName/Documents/LearningPython5E.pdf",
      "profile_name": "learning_python"
    }
  ]
}
```

Save the file. You are ready to launch.

---

### Launching the App

Make sure your virtual environment is active (you should see `(.venv)` in your terminal), then run:

```
python -m pylearn
```

**Windows shortcut:** If you want to launch without activating the virtual environment each time, you can run:
```
.venv\Scripts\python -m pylearn
```

The first time you open a book, PyLearn will offer to parse the PDF. This can take a few minutes depending on the size of the book. Subsequent loads are fast because the parsed content is cached.

---

## 2. The Interface

### Overview

PyLearn's window is divided into three main areas:

```
+------------------+---------------------------+
|                  |                           |
|  TOC Sidebar     |   Book Reader             |
|  (chapter list)  |   (formatted content)     |
|                  |                           |
+------------------+----------+----------------+
                   |          |
                   |  Code    |   Code         |
                   |  Editor  |   Console      |
                   |          |                |
                   +----------+----------------+
```

- **TOC Sidebar (far left)** — The table of contents. Click any chapter or section to jump to it.
- **Book Reader (center-left)** — Displays the book content with formatted headings, body text, and syntax-highlighted code blocks.
- **Code Editor (center-right, top)** — Where you write and edit code. Supports syntax highlighting, line numbers, and auto-indent.
- **Console (center-right, bottom)** — Shows the output from running your code.

You can resize any panel by dragging the dividers between them. PyLearn saves your layout preferences when you close the app.

[screenshot: annotated main interface with panel labels]

---

### Table of Contents Sidebar

The TOC sidebar lists all chapters and, within each chapter, the major sections. The sidebar is 220 pixels wide by default.

- **Click a chapter** to jump directly to it.
- **Click a section heading** within a chapter to scroll the reader to that section.
- Chapters are color-coded by status:
  - No indicator — not started
  - Partial indicator — in progress (you have visited this chapter)
  - Checkmark or full indicator — completed (you marked it done)
- **Toggle the sidebar** with `Ctrl+T` or via the View menu. This gives the reader panel more space when you need it.

[screenshot: TOC sidebar showing chapter list with status indicators]

---

### Toolbar

The toolbar runs across the top of the window and provides quick access to the most common actions:

| Button | What it does |
|--------|-------------|
| Run (play icon) | Runs the code in the editor (same as F5) |
| Stop (stop icon) | Stops running code (same as Shift+F5) |
| Clear Console | Clears the console output |
| Font size control | Increases or decreases the reader and editor font size |
| Theme selector | Switches between Light, Dark, and Sepia themes |
| External Editor button | Opens the current code in Notepad++ or your configured editor |

[screenshot: toolbar with buttons labeled]

---

### Status Bar

The status bar at the bottom of the window shows four pieces of information from left to right:

- **Book** — The title of the currently open book (e.g., "Book: Learning Python")
- **Chapter** — Your current position (e.g., "Chapter 3 of 41")
- **Progress** — Your overall completion percentage (e.g., "42% complete")
- **State** — What the app is doing right now ("Ready", "Running...", "Parsing...", etc.)

---

## 3. Reading Books

### Navigating Chapters

There are three ways to move between chapters:

1. **Click in the TOC sidebar** — Click any chapter name to jump to it directly.
2. **Keyboard shortcuts** — Press `Alt+Left` for the previous chapter, `Alt+Right` for the next.
3. **Book menu** — Use Book > Previous Chapter or Book > Next Chapter.

When you navigate to a chapter, PyLearn automatically marks it as "in progress." Your reading position (including scroll position) is saved when you close the app or switch books, so you can pick up exactly where you left off.

---

### Finding Text in a Chapter

To search for text within the current chapter:

1. Press `Ctrl+F` (or use Search > Find in Chapter).
2. An inline find bar appears at the top of the reader panel.
3. Type your search term. Matches are highlighted as you type.
4. Press `Enter` to move to the next match, `Shift+Enter` to go back.
5. Press `Escape` to close the find bar.

[screenshot: find bar open in reader panel with highlighted match]

---

### Searching Across All Books

To search all registered books at once:

1. Press `Ctrl+Shift+F` (or use Search > Search All Books).
2. The Search dialog opens.
3. Type your search term and press Enter.
4. Results show the book title, chapter, and a snippet of matching text.
5. Click any result to jump directly to that chapter.

[screenshot: search dialog with results]

---

### Changing Themes

PyLearn offers three themes for the reader panel:

- **Light** — White background, dark text. Good for bright rooms.
- **Dark** — Dark background, light text. Easier on the eyes in low light.
- **Sepia** — Warm cream background. A softer alternative to full light mode.

To change the theme, use the theme selector in the toolbar, or go to View > Theme. Your choice is saved and restored the next time you open the app.

[screenshot: side-by-side comparison of light and dark themes]

---

### Adjusting Font Size

To make the text larger or smaller:

- Press `Ctrl+=` to increase the font size.
- Press `Ctrl+-` to decrease the font size.
- Or use the font size control in the toolbar.
- Or go to View > Increase Font Size / Decrease Font Size.

Font size ranges from 6 to 30 for the reader, and 6 to 72 for the editor. Your setting is saved automatically.

---

## 4. Writing and Running Code

### Loading Code from the Book

Every code block in the reader panel has two small buttons in its top-right corner:

- **Copy** — Copies the code to your clipboard.
- **Try It** — Loads the code directly into the editor panel.

The "Try It" button is the fastest way to get a code example into the editor so you can run it or modify it. If the code uses interactive Python prompt format (lines starting with `>>>`), PyLearn automatically strips those prompts so the code runs cleanly.

[screenshot: code block in reader panel with Copy and Try It buttons highlighted]

---

### Writing Your Own Code

Click anywhere in the editor panel (top-right area) to start typing. The editor supports:

- **Syntax highlighting** for Python, C++, and HTML/CSS
- **Line numbers** on the left margin
- **Auto-indent** — pressing Enter after a colon (`:`) automatically indents the next line
- **Tab width** — defaults to 4 spaces

The editor language automatically matches the book you have open. When you switch to a C++ book, the editor switches to C++ syntax highlighting.

---

### Running Code

To run the code in the editor:

1. Make sure your code is in the editor panel.
2. Press `F5`, click the Run button in the toolbar, or go to Run > Run Code.
3. Output appears in the console panel below the editor.
4. The status bar shows "Running..." while code is executing.
5. When complete, "Ready" appears in the status bar.

Each run appends output to the console with a separator line, so you can compare results from multiple runs. To clear the console, click the Clear Console button in the toolbar or go to Run > Clear Console.

**Code safety:** PyLearn checks your code before running it. If it detects operations that could modify your file system or run system commands, it will warn you and ask for confirmation before proceeding.

**Language-specific behavior:**
- **Python** — Runs directly in a sandboxed Python subprocess.
- **C++** — Compiles with g++ and runs the result. Requires g++ to be installed on your system.
- **HTML/CSS** — Opens the code in your default web browser.

**Execution timeout:** By default, code is stopped after 30 seconds if it doesn't finish. See [editor_config.json](#editor_configjson) to change this.

[screenshot: console showing output after running code]

---

### Stopping Long-Running Code

If your code is taking too long or has an infinite loop:

1. Press `Shift+F5`, click the Stop button in the toolbar, or go to Run > Stop.
2. The console shows "Execution stopped by user."
3. The status bar returns to "Ready."

---

### Resetting the Session

PyLearn runs your code in a persistent session — variables you define in one run are available in the next run (similar to an interactive Python shell). This is useful when you build up code across multiple examples.

To start fresh with a clean session:

1. Go to Edit > Reset Session.
2. The console is cleared and all previously defined variables are erased.

This is helpful when you want to start a new exercise without leftover state from a previous example.

---

### Opening Code in an External Editor

If you prefer to edit code in a full-featured editor like Notepad++:

1. Click the External Editor button in the toolbar, or go to Edit > Open in External Editor (shortcut: `Ctrl+E`).
2. PyLearn saves your code to a temporary file and opens it in Notepad++ (or your configured editor).
3. Edit the file and save it in the external editor.
4. PyLearn detects your changes and automatically updates the editor panel.

To use a different editor, update the `external_editor_path` setting in `config/editor_config.json`. See [editor_config.json](#editor_configjson) for details.

To disable the external editor button entirely, set `external_editor_enabled` to `false` in `editor_config.json`.

---

### Saving and Loading Code Files

To save your code to a file on disk:

1. Press `Ctrl+S` or go to File > Save Code.
2. A file dialog opens. Choose a location and file name.
3. PyLearn defaults to the appropriate extension for your book language (`.py` for Python, `.cpp` for C++, `.html` for HTML).

To load code from a file:

1. Press `Ctrl+O` or go to File > Load Code.
2. A file dialog opens. Select your file.
3. The file contents replace the current editor contents.

Files larger than 10 MB cannot be loaded.

---

## 5. Tracking Your Progress

### How Progress Tracking Works

PyLearn tracks your progress through each book automatically. Every time you visit a chapter, it is marked as "in progress." This happens without any action from you — just reading is enough.

Progress is stored in a SQLite database at `data/pylearn.db`. Your progress persists across sessions and is never lost when you close and reopen the app.

Chapter status has three levels:

| Status | What it means |
|--------|--------------|
| Not Started | You have never opened this chapter |
| In Progress | You have visited this chapter at least once |
| Completed | You marked this chapter as done with Ctrl+M |

The TOC sidebar reflects these statuses visually so you can see at a glance where you are in the book.

---

### Marking a Chapter Complete

When you finish a chapter and feel confident in the material:

1. Press `Ctrl+M`, or go to Book > Mark Chapter Complete.
2. The chapter status updates to "Completed" in the TOC sidebar.
3. The progress percentage in the status bar updates.

You can mark a chapter complete at any time. The status does not revert automatically — only you can change it.

---

### Viewing the Progress Overview

To see a full summary of your progress across all books:

1. Go to View > Progress, or press `Ctrl+M` on the View menu.
2. The Progress dialog opens, showing a breakdown by book with chapter counts for each status level.

[screenshot: progress dialog showing completion stats]

---

### Bookmarks

Bookmarks let you save your place in a book and jump back to it later.

**Adding a bookmark:**

1. Navigate to the page you want to bookmark.
2. Press `Ctrl+B` or go to Edit > Add Bookmark.
3. A dialog appears. Enter a name for the bookmark (e.g., "Good example of list comprehension").
4. Click OK.

**Viewing and navigating bookmarks:**

1. Go to View > Bookmarks.
2. The Bookmarks dialog lists all your saved bookmarks, organized by book and chapter.
3. Click any bookmark to jump directly to that location.

[screenshot: bookmark dialog]

---

### Notes

Notes let you attach your own text to any chapter — questions, summaries, things to revisit, or anything else.

**Adding a note:**

1. Navigate to the chapter where you want to add a note.
2. Press `Ctrl+N` or go to Edit > Add Note.
3. A dialog opens, pre-filled with the current chapter title.
4. Type your note and click Save.

**Viewing, editing, and deleting notes:**

1. Go to View > Notes.
2. The Notes dialog shows all your notes, organized by book and chapter.
3. Click a note to edit it.
4. Select a note and click Delete to remove it.

[screenshot: notes dialog with example note]

---

## 6. Adding New Books

### Registering a Book

All books are registered in `config/books.json`. Open this file in a text editor and add a new entry to the `books` array:

```json
{
  "books": [
    {
      "book_id": "learning_python",
      "title": "Learning Python",
      "pdf_path": "C:/Users/YourName/Documents/LearningPython5E.pdf",
      "profile_name": "learning_python"
    },
    {
      "book_id": "cpp_primer",
      "title": "C++ Primer",
      "pdf_path": "C:/Users/YourName/Documents/CppPrimer5E.pdf",
      "profile_name": "cpp_primer"
    }
  ]
}
```

**Fields explained:**

| Field | Required | Description |
|-------|----------|-------------|
| `book_id` | Yes | Unique short identifier. No spaces. Use underscores. |
| `title` | Yes | Display name shown in the app. |
| `pdf_path` | Yes | Full absolute path to the PDF file. |
| `profile_name` | No | Parsing profile name (see below). Leave empty for auto-detect. |
| `language` | No | `"python"`, `"cpp"`, or `"html"`. Defaults to `"python"` if not set. |

Save `books.json`. The next time you launch PyLearn, your new book will appear in the book selector at the top of the window.

---

### Available Book Profiles

A book profile tells PyLearn how to read the fonts in your PDF — which font sizes are headings, which are body text, and which are code. Each O'Reilly book is formatted slightly differently, so profiles are tuned per book.

| Profile Name | Designed for |
|-------------|--------------|
| `learning_python` | Learning Python, 5th Edition (Lutz) |
| `python_cookbook` | Python Cookbook, 3rd Edition (Beazley & Jones) |
| `programming_python` | Programming Python, 4th Edition (Lutz) |
| `cpp_generic` | Generic C++ books — a good starting point |
| `cpp_primer` | C++ Primer, 5th Edition (Lippman et al.) |
| `effective_cpp` | Effective C++ (Meyers) |

If your book is not in this list, try one of these options:

1. **Leave `profile_name` empty** — PyLearn will attempt to auto-detect font thresholds from the PDF. Results vary.
2. **Use `cpp_generic`** for any C++ book as a starting point.
3. **Run the font analyzer script** and create a custom profile (see [Using the Font Analyzer Script](#using-the-font-analyzer-script)).

---

### Parsing a Book for the First Time

When you open a book that hasn't been parsed yet, PyLearn will ask:

> "[Book Title]" has not been parsed yet. Parse it now? (This may take a few minutes)

Click **Yes**. The status bar shows parsing progress while PyLearn processes the PDF in the background. The UI stays responsive during parsing.

For a large book (e.g., Learning Python at 1,500 pages), parsing typically takes 2 to 5 minutes on a modern machine. Once parsed, the book loads in under a second on every subsequent launch.

Parsed content is cached in `data/cache/`. You do not need to re-parse unless the book or its profile changes.

You can also trigger parsing manually from the menu: **Book > Parse Current Book**.

---

### Re-Parsing a Book

To clear the cache and re-parse a book (useful if you change its profile or if the content looks wrong):

1. Make sure the book you want to re-parse is selected in the book selector.
2. Go to **Book > Re-parse (clear cache)**.
3. PyLearn clears the cached data and starts parsing again.

Note: Re-parsing does not affect your progress, bookmarks, or notes — those are stored separately in the database.

---

### Using the Font Analyzer Script

If your book is not parsing correctly (wrong headings, missing code blocks, etc.), you can run the font analyzer script to inspect the PDF's font metadata. This helps you understand what font sizes the book uses for different content types.

From your terminal (with the virtual environment active):

```
python scripts/analyze_pdf_fonts.py path/to/your/book.pdf
```

The script outputs a table of fonts and sizes found in the PDF, along with their frequencies. Use this information to determine the right thresholds for a custom profile.

To create a custom profile, open `src/pylearn/parser/book_profiles.py` and add a new `BookProfile` entry modeled after the existing ones. Then reference its `name` value in your `books.json` entry.

[Note for maintainer: consider adding a guide specifically for creating custom profiles as a separate docs file.]

---

## 7. Configuration Reference

All configuration files live in the `config/` folder. They are JSON files you can edit in any text editor. PyLearn reads them at startup and saves changes automatically when you close the app.

If a config file is missing, PyLearn uses built-in defaults and will create the file on next save.

---

### app_config.json

Controls the main window layout and appearance.

| Field | Default | Description |
|-------|---------|-------------|
| `window_width` | `1400` | Window width in pixels on startup. |
| `window_height` | `900` | Window height in pixels on startup. |
| `window_x` | (unset) | Horizontal screen position. Set automatically when you move the window. |
| `window_y` | (unset) | Vertical screen position. Set automatically when you move the window. |
| `window_maximized` | `false` | If `true`, the window opens maximized. |
| `theme` | `"light"` | Starting theme. Options: `"light"`, `"dark"`, `"sepia"`. |
| `reader_font_size` | `11` | Reader panel font size in points. Valid range: 6–30. |
| `splitter_sizes` | `[700, 500]` | Pixel widths of the left and right panels. |
| `editor_console_sizes` | `[400, 400]` | Pixel heights of the editor and console panels. |
| `toc_width` | `220` | Width of the TOC sidebar in pixels. |
| `toc_visible` | `true` | Whether the TOC sidebar is shown on startup. |
| `last_book_id` | `""` | The `book_id` of the last opened book. Set automatically. |

**Example:**

```json
{
  "window_width": 1600,
  "window_height": 1000,
  "theme": "dark",
  "reader_font_size": 13,
  "toc_visible": true,
  "window_maximized": false,
  "last_book_id": "learning_python"
}
```

---

### editor_config.json

Controls the code editor and execution behavior.

| Field | Default | Description |
|-------|---------|-------------|
| `font_size` | `12` | Editor font size in points. Valid range: 6–72. |
| `tab_width` | `4` | Number of spaces per tab indent. Valid range: 1–16. |
| `show_line_numbers` | `true` | Whether to show line numbers in the editor gutter. |
| `auto_indent` | `true` | Whether the editor automatically indents new lines. |
| `word_wrap` | `false` | Whether long lines wrap in the editor. |
| `execution_timeout` | `30` | Seconds before a running program is forcibly stopped. Valid range: 5–300. |
| `external_editor_path` | `"notepad++.exe"` | Path or command name for the external editor. |
| `external_editor_enabled` | `true` | Set to `false` to hide the external editor button. |

**Example:**

```json
{
  "font_size": 14,
  "tab_width": 4,
  "show_line_numbers": true,
  "auto_indent": true,
  "word_wrap": false,
  "execution_timeout": 60,
  "external_editor_path": "notepad++.exe",
  "external_editor_enabled": true
}
```

**External editor on Mac/Linux:** Set `external_editor_path` to the full path of your editor, e.g., `"/usr/bin/code"` for VS Code or `"/usr/bin/gedit"` for Gedit.

**Increasing the timeout:** If you are working through exercises that involve processing large datasets or running simulations, consider increasing `execution_timeout` to 60 or 120 seconds.

---

### books.json

The registry of all books PyLearn knows about.

```json
{
  "books": [
    {
      "book_id": "learning_python",
      "title": "Learning Python",
      "pdf_path": "C:/Users/YourName/Documents/LearningPython5E.pdf",
      "profile_name": "learning_python",
      "language": "python"
    }
  ]
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `book_id` | Yes | Unique identifier. Must not contain spaces or special characters. Used internally as the database key and cache filename. |
| `title` | Yes | Human-readable title shown in the app's book selector. |
| `pdf_path` | Yes | Absolute path to the PDF file. The file must exist when you try to open the book. |
| `profile_name` | No | Name of the parsing profile (see [Available Book Profiles](#available-book-profiles)). Leave empty for auto-detect. |
| `language` | No | Programming language of the book. Options: `"python"`, `"cpp"`, `"html"`. Defaults to `"python"`. Affects editor syntax highlighting and how code is executed. |

You can register as many books as you like. All registered books appear in the book selector at the top of the app window.

---

## 8. Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| **Navigation** | |
| `Alt+Left` | Previous chapter |
| `Alt+Right` | Next chapter |
| `Ctrl+M` | Mark current chapter complete |
| `Ctrl+T` | Toggle the TOC sidebar |
| **Search** | |
| `Ctrl+F` | Find text in the current chapter |
| `Ctrl+Shift+F` | Search across all books |
| **Running Code** | |
| `F5` | Run code |
| `Shift+F5` | Stop running code |
| `Ctrl+S` | Save code to a file |
| `Ctrl+O` | Load code from a file |
| `Ctrl+E` | Open code in external editor |
| **View** | |
| `Ctrl+=` | Increase font size |
| `Ctrl+-` | Decrease font size |
| `Ctrl+1` | Move focus to the TOC panel |
| `Ctrl+2` | Move focus to the reader panel |
| `Ctrl+3` | Move focus to the code editor |
| **Notes and Bookmarks** | |
| `Ctrl+B` | Add a bookmark at the current position |
| `Ctrl+N` | Add a note to the current chapter |
| **Other** | |
| `Ctrl+/` | Show the keyboard shortcuts reference |
| `Alt+F4` | Exit the app (Windows) |

You can also view this reference at any time inside the app by pressing `Ctrl+/` or going to Help > Keyboard Shortcuts.

---

## 9. Troubleshooting

### App Won't Start

**Symptom:** Running `python -m pylearn` produces an error immediately.

**Check these in order:**

1. **Is the virtual environment active?** You should see `(.venv)` in your terminal prompt. If not, activate it:
   - Windows: `.venv\Scripts\activate`
   - Mac/Linux: `source .venv/bin/activate`

2. **Are dependencies installed?** Run `pip install -e .` again. If it fails with missing packages, check that you have Python 3.12+.

3. **Is the config folder correct?** PyLearn looks for config files in the `config/` directory inside the project folder. Make sure `config/app_config.json`, `config/books.json`, and `config/editor_config.json` all exist. If they are missing, copy them from the `.example` files.

4. **Check the log file.** PyLearn writes errors to `data/pylearn.log`. Open this file and look for error messages near the bottom.

---

### PDF Not Found Error

**Symptom:** You see a dialog saying "PDF Not Found: /path/to/book.pdf".

**Cause:** The path in `books.json` does not match the actual file location.

**Fix:**

1. Find your PDF file on disk and copy its full path.
2. Open `config/books.json` and update the `pdf_path` field.
3. On Windows, make sure to use either forward slashes (`/`) or double backslashes (`\\`) — a single backslash (`\`) is not valid in JSON.
4. Save `books.json` and try opening the book again.

---

### Book Doesn't Parse Correctly

**Symptom:** After parsing, the book content looks wrong — headings appear as body text, code blocks are missing, or the chapter list is incomplete.

**Common causes and fixes:**

- **Wrong profile.** Try a different `profile_name` in `books.json`, or remove it to use auto-detection.
- **Front matter included.** The book might have many pages of front matter (table of contents, copyright pages) before the actual content. Each profile has `skip_pages_start` and `skip_pages_end` settings to handle this.
- **Unusual fonts.** Your PDF might use non-standard fonts that the default profiles don't recognize. Run the font analyzer script to inspect the actual fonts used:
  ```
  python scripts/analyze_pdf_fonts.py path/to/your/book.pdf
  ```
  Use the output to create or adjust a profile in `src/pylearn/parser/book_profiles.py`.
- After changing a profile, go to **Book > Re-parse (clear cache)** to regenerate the content.

---

### Code Execution Issues

**Symptom:** Code doesn't run, produces unexpected errors, or the console stays blank.

**Check these:**

1. **Is there code in the editor?** The editor must have content before you can run it.

2. **Is Python installed and findable?** PyLearn runs your code using the Python from your virtual environment. If you see a "Python not found" error, make sure the virtual environment is active.

3. **For C++ code:** Make sure `g++` is installed and on your system PATH.
   - Windows: Install MinGW or use WSL.
   - Mac: `xcode-select --install` installs the compiler tools.
   - Linux: `sudo apt install g++` (Ubuntu/Debian) or `sudo dnf install gcc-c++` (Fedora).

4. **Did execution time out?** If your code runs for longer than the `execution_timeout` value (default 30 seconds), it is stopped automatically. Increase the timeout in `editor_config.json` if needed.

5. **REPL prompts in the editor?** If you manually pasted code that includes `>>>` Python prompt characters, the code won't run correctly. Remove the `>>>` characters, or use the "Try It" button in the reader panel — it strips them automatically.

---

### Exercises Panel Shows Nothing

**Symptom:** View > Exercises opens but shows no exercises.

**Cause:** Exercise detection depends on the book profile. Currently, exercises are only auto-detected for books with an `exercise_start_pattern` defined in their profile (Learning Python has this configured).

---

### Finding the Log File

PyLearn writes detailed log messages to:

- **Windows:** `data\pylearn.log` inside the PyLearn project folder
- **Mac/Linux:** `data/pylearn.log` inside the PyLearn project folder

Open this file in any text editor when troubleshooting. The most recent errors appear at the bottom of the file.

---

### Reporting Bugs

If you find a bug or something that doesn't work as expected:

1. Check the log file (`data/pylearn.log`) for error messages.
2. Open an issue on GitHub: [https://github.com/fritz99-lang/pylearn/issues](https://github.com/fritz99-lang/pylearn/issues)
3. Include:
   - What you were doing when the error occurred
   - The error message (from the dialog or from the log file)
   - Your operating system and Python version (`python --version`)

---

*Copyright (c) 2026 Nate Tritle. PyLearn is open source software released under the MIT License.*
