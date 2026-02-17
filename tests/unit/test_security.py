# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Tests for security-related functions: sanitize_book_id, get_safe_env, check_dangerous_code."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from pylearn.parser.cache_manager import sanitize_book_id
from pylearn.executor.sandbox import (
    get_safe_env,
    check_dangerous_code,
    _SENSITIVE_ENV_VARS,
)


# ---------------------------------------------------------------------------
# sanitize_book_id()
# ---------------------------------------------------------------------------

class TestSanitizeBookId:
    """Test the book ID sanitizer for path traversal and injection prevention."""

    def test_normal_input_lowercased(self):
        result = sanitize_book_id("Learning Python")
        # Spaces are stripped (not alphanumeric or underscore), uppercase lowered
        assert result == "learningpython"

    def test_already_clean_unchanged(self):
        assert sanitize_book_id("learning_python") == "learning_python"

    def test_path_traversal_unix(self):
        """Forward-slash path traversal components must be stripped."""
        result = sanitize_book_id("../../etc/passwd")
        assert "/" not in result
        assert ".." not in result
        assert "etc" in result  # alphanumeric portion survives

    def test_path_traversal_windows(self):
        """Backslash path traversal components must be stripped."""
        result = sanitize_book_id("..\\..\\windows\\system32")
        assert "\\" not in result
        assert ".." not in result

    def test_special_characters_stripped(self):
        result = sanitize_book_id("book;id'with\"chars")
        # Only alphanumeric and underscores should survive
        assert ";" not in result
        assert "'" not in result
        assert '"' not in result
        assert result.isascii()
        # Should contain the alphanumeric parts
        assert "book" in result
        assert "id" in result

    def test_empty_string(self):
        """Empty input should return an empty string (no crash)."""
        result = sanitize_book_id("")
        assert isinstance(result, str)
        assert result == ""

    def test_very_long_string_truncated(self):
        """Extremely long input should be truncated to 60 chars."""
        long_input = "a" * 200
        result = sanitize_book_id(long_input)
        assert len(result) <= 60

    def test_unicode_stripped(self):
        """Non-ASCII characters should be stripped."""
        result = sanitize_book_id("b\u00f6k_n\u00e0me")
        # Only ASCII alphanumeric + underscore should remain
        assert all(c.isascii() for c in result)
        # The non-ASCII chars \u00f6 and \u00e0 should be gone
        assert "\u00f6" not in result
        assert "\u00e0" not in result
        # ASCII letters and underscore survive
        assert "b" in result
        assert "k" in result
        assert "_" in result

    def test_digits_preserved(self):
        assert sanitize_book_id("python3_12") == "python3_12"

    def test_mixed_case_lowered(self):
        assert sanitize_book_id("MyBook") == "mybook"

    def test_dots_stripped(self):
        """Dots (used in file extensions) must be stripped."""
        result = sanitize_book_id("book.pdf")
        assert "." not in result
        assert result == "bookpdf"

    def test_null_bytes_stripped(self):
        """Null bytes (common injection vector) must be stripped."""
        result = sanitize_book_id("book\x00id")
        assert "\x00" not in result

    def test_result_is_filesystem_safe(self):
        """The result should only contain chars safe for filenames."""
        dangerous_inputs = [
            "../../../etc/shadow",
            "CON",  # Windows reserved name
            "book<>:\"|?*name",
            "a" * 300,
            "\t\n\r",
        ]
        for inp in dangerous_inputs:
            result = sanitize_book_id(inp)
            # Only alphanumeric + underscore allowed by the regex
            assert all(c in "abcdefghijklmnopqrstuvwxyz0123456789_" for c in result), (
                f"Unsafe char in result for input {inp!r}: {result!r}"
            )


# ---------------------------------------------------------------------------
# get_safe_env()
# ---------------------------------------------------------------------------

class TestGetSafeEnv:
    """Test environment variable sanitization for child processes."""

    def test_returns_dict(self):
        result = get_safe_env()
        assert isinstance(result, dict)

    def test_returns_copy_not_original(self):
        """Modifying the returned dict should not affect os.environ."""
        env = get_safe_env()
        env["__TEST_SENTINEL__"] = "modified"
        assert "__TEST_SENTINEL__" not in os.environ

    def test_sensitive_vars_removed(self):
        """All known sensitive variables should be stripped."""
        fake_env = {var: "secret_value" for var in _SENSITIVE_ENV_VARS}
        fake_env["PATH"] = "/usr/bin"
        fake_env["HOME"] = "/home/user"
        with patch.dict(os.environ, fake_env, clear=True):
            result = get_safe_env()
        for var in _SENSITIVE_ENV_VARS:
            assert var not in result, f"{var} should have been stripped"

    def test_path_preserved(self):
        """PATH should remain in the sanitized environment."""
        with patch.dict(os.environ, {"PATH": "/usr/bin"}, clear=False):
            result = get_safe_env()
        assert "PATH" in result

    def test_home_preserved(self):
        with patch.dict(os.environ, {"HOME": "/home/user"}, clear=False):
            result = get_safe_env()
        assert "HOME" in result

    def test_aws_secret_key_removed(self):
        with patch.dict(os.environ, {"AWS_SECRET_ACCESS_KEY": "hunter2"}, clear=False):
            result = get_safe_env()
        assert "AWS_SECRET_ACCESS_KEY" not in result

    def test_github_token_removed(self):
        with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_abc123"}, clear=False):
            result = get_safe_env()
        assert "GITHUB_TOKEN" not in result

    def test_database_url_removed(self):
        with patch.dict(os.environ, {"DATABASE_URL": "postgres://..."}, clear=False):
            result = get_safe_env()
        assert "DATABASE_URL" not in result

    def test_openai_api_key_removed(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-abc"}, clear=False):
            result = get_safe_env()
        assert "OPENAI_API_KEY" not in result

    def test_anthropic_api_key_removed(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-abc"}, clear=False):
            result = get_safe_env()
        assert "ANTHROPIC_API_KEY" not in result

    def test_normal_vars_survive(self):
        """Arbitrary non-sensitive variables should pass through."""
        with patch.dict(os.environ, {"MY_APP_SETTING": "value"}, clear=False):
            result = get_safe_env()
        assert "MY_APP_SETTING" in result
        assert result["MY_APP_SETTING"] == "value"

    def test_missing_sensitive_var_no_error(self):
        """If a sensitive var is not present, stripping it should not raise."""
        # Clear all sensitive vars so pop() hits the default path
        clean = {k: v for k, v in os.environ.items() if k not in _SENSITIVE_ENV_VARS}
        with patch.dict(os.environ, clean, clear=True):
            result = get_safe_env()  # should not raise
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# check_dangerous_code()
# ---------------------------------------------------------------------------

class TestCheckDangerousCode:
    """Test the advisory danger-pattern scanner."""

    # --- Safe code ---

    def test_safe_print_no_warnings(self):
        assert check_dangerous_code('print("hello")') == []

    def test_safe_arithmetic_no_warnings(self):
        assert check_dangerous_code("x = 1 + 2\nprint(x)") == []

    def test_safe_function_def_no_warnings(self):
        code = "def add(a, b):\n    return a + b\nprint(add(1, 2))"
        assert check_dangerous_code(code) == []

    def test_safe_open_read_no_warnings(self):
        """open() with 'r' mode should NOT trigger."""
        assert check_dangerous_code("f = open('data.txt', 'r')") == []

    def test_empty_string_no_warnings(self):
        assert check_dangerous_code("") == []

    # --- os.system ---

    def test_os_system_detected(self):
        warnings = check_dangerous_code('os.system("rm -rf /")')
        assert any("os.system" in w for w in warnings)

    # --- subprocess ---

    def test_subprocess_call_detected(self):
        warnings = check_dangerous_code("subprocess.call(['ls'])")
        assert any("subprocess" in w for w in warnings)

    def test_subprocess_run_detected(self):
        warnings = check_dangerous_code("subprocess.run(['ls'])")
        assert any("subprocess" in w for w in warnings)

    def test_subprocess_popen_detected(self):
        warnings = check_dangerous_code("subprocess.Popen(['ls'])")
        assert any("subprocess" in w for w in warnings)

    # --- eval / exec ---

    def test_eval_detected(self):
        warnings = check_dangerous_code("result = eval(user_input)")
        assert any("eval" in w for w in warnings)

    def test_exec_detected(self):
        warnings = check_dangerous_code("exec(code_string)")
        assert any("exec" in w for w in warnings)

    # --- File deletion ---

    def test_os_remove_detected(self):
        warnings = check_dangerous_code("os.remove('/tmp/file')")
        assert any("remove" in w.lower() or "unlink" in w.lower() for w in warnings)

    def test_shutil_rmtree_detected(self):
        warnings = check_dangerous_code("shutil.rmtree('/tmp/dir')")
        assert any("rmtree" in w for w in warnings)

    # --- getattr / __builtins__ (newly added patterns) ---

    def test_getattr_detected(self):
        warnings = check_dangerous_code("getattr(os, 'system')('rm -rf /')")
        assert any("getattr" in w for w in warnings)

    def test_builtins_detected(self):
        warnings = check_dangerous_code("__builtins__.__import__('os')")
        assert any("__builtins__" in w for w in warnings)

    # --- Network access ---

    def test_socket_detected(self):
        warnings = check_dangerous_code("import socket\ns = socket.socket()")
        assert any("socket" in w for w in warnings)

    def test_http_client_detected(self):
        warnings = check_dangerous_code("import http.client")
        assert any("HTTP" in w or "http" in w.lower() for w in warnings)

    def test_urllib_detected(self):
        warnings = check_dangerous_code("import urllib.request")
        assert any("HTTP" in w or "http" in w.lower() for w in warnings)

    # --- File write ---

    def test_file_write_detected(self):
        warnings = check_dangerous_code("f = open('data.txt', 'w')")
        assert any("file write" in w.lower() for w in warnings)

    # --- ctypes / importlib ---

    def test_ctypes_detected(self):
        warnings = check_dangerous_code("import ctypes")
        assert any("ctypes" in w for w in warnings)

    def test_importlib_detected(self):
        warnings = check_dangerous_code("import importlib")
        assert any("importlib" in w for w in warnings)

    # --- __import__ ---

    def test_dunder_import_detected(self):
        warnings = check_dangerous_code("__import__('os').system('ls')")
        assert any("__import__" in w for w in warnings)

    # --- Path.unlink ---

    def test_path_unlink_detected(self):
        warnings = check_dangerous_code("Path('/tmp/file').unlink()")
        assert any("unlink" in w.lower() for w in warnings)

    # --- os.rmdir / os.rename ---

    def test_os_rmdir_detected(self):
        warnings = check_dangerous_code("os.rmdir('/tmp/dir')")
        assert any("rmdir" in w for w in warnings)

    def test_os_rename_detected(self):
        warnings = check_dangerous_code("os.rename('/a', '/b')")
        assert any("rename" in w for w in warnings)

    # --- Multiple patterns ---

    def test_multiple_dangerous_patterns(self):
        """Code with multiple dangerous patterns should return multiple warnings."""
        code = 'import os\nos.system("ls")\neval(x)\nexec(code)\nimport socket'
        warnings = check_dangerous_code(code)
        assert len(warnings) >= 4

    def test_returns_list_type(self):
        result = check_dangerous_code("x = 1")
        assert isinstance(result, list)

    def test_each_warning_is_string(self):
        warnings = check_dangerous_code("os.system('ls')\neval(x)")
        for w in warnings:
            assert isinstance(w, str)
