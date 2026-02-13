"""Persistent execution session where variables carry over between runs."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import logging
from pathlib import Path

from pylearn.executor.sandbox import ExecutionResult

logger = logging.getLogger("pylearn.executor")


class Session:
    """A persistent Python session using a long-running subprocess.

    Variables and imports persist between run() calls, similar to a notebook.
    Implemented by writing code to a temp file that includes session state.
    """

    def __init__(self, timeout: int = 30) -> None:
        self.timeout = timeout
        self._namespace: dict[str, str] = {}
        self._history: list[str] = []
        self._session_file = Path(tempfile.mkdtemp()) / "session.py"
        self._process: subprocess.Popen | None = None

    def run(self, code: str) -> ExecutionResult:
        """Execute code in the session context.

        Previous imports and variable definitions are prepended so they persist.
        """
        # Build the full script: session history + new code
        full_code = "\n".join(self._history) + "\n" + code

        try:
            self._process = subprocess.Popen(
                [sys.executable, "-u", "-c", full_code],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )

            try:
                stdout, stderr = self._process.communicate(timeout=self.timeout)
                result = ExecutionResult(
                    stdout=stdout,
                    stderr=stderr,
                    return_code=self._process.returncode,
                )
                # Only add to history if it succeeded
                if result.success:
                    self._history.append(code)
                return result

            except subprocess.TimeoutExpired:
                self._process.kill()
                stdout, stderr = self._process.communicate(timeout=5)
                return ExecutionResult(
                    stdout=stdout or "",
                    stderr=f"Execution timed out after {self.timeout} seconds",
                    return_code=-1,
                    timed_out=True,
                )

        except Exception as e:
            logger.error(f"Session execution error: {e}")
            return ExecutionResult(stderr=str(e), return_code=-1)
        finally:
            self._process = None

    def stop(self) -> bool:
        """Kill the currently running process."""
        if self._process is not None:
            try:
                self._process.kill()
                self._process = None
                return True
            except Exception:
                pass
        return False

    def reset(self) -> None:
        """Clear session history."""
        self._history.clear()
        self._namespace.clear()

    @property
    def history(self) -> list[str]:
        return list(self._history)

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None
