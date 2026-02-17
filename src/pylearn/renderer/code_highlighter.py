# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Syntax highlighting for code blocks using Pygments."""

from __future__ import annotations

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import (
    PythonLexer, PythonConsoleLexer,
    CppLexer, CLexer,
    HtmlLexer, CssLexer,
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

_formatter = HtmlFormatter(nowrap=True, noclasses=True, style="monokai")


def highlight_code(code: str, language: str = "python", is_repl: bool = False) -> str:
    """Highlight source code and return HTML."""
    if is_repl and language == "python":
        lexer = _lexers["python_repl"]
    else:
        lexer = _lexers.get(language, _lexers["text"])

    try:
        return str(highlight(code, lexer, _formatter))
    except Exception:
        return str(highlight(code, _lexers["text"], _formatter))


def get_highlight_css(style: str = "monokai") -> str:
    """Get CSS for Pygments syntax highlighting."""
    formatter = HtmlFormatter(style=style, noclasses=False)
    return str(formatter.get_style_defs(".highlight"))
