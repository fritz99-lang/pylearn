# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Test runner for code challenges: concatenates user code + test assertions."""

from __future__ import annotations

from dataclasses import dataclass, field

from pylearn.executor.session import Session


@dataclass
class TestResult:
    """Result of running test assertions against user code."""

    passed: bool = False
    total_tests: int = 0
    passed_tests: int = 0
    results: list[dict] = field(default_factory=list)  # [{name, passed, message}]
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    error: str = ""


class TestRunner:
    """Runs user code + test assertions through the Session executor.

    Test code should be plain Python assert statements. Each assert is wrapped
    individually so that all tests run even if earlier ones fail.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def run_tests(self, user_code: str, test_code: str) -> TestResult:
        """Execute user code followed by test assertions.

        Args:
            user_code: The user's solution code.
            test_code: Python code with assert statements to validate the solution.

        Returns:
            TestResult with per-test pass/fail information.
        """
        # Parse individual assert statements from test_code
        test_lines = self._parse_tests(test_code)

        if not test_lines:
            # No individual asserts found — run as a single block
            return self._run_single_block(user_code, test_code)

        # Build wrapped test code that reports results individually
        wrapped = self._build_wrapped_code(user_code, test_lines)
        exec_result = self._session.run(wrapped)

        if exec_result.timed_out:
            return TestResult(
                passed=False,
                timed_out=True,
                stdout=exec_result.stdout,
                stderr=exec_result.stderr,
                error="Execution timed out.",
            )

        # Parse the structured output
        return self._parse_results(exec_result.stdout, exec_result.stderr, len(test_lines))

    def _parse_tests(self, test_code: str) -> list[str]:
        """Extract individual test statements from test code.

        Each assert statement (possibly multi-line) becomes one test.
        Non-assert lines (setup code) are kept as-is and prepended to the first test.
        """
        lines = test_code.strip().splitlines()
        tests: list[str] = []
        setup: list[str] = []
        current_test: list[str] = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("assert ") or stripped.startswith("assert("):
                if current_test:
                    tests.append("\n".join(current_test))
                current_test = [line]
            elif current_test:
                # Continuation of multi-line assert
                current_test.append(line)
            elif stripped and not stripped.startswith("#"):
                setup.append(line)

        if current_test:
            tests.append("\n".join(current_test))

        # If there's setup code, prepend it to each test context
        if setup:
            setup_block = "\n".join(setup)
            tests = [setup_block + "\n" + t if tests else setup_block for t in tests]
            if not tests:
                tests = [setup_block]

        return tests

    def _build_wrapped_code(self, user_code: str, test_lines: list[str]) -> str:
        """Build code that runs user code then each test with result reporting."""
        parts = [user_code, "", "# --- Test Runner ---", "_test_results = []"]

        for i, test in enumerate(test_lines):
            # Indent test code for try block
            indented = "\n".join("    " + line for line in test.splitlines())
            parts.append(f"""try:
{indented}
    _test_results.append(("PASS", "Test {i + 1}"))
except AssertionError as _e:
    _test_results.append(("FAIL", f"Test {i + 1}: {{_e}}"))
except Exception as _e:
    _test_results.append(("ERROR", f"Test {i + 1}: {{type(_e).__name__}}: {{_e}}"))""")

        parts.append("""
for _status, _msg in _test_results:
    print(f"[{_status}] {_msg}")
_passed = sum(1 for s, _ in _test_results if s == "PASS")
_total = len(_test_results)
print(f"\\n{_passed}/{_total} tests passed")""")

        return "\n".join(parts)

    def _run_single_block(self, user_code: str, test_code: str) -> TestResult:
        """Fallback: run user_code + test_code as a single block."""
        combined = user_code + "\n\n" + test_code
        exec_result = self._session.run(combined)

        if exec_result.timed_out:
            return TestResult(
                passed=False,
                timed_out=True,
                stdout=exec_result.stdout,
                stderr=exec_result.stderr,
                error="Execution timed out.",
            )

        passed = exec_result.success
        return TestResult(
            passed=passed,
            total_tests=1,
            passed_tests=1 if passed else 0,
            results=[{"name": "Test", "passed": passed, "message": exec_result.stderr if not passed else ""}],
            stdout=exec_result.stdout,
            stderr=exec_result.stderr,
        )

    def _parse_results(self, stdout: str, stderr: str, expected_count: int) -> TestResult:
        """Parse structured test output from wrapped code."""
        results: list[dict] = []
        passed_count = 0

        for line in stdout.splitlines():
            line = line.strip()
            if line.startswith("[PASS]"):
                name = line[7:].strip()
                results.append({"name": name, "passed": True, "message": ""})
                passed_count += 1
            elif line.startswith("[FAIL]"):
                msg = line[7:].strip()
                results.append({"name": msg, "passed": False, "message": msg})
            elif line.startswith("[ERROR]"):
                msg = line[8:].strip()
                results.append({"name": msg, "passed": False, "message": msg})

        all_passed = passed_count == expected_count and len(results) == expected_count

        # If user code itself had an error (before tests ran)
        error = ""
        if stderr and not results:
            error = stderr.strip()
            all_passed = False

        return TestResult(
            passed=all_passed,
            total_tests=expected_count,
            passed_tests=passed_count,
            results=results,
            stdout=stdout,
            stderr=stderr,
            error=error,
        )
