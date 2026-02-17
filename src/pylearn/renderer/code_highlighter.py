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


def highlight_code(code: str, language: str = "python", is_repl: bool = False) -> str:
    """Highlight source code and return HTML."""
    if is_repl and language == "python":
        lexer = _lexers["python_repl"]
    else:
        lexer = _lexers.get(language, _lexers["text"])

    formatter = HtmlFormatter(
        nowrap=True,
        noclasses=True,
        style="monokai",
    )
    try:
        return str(highlight(code, lexer, formatter))
    except Exception:
        return str(highlight(code, _lexers["text"], formatter))


# Keep old name as alias for compatibility
highlight_python = highlight_code


def get_highlight_css(style: str = "monokai") -> str:
    """Get CSS for Pygments syntax highlighting."""
    formatter = HtmlFormatter(style=style, noclasses=False)
    return str(formatter.get_style_defs(".highlight"))
