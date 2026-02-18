# PyLearn TODO

## Completed
- [x] Initial implementation (PDF reader, code editor, executor)
- [x] HTML/CSS lexer theming + Notepad++ external editor
- [x] Security hardening (49 fixes across all modules)
- [x] mypy strict type checking (0 errors across 46 source files)
- [x] GitHub Actions CI (Python 3.12+3.13 test matrix + mypy typecheck)
- [x] Cross-platform subprocess constant fix for Linux CI
- [x] `.gitignore` cleanup — `data/`, `config/*.json`, `*.spec`, build artifacts now ignored
- [x] Copyright headers on all 46 source files (MIT)
- [x] MIT LICENSE file added
- [x] `config/*.json.example` defaults created, user-specific configs un-tracked
- [x] README.md with install/usage/dev docs, GitHub URL fixed, pip-install-from-git option
- [x] `pyproject.toml` updated with license, author, Python 3.12+ requirement
- [x] State persistence verified — window geometry, last book, chapter position, scroll, splitters, TOC, theme all saved/restored
- [x] **Add Note crash fixed** — added `QWidget` to notes_dialog.py imports
- [x] **Global exception handler** — `sys.excepthook` shows error dialog instead of silent crash
- [x] **`@safe_slot` on all 38 UI slot methods** — exceptions caught, logged, and shown to user
- [x] **ParseProcess error handling** — try/except in QProcess signal handlers
- [x] User manual drafted (`docs/user-manual.md`)
- [x] GitHub URL updated from placeholder to `fritz99-lang`
- [x] Install-from-git documented in README
- [x] **Comprehensive 5-audit code review** — security, performance, error handling, code quality, test coverage
- [x] **Security fixes** — CSP on HTML preview, path traversal validation, color param validation, sanitize_book_id at creation, guarded mkdir, improved atomic writes
- [x] **Performance overhaul** — persistent DB connection, N+1 queries eliminated, batch upserts, DB indexes, str.translate(), HtmlFormatter singleton, is_monospace caching, compact JSON cache
- [x] **Code cleanup** — dead imports removed, magic strings replaced with constants, duplicated code extracted, type hints fixed
- [x] **702 tests** (334 → 702) covering renderer, output handler, error handler, security, exercise extractor, font analyzer, book controller, executor edge cases
- [x] README polish — badges, keyboard shortcuts, troubleshooting/FAQ, platform notes, acknowledgments
- [x] CLAUDE.md test counts updated
- [x] LICENSE updated to Nathan Tritle

## Before Release
- [x] Screenshots — 4 screenshots (light, dark, sepia, code execution) in `docs/screenshots/`, linked in README
- [x] Manual testing pass — found and fixed: Ctrl+N crash, F5 shortcut, console colors, blue font readability
- [ ] PyPI publish — `python -m build` then `twine upload dist/*` (name "pylearn" is available, account exists)
- [ ] GitHub Release — `git tag v1.0.0`, push tag, create release with notes

## Nice-to-Have Before Release
- [ ] CONTRIBUTING.md — short guide if you want outside contributions
- [ ] PyInstaller standalone `.exe` — bundle for users without Python installed

## Enhancements (Post-Release)
- [ ] Search within book content (full-text search across chapters)
- [ ] Export notes/bookmarks to Markdown
- [ ] Dark mode for editor panel (QScintilla theming to match reader dark theme)
- [ ] Test coverage report (add `pytest-cov` to dev deps)
- [ ] Pre-commit hooks (ruff, mypy)
- [ ] Custom book profile creation guide (docs/)
- [ ] Welcome screen respects dark/sepia theme colors
- [ ] PyInstaller builds for macOS and Linux
