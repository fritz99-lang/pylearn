# Contributing to PyLearn

Thanks for your interest in contributing to PyLearn! This guide covers everything you need to get started.

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md) in all interactions.

## Ways to Contribute

- **Report bugs** — Use the [bug report template](https://github.com/fritz99-lang/pylearn/issues/new?template=bug_report.md) on GitHub Issues
- **Request features** — Use the [feature request template](https://github.com/fritz99-lang/pylearn/issues/new?template=feature_request.md) on GitHub Issues
- **Submit code** — Fix a bug, add a feature, or improve existing code via pull request
- **Improve docs** — Fix typos, clarify instructions, or add missing documentation
- **Report security issues** — See [SECURITY.md](SECURITY.md) (email only, do not open a public issue)

## Development Setup

```bash
git clone https://github.com/fritz99-lang/pylearn.git
cd pylearn

# Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate    # Linux/macOS
.venv\Scripts\activate       # Windows

# Install with dev dependencies (pytest + mypy)
pip install -e ".[dev]"
```

Requires Python 3.12 or newer.

## Running Tests and Type Checks

```bash
# Run all tests (702 tests)
pytest tests/ -v

# Skip slow tests
pytest tests/ -v -m "not slow"

# Type checking
mypy src/pylearn/
```

All tests must pass and mypy must report zero errors before submitting a PR.

## Coding Standards

- **Python 3.12+** — Use modern syntax (type unions with `|`, etc.)
- **Type hints** — Strict mypy on core code (`src/pylearn/`). PyQt6 UI code uses relaxed checking since PyQt6 lacks type stubs.
- **License headers** — New files should include the MIT copyright header: `Copyright (c) 2026 Nathan Tritle`
- **No magic strings** — Use constants from `src/pylearn/core/constants.py` instead of hardcoded values
- **Keep it simple** — Match the existing code style in the file you're editing

## Pull Request Workflow

1. **Fork** the repository on GitHub
2. **Create a branch** from `master` for your change (`git checkout -b my-feature`)
3. **Make your changes** — keep commits focused and well-described
4. **Run tests and type checks** — make sure everything passes (see above)
5. **Push** your branch and **open a pull request** against `master`
6. **Fill out the PR template** — the checklist will guide you through what's needed

PRs are reviewed by the maintainer. Small, focused PRs are easier to review and more likely to be merged quickly.

## Questions?

Open a [GitHub Issue](https://github.com/fritz99-lang/pylearn/issues) or start a discussion. Happy coding!
