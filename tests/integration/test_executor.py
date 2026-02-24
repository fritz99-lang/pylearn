"""Integration tests: executor session and sandbox lifecycle."""

from __future__ import annotations

import pytest

from pylearn.executor.sandbox import ExecutionResult, Sandbox, check_dangerous_code
from pylearn.executor.session import Session


class TestSessionLifecycle:
    """Session: run, state persistence, reset, timeout, error recovery."""

    def test_basic_run(self) -> None:
        session = Session(timeout=10)
        try:
            result = session.run("print('hello')")
            assert result.stdout.strip() == "hello"
            assert result.return_code == 0
        finally:
            session.reset()

    def test_state_persists_across_runs(self) -> None:
        session = Session(timeout=10)
        try:
            session.run("x = 42")
            result = session.run("print(x)")
            assert "42" in result.stdout
        finally:
            session.reset()

    def test_import_persists(self) -> None:
        session = Session(timeout=10)
        try:
            session.run("import math")
            result = session.run("print(math.pi)")
            assert "3.14" in result.stdout
        finally:
            session.reset()

    def test_reset_clears_state(self) -> None:
        session = Session(timeout=10)
        try:
            session.run("x = 99")
            session.reset()
            result = session.run("print(x)")
            assert result.stderr  # x should not be defined
        finally:
            session.reset()

    @pytest.mark.slow
    def test_timeout(self) -> None:
        session = Session(timeout=3)
        try:
            result = session.run("import time; time.sleep(10)")
            assert result.timed_out
        finally:
            session.reset()

    def test_syntax_error_recovery(self) -> None:
        session = Session(timeout=10)
        try:
            # Run bad code
            result = session.run("def f(:")
            assert result.stderr  # syntax error

            # Session should still work after
            result = session.run("print('recovered')")
            assert "recovered" in result.stdout
        finally:
            session.reset()

    def test_stop(self) -> None:
        session = Session(timeout=10)
        try:
            # Start a process
            session.run("x = 1")
            assert session.is_running
            stopped = session.stop()
            assert stopped
            assert not session.is_running
        finally:
            session.reset()

    def test_history_is_empty(self) -> None:
        """History property returns empty list (persistent REPL handles state)."""
        session = Session(timeout=10)
        assert session.history == []


class TestSandbox:
    """Sandbox: run, error capture, timeout."""

    def test_basic_run(self) -> None:
        sandbox = Sandbox(timeout=10)
        result = sandbox.run("print('sandbox')")
        assert result.stdout.strip() == "sandbox"
        assert result.success

    def test_error_captured(self) -> None:
        sandbox = Sandbox(timeout=10)
        result = sandbox.run("raise ValueError('boom')")
        assert "ValueError" in result.stderr
        assert result.return_code != 0

    def test_syntax_error(self) -> None:
        sandbox = Sandbox(timeout=10)
        result = sandbox.run("def f(:")
        assert result.stderr
        assert not result.success

    @pytest.mark.slow
    def test_timeout(self) -> None:
        sandbox = Sandbox(timeout=3)
        result = sandbox.run("import time; time.sleep(10)")
        assert result.timed_out

    def test_multiline_code(self) -> None:
        sandbox = Sandbox(timeout=10)
        code = "for i in range(3):\n    print(i)"
        result = sandbox.run(code)
        assert "0" in result.stdout
        assert "1" in result.stdout
        assert "2" in result.stdout

    def test_execution_result_success_property(self) -> None:
        good = ExecutionResult(stdout="ok", return_code=0)
        assert good.success

        bad = ExecutionResult(stderr="err", return_code=1)
        assert not bad.success

        timeout = ExecutionResult(return_code=0, timed_out=True)
        assert not timeout.success

        killed = ExecutionResult(return_code=0, killed=True)
        assert not killed.success


class TestDangerousCodeDetection:
    """check_dangerous_code identifies risky patterns."""

    def test_safe_code(self) -> None:
        warnings = check_dangerous_code("x = 1\nprint(x)")
        assert warnings == []

    def test_os_system(self) -> None:
        warnings = check_dangerous_code("os.system('rm -rf /')")
        assert any("os.system" in w for w in warnings)

    def test_subprocess(self) -> None:
        warnings = check_dangerous_code("subprocess.run(['ls'])")
        assert any("subprocess" in w for w in warnings)

    def test_eval(self) -> None:
        warnings = check_dangerous_code("eval('1+1')")
        assert any("eval" in w for w in warnings)

    def test_exec(self) -> None:
        warnings = check_dangerous_code("exec('pass')")
        assert any("exec" in w for w in warnings)

    def test_multiple_dangers(self) -> None:
        code = "import socket\nos.system('ls')\neval('x')"
        warnings = check_dangerous_code(code)
        assert len(warnings) >= 3
