# PyLearn TODO

## Completed
- [x] Initial implementation (PDF reader, code editor, executor)
- [x] HTML/CSS lexer theming + Notepad++ external editor
- [x] Security hardening (49 fixes across all modules)
- [x] 167 unit tests covering parser, models, config, database, text utils
- [x] mypy strict type checking (0 errors across 46 source files)
- [x] 47 integration tests (parser pipeline, executor lifecycle, config/DB round-trips)
- [x] GitHub Actions CI (Python 3.12+3.13 test matrix + mypy typecheck)
- [x] Cross-platform subprocess constant fix for Linux CI
- [x] `.gitignore` cleanup — `data/`, `config/*.json`, `*.spec`, build artifacts now ignored
- [x] Copyright headers on all 46 source files (MIT)
- [x] MIT LICENSE file added
- [x] `config/*.json.example` defaults created, user-specific configs un-tracked
- [x] README.md (initial version) with install/usage/dev docs
- [x] `pyproject.toml` updated with license, author, Python 3.12+ requirement
- [x] State persistence verified — window geometry, last book, chapter position, scroll, splitters, TOC, theme all saved/restored

## Bugs — Must Fix Before Release
- [ ] **Add Note crash** — `notes_dialog.py:48` uses `QWidget()` but doesn't import it → `NameError` → silent crash
- [ ] **No global exception handler** — unhandled exceptions in Qt slots silently kill the app (no error dialog, no user feedback)
- [ ] **No `try/except` in UI slot methods** — none of the menu action handlers in `main_window.py` have error handling

## Next Up — Before Release
- [ ] Fix the Add Note crash (add `QWidget` to notes_dialog.py imports)
- [ ] Add global `sys.excepthook` in `app.py` that shows an error dialog instead of silent crash
- [ ] Add try/except wrappers to critical UI slot methods (dialog openers, file operations)
- [ ] Add tests for NotesDialog, BookmarkDialog, and other untested UI dialogs
- [ ] Test all menu bar actions work end-to-end (Add Note, Add Bookmark, Exercises, Search, Progress, etc.)
- [ ] Write user manual (separate from README — walkthrough of features, screenshots, tips)
- [ ] Improve README.md for open-source release:
  - [ ] Add screenshots (main UI, dark theme, TOC sidebar, console output)
  - [ ] Add badges (CI status, license, Python version, mypy)
  - [ ] Add quick start walkthrough (first-run experience)
  - [ ] Add keyboard shortcuts table
  - [ ] Add troubleshooting / FAQ section
  - [ ] Add platform-specific install notes (Linux PyQt6 deps, macOS Xcode tools)
  - [ ] Add contributing guidelines (or CONTRIBUTING.md)
  - [ ] Update GitHub URL placeholder from `your-username`
- [ ] Publish to PyPI (or at minimum, document `pip install -e .` workflow)

## Enhancements (Nice to Have)
- [ ] Search within book content (full-text search across chapters)
- [ ] Export notes/bookmarks to Markdown
- [ ] Auto-detect book profile from PDF font statistics (partially implemented in `font_analyzer.py`)
- [ ] Dark mode for editor panel (QScintilla theming to match reader dark theme)
- [ ] Test coverage report (add `pytest-cov` to dev deps)
- [ ] Pre-commit hooks (ruff, mypy)
- [ ] Custom book profile creation guide (docs/)

## Known Issues (Resolved)
- [x] `config/*.json` files tracked in git with user-specific data → now gitignored with `*.json.example` defaults
- [x] `=1.8.0` junk file in repo root → deleted
