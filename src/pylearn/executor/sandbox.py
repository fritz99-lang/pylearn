"""Subprocess-based code execution with timeout and kill."""

from __future__ import annotations

import subprocess
import sys
import logging
from dataclasses import dataclass

from pylearn.core.constants import DEFAULT_EXECUTION_TIMEOUT

logger = logging.getLogger("pylearn.executor")


@dataclass
class ExecutionResult:
    """Result of running user code."""
    stdout: str = ""
    stderr: str = ""
    return_code: int = 0
    timed_out: bool = False
    killed: bool = False

    @property
    def success(self) -> bool:
        return self.return_code == 0 and not self.timed_out and not self.killed


class Sandbox:
    """Execute Python code in a subprocess with timeout."""

    def __init__(self, timeout: int = DEFAULT_EXECUTION_TIMEOUT) -> None:
        self.timeout = timeout
        self._process: subprocess.Popen | None = None

    def run(self, code: str, timeout: int | None = None) -> ExecutionResult:
        """Execute Python code in a subprocess."""
        timeout = timeout or self.timeout

        try:
            self._process = subprocess.Popen(
                [sys.executable, "-u", "-c", code],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )

            try:
                stdout, stderr = self._process.communicate(timeout=timeout)
                return ExecutionResult(
                    stdout=stdout,
                    stderr=stderr,
                    return_code=self._process.returncode,
                )
            except subprocess.TimeoutExpired:
                self._process.kill()
                stdout, stderr = self._process.communicate(timeout=5)
                return ExecutionResult(
                    stdout=stdout or "",
                    stderr=stderr or f"Execution timed out after {timeout} seconds",
                    return_code=-1,
                    timed_out=True,
                )

        except Exception as e:
            logger.error(f"Execution error: {e}")
            return ExecutionResult(
                stderr=str(e),
                return_code=-1,
            )
        finally:
            self._process = None

    def stop(self) -> bool:
        """Kill the currently running process."""
        if self._process is not None:
            try:
                self._process.kill()
                self._process = None
                return True
            except Exception as e:
                logger.error(f"Error killing process: {e}")
        return False

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None
