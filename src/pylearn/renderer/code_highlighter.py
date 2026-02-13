"""Syntax highlighting for code blocks using Pygments."""

from __future__ import annotations

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import PythonLexer, PythonConsoleLexer, TextLexer


_python_lexer = PythonLexer()
_console_lexer = PythonConsoleLexer()
_text_lexer = TextLexer()


def highlight_python(code: str, is_repl: bool = False) -> str:
    """Highlight Python code and return HTML."""
    lexer = _console_lexer if is_repl else _python_lexer
    formatter = HtmlFormatter(
        nowrap=True,
        noclasses=True,
        style="monokai",
    )
    try:
        return highlight(code, lexer, formatter)
    except Exception:
        return highlight(code, _text_lexer, formatter)


def get_highlight_css(style: str = "monokai") -> str:
    """Get CSS for Pygments syntax highlighting."""
    formatter = HtmlFormatter(style=style, noclasses=False)
    return formatter.get_style_defs(".highlight")
