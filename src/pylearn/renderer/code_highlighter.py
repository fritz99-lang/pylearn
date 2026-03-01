# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Syntax highlighting for code blocks using Pygments."""

from __future__ import annotations

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import (
    CLexer,
    CppLexer,
    CssLexer,
    HtmlLexer,
    PythonConsoleLexer,
    PythonLexer,
    TextLexer,
)

_lexers = {
    "python": PythonLexer(),
    "python_repl": PythonConsoleLexer(),
    "cpp": CppLexer(),
    "c": CLexer(),
    "html": HtmlLexer(),
    "css": CssLexer(),
    "text": TextLexer(),
}

# Pygments style per app theme — monokai for dark code backgrounds,
# friendly for sepia's light code background.
_THEME_STYLES: dict[str, str] = {
    "light": "monokai",
    "dark": "monokai",
    "sepia": "friendly",
}

_formatters: dict[str, HtmlFormatter] = {}


def _get_formatter(style: str) -> HtmlFormatter:
    """Get or create a cached HtmlFormatter for the given Pygments style."""
    if style not in _formatters:
        _formatters[style] = HtmlFormatter(nowrap=True, noclasses=True, style=style)
    return _formatters[style]


def highlight_code(code: str, language: str = "python", is_repl: bool = False, theme: str = "light") -> str:
    """Highlight source code and return HTML.

    Args:
        code: Source code to highlight.
        language: Programming language for lexer selection.
        is_repl: If True and language is Python, use the REPL lexer.
        theme: App theme name — selects an appropriate Pygments style.
    """
    if is_repl and language == "python":
        lexer = _lexers["python_repl"]
    else:
        lexer = _lexers.get(language, _lexers["text"])

    style = _THEME_STYLES.get(theme, "monokai")
    formatter = _get_formatter(style)

    try:
        return str(highlight(code, lexer, formatter))
    except Exception:
        return str(highlight(code, _lexers["text"], formatter))


def get_highlight_css(style: str = "monokai") -> str:
    """Get CSS for Pygments syntax highlighting."""
    formatter = HtmlFormatter(style=style, noclasses=False)
    return str(formatter.get_style_defs(".highlight"))
