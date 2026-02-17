# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Persistent execution session where variables carry over between runs.

Uses a long-running subprocess with a custom REPL protocol so that
variables, imports, and state persist between run() calls — no history
replay needed.
"""

from __future__ import annotations

import subprocess
import sys
import threading
import logging
import uuid

from pylearn.core.constants import get_python_executable, DATA_DIR
from pylearn.executor.sandbox import ExecutionResult, get_safe_env, _kill_tree, _CREATE_NO_WINDOW

logger = logging.getLogger("pylearn.executor")

# Maximum chars of stdout/stderr to capture before truncating
_MAX_OUTPUT_CHARS = 2 * 1024 * 1024  # 2M characters

def _new_sentinel() -> str:
    """Generate a unique sentinel per process spawn."""
    return f"__PYLEARN_DONE_{uuid.uuid4().hex}__"

# Script injected into the persistent subprocess.  It reads code blocks
# from stdin delimited by the sentinel, exec()s them, and prints the
# sentinel back so the parent knows when output is complete.
_REPL_BOOTSTRAP = r'''
import sys, traceback, io

_SENTINEL = {sentinel!r}
_namespace = {{"__name__": "__main__", "__builtins__": __builtins__}}

while True:
    # Read lines until we see the sentinel
    lines = []
    for raw in sys.stdin:
        line = raw.rstrip("\n")
        if line == _SENTINEL:
            break
        lines.append(line)
    else:
        # stdin closed — exit
        break

    code = "\n".join(lines)
    if not code.strip():
        # Empty code block — just echo sentinel
        print(_SENTINEL, flush=True)
        print(_SENTINEL, file=sys.stderr, flush=True)
        continue

    try:
        compiled = compile(code, "<session>", "exec")
        exec(compiled, _namespace)
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc()

    # Flush and print sentinel on both streams so parent knows we're done
    sys.stdout.flush()
    sys.stderr.flush()
    print(_SENTINEL, flush=True)
    print(_SENTINEL, file=sys.stderr, flush=True)
'''


class Session:
    """A persistent Python session using a long-running subprocess.

    Variables and imports persist between run() calls naturally because
    the subprocess maintains its own namespace dict.  No history replay.
    """

    def __init__(self, timeout: int = 30, language: str = "python") -> None:
        self.timeout = timeout
        self.language = language
        self._process: subprocess.Popen | None = None
        self._sentinel: str = ""
        self._process_lock = threading.Lock()
        self._scratch_dir = DATA_DIR / "scratch"
        self._scratch_dir.mkdir(parents=True, exist_ok=True)

    def _ensure_process(self) -> subprocess.Popen | None:
        """Start the persistent subprocess if it isn't running."""
        with self._process_lock:
            if self._process is not None and self._process.poll() is None:
                return self._process
            # Start a new one
            python = get_python_executable()
            if not python:
                return None
            self._sentinel = _new_sentinel()
            bootstrap = _REPL_BOOTSTRAP.format(sentinel=self._sentinel)
            self._process = subprocess.Popen(
                [python, "-u", "-c", bootstrap],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(self._scratch_dir),
                env=get_safe_env(),
                creationflags=_CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            return self._process

    def run(self, code: str, language: str | None = None) -> ExecutionResult:
        """Execute code in the persistent session.

        For C++/HTML, delegates to Sandbox (no session persistence).
        """
        lang = language or self.language

        # C++/HTML don't support session persistence — delegate to Sandbox
        if lang in ("cpp", "c", "html"):
            from pylearn.executor.sandbox import Sandbox
            sandbox = Sandbox(timeout=self.timeout)
            return sandbox.run(code, language=lang)

        proc = self._ensure_process()
        if proc is None:
            return ExecutionResult(
                stderr="No Python interpreter found. Install Python and add it to PATH.",
                return_code=-1,
            )

        try:
            # Send code + sentinel to the subprocess
            if proc.stdin is None:
                self._kill_process()
                return ExecutionResult(stderr="Session stdin unavailable", return_code=-1)
            proc.stdin.write(code + "\n" + self._sentinel + "\n")
            proc.stdin.flush()
        except (OSError, BrokenPipeError) as e:
            logger.error(f"Failed to send code to session: {e}")
            self._kill_process()
            return ExecutionResult(stderr=f"Session process died: {e}", return_code=-1)

        # Collect stdout and stderr until we see the sentinel on each
        sentinel = self._sentinel
        stdout_lines: list[str] = []
        stderr_lines: list[str] = []
        stdout_bytes = 0
        stderr_bytes = 0
        stdout_truncated = False
        stderr_truncated = False
        timed_out = False

        def _read_stdout() -> None:
            nonlocal stdout_bytes, stdout_truncated
            try:
                if proc.stdout is None:
                    return
                for line in proc.stdout:
                    if line.rstrip("\n") == sentinel:
                        break
                    if not stdout_truncated:
                        stdout_bytes += len(line)
                        if stdout_bytes > _MAX_OUTPUT_CHARS:
                            stdout_truncated = True
                            stdout_lines.append("\n[output truncated — exceeded 2 MB limit]\n")
                        else:
                            stdout_lines.append(line)
            except Exception:
                pass

        def _read_stderr() -> None:
            nonlocal stderr_bytes, stderr_truncated
            try:
                if proc.stderr is None:
                    return
                for line in proc.stderr:
                    if line.rstrip("\n") == sentinel:
                        break
                    if not stderr_truncated:
                        stderr_bytes += len(line)
                        if stderr_bytes > _MAX_OUTPUT_CHARS:
                            stderr_truncated = True
                            stderr_lines.append("\n[stderr truncated — exceeded 2 MB limit]\n")
                        else:
                            stderr_lines.append(line)
            except Exception:
                pass

        stdout_thread = threading.Thread(target=_read_stdout, daemon=True)
        stderr_thread = threading.Thread(target=_read_stderr, daemon=True)
        stdout_thread.start()
        stderr_thread.start()

        stdout_thread.join(timeout=self.timeout)
        stderr_thread.join(timeout=max(1, self.timeout - 1))

        if stdout_thread.is_alive() or stderr_thread.is_alive():
            # Timed out — kill the process (it will be restarted on next run)
            timed_out = True
            self._kill_process()
            return ExecutionResult(
                stdout="".join(stdout_lines),
                stderr=f"Execution timed out after {self.timeout} seconds",
                return_code=-1,
                timed_out=True,
            )

        stdout = "".join(stdout_lines)
        stderr = "".join(stderr_lines)

        # Check if subprocess died
        if proc.poll() is not None:
            self._kill_process()
            return ExecutionResult(
                stdout=stdout,
                stderr=stderr or "Session process exited unexpectedly",
                return_code=proc.returncode,
            )

        # If there's stderr output, it's an error but the process is still alive
        return_code = 1 if stderr.strip() else 0
        return ExecutionResult(
            stdout=stdout,
            stderr=stderr,
            return_code=return_code,
        )

    def _kill_process(self) -> None:
        """Kill the persistent subprocess and all its children."""
        with self._process_lock:
            if self._process is not None:
                try:
                    _kill_tree(self._process)
                    self._process.wait(timeout=5)
                except Exception:
                    try:
                        self._process.kill()
                    except Exception:
                        pass
                self._process = None

    def stop(self) -> bool:
        """Kill the currently running process and clean up."""
        had_process = self._process is not None
        self._kill_process()
        return had_process

    def reset(self) -> None:
        """Reset the session by killing the subprocess.

        The next run() call will start a fresh process.
        """
        self._kill_process()

    @property
    def history(self) -> list[str]:
        # No longer tracking history — persistent REPL handles state
        return []

    @property
    def is_running(self) -> bool:
        with self._process_lock:
            return self._process is not None and self._process.poll() is None
