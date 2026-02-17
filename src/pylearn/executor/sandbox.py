# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Subprocess-based code execution with timeout and kill."""

from __future__ import annotations

import glob as _glob_mod
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import uuid
import webbrowser
from dataclasses import dataclass
from pathlib import Path

from pylearn.core.constants import DEFAULT_EXECUTION_TIMEOUT, DATA_DIR, get_python_executable

logger = logging.getLogger("pylearn.executor")

# _CREATE_NO_WINDOW only exists on Windows; default to 0 on other platforms.
_CREATE_NO_WINDOW: int = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# Maximum chars of stdout/stderr to capture before truncating
_MAX_OUTPUT_CHARS = 2 * 1024 * 1024  # 2M characters

# Locate C++ compiler
_CPP_COMPILER = shutil.which("g++") or shutil.which("clang++") or ""

# Scratch directory for subprocess cwd (isolates relative-path operations)
_SCRATCH_DIR = DATA_DIR / "scratch"
_SCRATCH_DIR.mkdir(parents=True, exist_ok=True)

# Environment variables to strip from child processes
_SENSITIVE_ENV_VARS = {
    "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN",
    "AZURE_CLIENT_SECRET", "GCP_SERVICE_ACCOUNT_KEY",
    "DATABASE_URL", "DB_PASSWORD", "GITHUB_TOKEN", "GH_TOKEN",
    "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "API_KEY", "SECRET_KEY",
    "PRIVATE_KEY",
}

# Advisory warning patterns — NOT a security sandbox. User code runs with full privileges.
# These patterns catch common dangerous operations to show a confirmation dialog.
_DANGER_PATTERNS = [
    (re.compile(r'\bos\.system\b'), "os.system()"),
    (re.compile(r'\bos\.remove\b|\bos\.unlink\b'), "os.remove()/unlink()"),
    (re.compile(r'\bshutil\.rmtree\b'), "shutil.rmtree()"),
    (re.compile(r'\bsubprocess\.(call|run|Popen)\b'), "subprocess execution"),
    (re.compile(r'\b__import__\b'), "__import__()"),
    (re.compile(r'\bos\.rmdir\b'), "os.rmdir()"),
    (re.compile(r'\bos\.rename\b'), "os.rename()"),
    (re.compile(r"\bopen\s*\(.*['\"]w['\"]"), "file write via open()"),
    (re.compile(r'\bpathlib\.Path.*\.unlink\b|\bPath.*\.unlink\b'), "Path.unlink()"),
    (re.compile(r'\bsocket\b'), "socket (network access)"),
    (re.compile(r'\bhttp\.client\b|\burllib\.request\b'), "HTTP network access"),
    (re.compile(r'\beval\s*\('), "eval()"),
    (re.compile(r'\bexec\s*\('), "exec()"),
    (re.compile(r'\bctypes\b'), "ctypes (native code access)"),
    (re.compile(r'\bimportlib\b'), "importlib (dynamic import)"),
    (re.compile(r'getattr\s*\('), "getattr() (attribute access bypass)"),
    (re.compile(r'__builtins__'), "__builtins__ (builtin access)"),
]


def get_safe_env() -> dict[str, str]:
    """Return a copy of os.environ with sensitive variables stripped."""
    env = os.environ.copy()
    for var in _SENSITIVE_ENV_VARS:
        env.pop(var, None)
    return env


def check_dangerous_code(code: str) -> list[str]:
    """Return list of warnings if code contains potentially dangerous patterns."""
    warnings = []
    for pattern, desc in _DANGER_PATTERNS:
        if pattern.search(code):
            warnings.append(desc)
    return warnings


def _kill_tree(proc: subprocess.Popen) -> None:
    """Kill a process and all its children. Falls back to proc.kill()."""
    try:
        if sys.platform == "win32":
            # taskkill /T kills the entire process tree
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
                creationflags=_CREATE_NO_WINDOW,
            )
        else:
            proc.kill()
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


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
    """Execute code in a subprocess with timeout. Supports Python, C++, and HTML."""

    _html_first_open = True  # Track first browser open for status message

    def __init__(self, timeout: int = DEFAULT_EXECUTION_TIMEOUT) -> None:
        self.timeout = timeout
        self._process: subprocess.Popen | None = None
        self._process_lock = threading.Lock()

    def run(self, code: str, language: str = "python",
            timeout: int | None = None) -> ExecutionResult:
        """Execute code in a subprocess."""
        if language == "html":
            return self._run_html(code, timeout)
        if language in ("cpp", "c"):
            return self._run_cpp(code, timeout)
        return self._run_python(code, timeout)

    def _run_python(self, code: str, timeout: int | None = None) -> ExecutionResult:
        """Execute Python code."""
        timeout = timeout or self.timeout
        python = get_python_executable()
        if not python:
            return ExecutionResult(
                stderr="No Python interpreter found. Install Python and add it to PATH.",
                return_code=-1,
            )
        try:
            with self._process_lock:
                self._process = subprocess.Popen(
                    [python, "-u", "-c", code],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=str(_SCRATCH_DIR),
                    env=get_safe_env(),
                    creationflags=_CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                )
            return self._wait(self._process, timeout)
        except Exception as e:
            logger.error(f"Python execution error: {e}")
            return ExecutionResult(stderr=str(e), return_code=-1)
        finally:
            with self._process_lock:
                self._process = None

    def _run_html(self, code: str, timeout: int | None = None) -> ExecutionResult:
        """Write HTML to a file and open it in the default browser."""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)

            # Clean up old preview files
            for old in _glob_mod.glob(str(DATA_DIR / "preview_*.html")):
                try:
                    Path(old).unlink()
                except OSError:
                    pass

            preview_path = DATA_DIR / f"preview_{uuid.uuid4().hex[:8]}.html"

            # Inject a CSP meta tag into the HTML head for basic content policy
            if "<head>" in code.lower():
                csp_tag = (
                    '<meta http-equiv="Content-Security-Policy" '
                    'content="default-src \'self\' \'unsafe-inline\'; '
                    'script-src \'unsafe-inline\';">'
                )
                # Insert CSP right after <head>
                idx = code.lower().index("<head>")
                insert_pos = idx + len("<head>")
                code = code[:insert_pos] + "\n" + csp_tag + "\n" + code[insert_pos:]

            preview_path.write_text(code, encoding="utf-8")

            # Always open — on most browsers this refreshes the existing tab
            # for the same file:// URL rather than opening a new one.
            webbrowser.open(preview_path.as_uri())

            if Sandbox._html_first_open:
                Sandbox._html_first_open = False
                msg = f"Opened in browser: {preview_path}"
            else:
                msg = f"Updated and refreshed: {preview_path}"
            return ExecutionResult(stdout=msg, return_code=0)
        except Exception as e:
            logger.error(f"HTML preview error: {e}")
            return ExecutionResult(stderr=str(e), return_code=-1)

    def _run_cpp(self, code: str, timeout: int | None = None) -> ExecutionResult:
        """Compile and execute C++ code."""
        timeout = timeout or self.timeout

        if not _CPP_COMPILER:
            return ExecutionResult(
                stderr="No C++ compiler found. Install g++ or clang++ and add to PATH.",
                return_code=-1,
            )

        # Write source to temp file
        tmp_dir = Path(tempfile.mkdtemp(prefix="pylearn_"))
        src_file = tmp_dir / "main.cpp"
        exe_file = tmp_dir / ("main.exe" if sys.platform == "win32" else "main")

        try:
            src_file.write_text(code, encoding="utf-8")

            # Compile
            compile_result = subprocess.run(
                [_CPP_COMPILER, str(src_file), "-o", str(exe_file),
                 "-std=c++17", "-Wall"],
                capture_output=True, text=True, timeout=30,
                env=get_safe_env(),
                creationflags=_CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )

            if compile_result.returncode != 0:
                return ExecutionResult(
                    stderr=f"Compilation failed:\n{compile_result.stderr}",
                    return_code=compile_result.returncode,
                )

            # Run
            with self._process_lock:
                self._process = subprocess.Popen(
                    [str(exe_file)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=str(tmp_dir),
                    env=get_safe_env(),
                    creationflags=_CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                )
            result = self._wait(self._process, timeout)

            # Prepend compilation success note if there were warnings
            if compile_result.stderr.strip():
                result.stderr = f"Compiler warnings:\n{compile_result.stderr}\n{result.stderr}"

            return result

        except subprocess.TimeoutExpired:
            return ExecutionResult(
                stderr="Compilation timed out after 30 seconds",
                return_code=-1, timed_out=True,
            )
        except Exception as e:
            logger.error(f"C++ execution error: {e}")
            return ExecutionResult(stderr=str(e), return_code=-1)
        finally:
            with self._process_lock:
                self._process = None
            # Clean up temp directory and all contents
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def _wait(self, proc: subprocess.Popen, timeout: int) -> ExecutionResult:
        """Wait for a process to finish, capping output size."""
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
            # Truncate if output exceeds limit
            if len(stdout) > _MAX_OUTPUT_CHARS:
                stdout = stdout[:_MAX_OUTPUT_CHARS] + "\n[output truncated — exceeded 2 MB limit]"
            if len(stderr) > _MAX_OUTPUT_CHARS:
                stderr = stderr[:_MAX_OUTPUT_CHARS] + "\n[stderr truncated — exceeded 2 MB limit]"
            return ExecutionResult(
                stdout=stdout,
                stderr=stderr,
                return_code=proc.returncode,
            )
        except subprocess.TimeoutExpired:
            _kill_tree(proc)
            try:
                stdout, stderr = proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                stdout, stderr = "", "Process could not be terminated"
                try:
                    proc.kill()
                except OSError:
                    pass
            return ExecutionResult(
                stdout=stdout or "",
                stderr=stderr or f"Execution timed out after {timeout} seconds",
                return_code=-1,
                timed_out=True,
            )

    def stop(self) -> bool:
        """Kill the currently running process."""
        with self._process_lock:
            if self._process is not None:
                try:
                    self._process.kill()
                    return True
                except Exception as e:
                    logger.error(f"Error killing process: {e}")
        return False

    @property
    def is_running(self) -> bool:
        with self._process_lock:
            return self._process is not None and self._process.poll() is None

    @staticmethod
    def has_cpp_compiler() -> bool:
        return bool(_CPP_COMPILER)

    @staticmethod
    def cpp_compiler_path() -> str:
        return _CPP_COMPILER
