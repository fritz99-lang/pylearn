"""Entry point for PyLearn application."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the src directory is in the path
src_dir = Path(__file__).resolve().parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))


def main() -> None:
    """Launch the PyLearn application."""
    debug = "--debug" in sys.argv
    from pylearn.app import run_app
    sys.exit(run_app(debug=debug))


if __name__ == "__main__":
    main()
