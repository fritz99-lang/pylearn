"""Tests for text utility functions."""

import pytest
from pylearn.utils.text_utils import (
    clean_text,
    clean_code_text,
    normalize_whitespace,
    is_page_header_or_footer,
    detect_repl_code,
    strip_repl_prompts,
)


class TestCleanText:
    def test_empty(self):
        assert clean_text("") == ""

    def test_ligatures(self):
        assert clean_text("\ufb01nd") == "find"
        assert clean_text("\ufb02ow") == "flow"
        assert clean_text("\ufb03") == "ffi"
        assert clean_text("\ufb04") == "ffl"

    def test_smart_quotes(self):
        assert clean_text("\u201chello\u201d") == '"hello"'
        assert clean_text("\u2018it\u2019s") == "'it's"

    def test_dashes(self):
        assert clean_text("\u2013") == "-"
        assert clean_text("\u2014") == "--"

    def test_ellipsis(self):
        assert clean_text("\u2026") == "..."

    def test_nbsp(self):
        assert clean_text("hello\u00a0world") == "hello world"

    def test_passthrough(self):
        assert clean_text("normal text") == "normal text"


class TestCleanCodeText:
    def test_strips_page_numbers(self):
        code = "def foo():\n42\n    pass"
        result = clean_code_text(code)
        assert "42" not in result
        assert "def foo():" in result
        assert "    pass" in result

    def test_strips_chapter_headers(self):
        code = "x = 1\nChapter 5: Title\ny = 2"
        result = clean_code_text(code)
        assert "Chapter 5:" not in result

    def test_preserves_real_code(self):
        code = "for i in range(100):\n    print(i)"
        result = clean_code_text(code)
        assert result == code


class TestNormalizeWhitespace:
    def test_collapses_spaces(self):
        assert normalize_whitespace("a  b   c") == "a b c"

    def test_collapses_newlines(self):
        assert normalize_whitespace("a\n\n\n\nb") == "a\n\nb"

    def test_strips(self):
        assert normalize_whitespace("  hello  ") == "hello"


class TestIsPageHeaderOrFooter:
    def test_empty(self):
        assert is_page_header_or_footer("") is True
        assert is_page_header_or_footer("   ") is True

    def test_page_number(self):
        assert is_page_header_or_footer("42") is True
        assert is_page_header_or_footer("1234") is True

    def test_not_page_number(self):
        assert is_page_header_or_footer("12345") is False

    def test_chapter_header(self):
        assert is_page_header_or_footer("Chapter 5") is True
        assert is_page_header_or_footer("Part III") is True

    def test_pipe_header(self):
        assert is_page_header_or_footer("123 | Chapter 5: Functions") is True

    def test_url(self):
        assert is_page_header_or_footer("www.oreilly.com") is True

    def test_normal_text(self):
        assert is_page_header_or_footer("Python is a programming language") is False
        assert is_page_header_or_footer("The print() function outputs text.") is False


class TestDetectReplCode:
    def test_repl_code(self):
        code = ">>> x = 1\n>>> print(x)\n1"
        assert detect_repl_code(code) is True

    def test_repl_with_continuation(self):
        code = ">>> for i in range(3):\n...     print(i)\n0\n1\n2"
        assert detect_repl_code(code) is True

    def test_not_repl(self):
        code = "x = 1\nprint(x)"
        assert detect_repl_code(code) is False

    def test_single_prompt(self):
        code = ">>> print('hello')\nhello"
        assert detect_repl_code(code) is True

    def test_empty(self):
        assert detect_repl_code("") is False


class TestStripReplPrompts:
    def test_basic(self):
        code = ">>> x = 1\n>>> print(x)\n1"
        result = strip_repl_prompts(code)
        assert result == "x = 1\nprint(x)"

    def test_continuation(self):
        code = ">>> for i in range(3):\n...     print(i)\n0\n1\n2"
        result = strip_repl_prompts(code)
        assert result == "for i in range(3):\n    print(i)"

    def test_bare_prompt(self):
        code = ">>>\n>>> x = 1"
        result = strip_repl_prompts(code)
        assert result == "\nx = 1"

    def test_no_prompts(self):
        code = "x = 1\nprint(x)"
        result = strip_repl_prompts(code)
        # No prompt lines → no code lines in output
        assert result == ""
