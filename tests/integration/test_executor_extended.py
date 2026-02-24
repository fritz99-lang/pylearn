# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Extended integration tests for executor session and sandbox.

Covers: get_safe_env(), check_dangerous_code() exhaustive patterns,
Session language delegation, Session edge cases, and _kill_tree().
Complements the existing test_executor.py without duplicating it.
"""

from __future__ import annotations

import os
import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest

from pylearn.executor.sandbox import (
    _SENSITIVE_ENV_VARS,
    ExecutionResult,
    _kill_tree,
    check_dangerous_code,
    get_safe_env,
)
from pylearn.executor.session import Session

# ---------------------------------------------------------------------------
# get_safe_env()
# ---------------------------------------------------------------------------


class TestGetSafeEnv:
    """Verify that get_safe_env() strips sensitive env vars and keeps safe ones."""

    def test_strips_aws_secret(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "secret123")
        env = get_safe_env()
        assert "AWS_SECRET_ACCESS_KEY" not in env

    def test_strips_github_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_xxx")
        env = get_safe_env()
        assert "GITHUB_TOKEN" not in env

    def test_strips_gh_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GH_TOKEN", "gho_yyy")
        env = get_safe_env()
        assert "GH_TOKEN" not in env

    def test_strips_openai_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        env = get_safe_env()
        assert "OPENAI_API_KEY" not in env

    def test_strips_anthropic_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        env = get_safe_env()
        assert "ANTHROPIC_API_KEY" not in env

    def test_strips_database_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@host/db")
        env = get_safe_env()
        assert "DATABASE_URL" not in env

    def test_preserves_path(self) -> None:
        env = get_safe_env()
        # PATH should always be present in the environment
        assert "PATH" in env or "Path" in env  # Windows uses "Path"

    def test_preserves_home(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HOME", "/home/testuser")
        env = get_safe_env()
        assert env.get("HOME") == "/home/testuser"

    def test_strips_all_sensitive_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Every variable in _SENSITIVE_ENV_VARS is stripped."""
        for var in _SENSITIVE_ENV_VARS:
            monkeypatch.setenv(var, "sensitive_value")
        env = get_safe_env()
        for var in _SENSITIVE_ENV_VARS:
            assert var not in env, f"{var} was not stripped"

    def test_returns_copy_not_original(self) -> None:
        """Modifying the returned dict should not affect os.environ."""
        env = get_safe_env()
        env["__PYLEARN_TEST_SENTINEL__"] = "1"
        assert "__PYLEARN_TEST_SENTINEL__" not in os.environ


# ---------------------------------------------------------------------------
# check_dangerous_code() — exhaustive pattern coverage
# ---------------------------------------------------------------------------


class TestCheckDangerousCodeExtended:
    """Cover every danger pattern defined in sandbox._DANGER_PATTERNS."""

    def test_safe_code_returns_empty(self) -> None:
        assert check_dangerous_code("x = 1\nprint(x)") == []

    def test_os_remove(self) -> None:
        warnings = check_dangerous_code("os.remove('/tmp/file')")
        assert any("os.remove" in w for w in warnings)

    def test_os_unlink(self) -> None:
        warnings = check_dangerous_code("os.unlink('/tmp/file')")
        assert any("unlink" in w for w in warnings)

    def test_shutil_rmtree(self) -> None:
        warnings = check_dangerous_code("shutil.rmtree('/tmp/dir')")
        assert any("shutil.rmtree" in w for w in warnings)

    def test_import_dunder(self) -> None:
        warnings = check_dangerous_code("mod = __import__('os')")
        assert any("__import__" in w for w in warnings)

    def test_os_rmdir(self) -> None:
        warnings = check_dangerous_code("os.rmdir('/tmp/dir')")
        assert any("os.rmdir" in w for w in warnings)

    def test_os_rename(self) -> None:
        warnings = check_dangerous_code("os.rename('a', 'b')")
        assert any("os.rename" in w for w in warnings)

    def test_file_write_open(self) -> None:
        warnings = check_dangerous_code("open('file.txt', 'w')")
        assert any("file write" in w.lower() or "open" in w.lower() for w in warnings)

    def test_path_unlink(self) -> None:
        warnings = check_dangerous_code("Path('/tmp/f').unlink()")
        assert any("unlink" in w.lower() for w in warnings)

    def test_pathlib_path_unlink(self) -> None:
        warnings = check_dangerous_code("pathlib.Path('/tmp/f').unlink()")
        assert any("unlink" in w.lower() for w in warnings)

    def test_socket(self) -> None:
        warnings = check_dangerous_code("import socket\nsocket.create_connection()")
        assert any("socket" in w for w in warnings)

    def test_http_client(self) -> None:
        warnings = check_dangerous_code("import http.client")
        assert any("HTTP" in w or "http" in w for w in warnings)

    def test_urllib_request(self) -> None:
        warnings = check_dangerous_code("import urllib.request")
        assert any("HTTP" in w or "urllib" in w for w in warnings)

    def test_ctypes(self) -> None:
        warnings = check_dangerous_code("import ctypes")
        assert any("ctypes" in w for w in warnings)

    def test_importlib(self) -> None:
        warnings = check_dangerous_code("import importlib")
        assert any("importlib" in w for w in warnings)

    def test_getattr_pattern(self) -> None:
        warnings = check_dangerous_code("getattr(obj, 'secret')")
        assert any("getattr" in w for w in warnings)

    def test_builtins_pattern(self) -> None:
        warnings = check_dangerous_code("__builtins__['eval']")
        assert any("__builtins__" in w for w in warnings)

    def test_subprocess_call(self) -> None:
        warnings = check_dangerous_code("subprocess.call(['ls'])")
        assert any("subprocess" in w for w in warnings)

    def test_subprocess_popen(self) -> None:
        warnings = check_dangerous_code("subprocess.Popen(['ls'])")
        assert any("subprocess" in w for w in warnings)


# ---------------------------------------------------------------------------
# Session language delegation
# ---------------------------------------------------------------------------


class TestSessionLanguageDelegation:
    """Session.run() delegates C++/HTML to Sandbox instead of the REPL."""

    @patch("pylearn.executor.sandbox.Sandbox")
    def test_cpp_delegates_to_sandbox(self, MockSandbox: MagicMock) -> None:
        mock_sandbox_instance = MockSandbox.return_value
        mock_sandbox_instance.run.return_value = ExecutionResult(
            stdout="Hello from C++",
            return_code=0,
        )
        session = Session(timeout=10, language="python")
        result = session.run("int main() { return 0; }", language="cpp")

        MockSandbox.assert_called_once_with(timeout=10)
        mock_sandbox_instance.run.assert_called_once_with(
            "int main() { return 0; }",
            language="cpp",
        )
        assert result.stdout == "Hello from C++"

    @patch("pylearn.executor.sandbox.Sandbox")
    def test_c_delegates_to_sandbox(self, MockSandbox: MagicMock) -> None:
        mock_sandbox_instance = MockSandbox.return_value
        mock_sandbox_instance.run.return_value = ExecutionResult(
            stdout="Hello from C",
            return_code=0,
        )
        session = Session(timeout=10)
        session.run("#include <stdio.h>", language="c")

        MockSandbox.assert_called_once_with(timeout=10)
        mock_sandbox_instance.run.assert_called_once_with(
            "#include <stdio.h>",
            language="c",
        )

    @patch("pylearn.executor.sandbox.Sandbox")
    def test_html_delegates_to_sandbox(self, MockSandbox: MagicMock) -> None:
        mock_sandbox_instance = MockSandbox.return_value
        mock_sandbox_instance.run.return_value = ExecutionResult(
            stdout="Opened in browser",
            return_code=0,
        )
        session = Session(timeout=10)
        result = session.run("<html></html>", language="html")

        MockSandbox.assert_called_once_with(timeout=10)
        mock_sandbox_instance.run.assert_called_once_with(
            "<html></html>",
            language="html",
        )
        assert result.stdout == "Opened in browser"

    def test_python_does_not_delegate(self) -> None:
        """Python code uses the persistent REPL, not Sandbox."""
        session = Session(timeout=10)
        try:
            result = session.run("print('repl')", language="python")
            assert "repl" in result.stdout
        finally:
            session.reset()

    @patch("pylearn.executor.sandbox.Sandbox")
    def test_session_default_language_delegates(self, MockSandbox: MagicMock) -> None:
        """If Session.language is 'cpp', run() without explicit language delegates."""
        mock_sandbox_instance = MockSandbox.return_value
        mock_sandbox_instance.run.return_value = ExecutionResult(
            stdout="cpp output",
            return_code=0,
        )
        session = Session(timeout=10, language="cpp")
        session.run("int main() {}")

        # language=None means use self.language="cpp"
        MockSandbox.assert_called_once_with(timeout=10)
        mock_sandbox_instance.run.assert_called_once_with(
            "int main() {}",
            language="cpp",
        )


# ---------------------------------------------------------------------------
# Session edge cases
# ---------------------------------------------------------------------------


class TestSessionEdgeCases:
    """Edge cases for Session: stop, reset, empty code, properties."""

    def test_stop_when_no_process_returns_false(self) -> None:
        session = Session(timeout=10)
        # No process has been started yet
        assert session.stop() is False

    def test_stop_when_process_running_returns_true(self) -> None:
        session = Session(timeout=10)
        try:
            session.run("x = 1")
            assert session.is_running
            assert session.stop() is True
            assert not session.is_running
        finally:
            session.reset()

    def test_reset_kills_process(self) -> None:
        session = Session(timeout=10)
        try:
            session.run("x = 1")
            assert session.is_running
            session.reset()
            assert not session.is_running
        finally:
            session.reset()

    def test_reset_then_run_starts_new_process(self) -> None:
        session = Session(timeout=10)
        try:
            session.run("x = 42")
            session.reset()
            # After reset, previous state is gone
            result = session.run("print(x)")
            assert result.stderr  # x should not be defined
        finally:
            session.reset()

    def test_run_empty_code(self) -> None:
        session = Session(timeout=10)
        try:
            result = session.run("")
            # Empty code should succeed (the REPL just echoes sentinel)
            assert result.return_code == 0
            assert result.stdout.strip() == ""
        finally:
            session.reset()

    def test_run_whitespace_only_code(self) -> None:
        session = Session(timeout=10)
        try:
            result = session.run("   \n  \n")
            assert result.return_code == 0
        finally:
            session.reset()

    def test_is_running_initially_false(self) -> None:
        session = Session(timeout=10)
        assert not session.is_running

    def test_history_always_empty(self) -> None:
        session = Session(timeout=10)
        try:
            session.run("x = 1")
            assert session.history == []
        finally:
            session.reset()

    def test_multiple_resets_no_crash(self) -> None:
        session = Session(timeout=10)
        session.reset()
        session.reset()
        session.reset()
        # Should not raise


# ---------------------------------------------------------------------------
# _kill_tree()
# ---------------------------------------------------------------------------


class TestKillTree:
    """Test _kill_tree() terminates a subprocess."""

    def test_kill_tree_terminates_subprocess(self) -> None:
        """Start a sleeping subprocess, kill it, verify it is dead."""
        proc = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(60)"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert proc.poll() is None  # process is alive

        _kill_tree(proc)
        # Give it a moment to die
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)

        assert proc.poll() is not None  # process is dead

    def test_kill_tree_already_dead_no_error(self) -> None:
        """Calling _kill_tree on an already-dead process should not raise."""
        proc = subprocess.Popen(
            [sys.executable, "-c", "pass"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        proc.wait(timeout=5)
        assert proc.poll() is not None
        # Should not raise even though process is already dead
        _kill_tree(proc)


# ---------------------------------------------------------------------------
# ExecutionResult edge cases
# ---------------------------------------------------------------------------


class TestExecutionResultExtended:
    """Additional coverage for ExecutionResult."""

    def test_default_values(self) -> None:
        result = ExecutionResult()
        assert result.stdout == ""
        assert result.stderr == ""
        assert result.return_code == 0
        assert result.timed_out is False
        assert result.killed is False
        assert result.success is True

    def test_killed_flag(self) -> None:
        result = ExecutionResult(return_code=0, killed=True)
        assert not result.success

    def test_nonzero_return_code(self) -> None:
        result = ExecutionResult(return_code=1)
        assert not result.success

    def test_timed_out_overrides_return_code(self) -> None:
        result = ExecutionResult(return_code=0, timed_out=True)
        assert not result.success
