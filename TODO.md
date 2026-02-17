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

## Next Up — Release Prep
- [ ] Add `.gitignore` entries for `data/`, `config/*.json` (user-specific), `*.db`, `*.spec`, build artifacts
- [ ] Copyright/trademark header in source files (needed before open-source release per CLAUDE.md)
- [ ] Choose a license (MIT? Apache 2.0?) and add LICENSE file
- [ ] Write a proper README.md with screenshots, install instructions, usage guide
- [ ] Publish to PyPI (or at minimum, document `pip install -e .` workflow)

## Enhancements (Nice to Have)
- [ ] Search within book content (full-text search across chapters)
- [ ] Export notes/bookmarks to Markdown
- [ ] Auto-detect book profile from PDF font statistics (partially implemented in `font_analyzer.py`)
- [ ] Dark mode for editor panel (QScintilla theming to match reader dark theme)
- [ ] Keyboard shortcuts documentation / help dialog
- [ ] Test coverage report (add `pytest-cov` to dev deps)
- [ ] Pre-commit hooks (ruff, mypy)

## Known Issues
- [ ] `config/*.json` files are tracked in git but contain user-specific data (window sizes, book paths) — should be gitignored with defaults committed as `*.json.example`
- [ ] `=1.8.0` junk file in repo root (artifact from pip install, delete it)
