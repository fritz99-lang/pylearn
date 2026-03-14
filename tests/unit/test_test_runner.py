# Copyright (c) 2026 Nate Tritle. Licensed under the MIT License.
"""Tests for the TestRunner class."""

from __future__ import annotations

from pylearn.executor.test_runner import TestRunner


class TestParseTests:
    """Test the _parse_tests method for splitting assert statements."""

    def setup_method(self) -> None:
        # TestRunner needs a Session, but _parse_tests doesn't use it
        self.runner = TestRunner.__new__(TestRunner)

    def test_single_assert(self) -> None:
        tests = self.runner._parse_tests("assert x == 1")
        assert len(tests) == 1
        assert "assert x == 1" in tests[0]

    def test_multiple_asserts(self) -> None:
        code = "assert x == 1\nassert y == 2\nassert z == 3"
        tests = self.runner._parse_tests(code)
        assert len(tests) == 3

    def test_assert_with_message(self) -> None:
        code = "assert x == 1, 'x should be 1'"
        tests = self.runner._parse_tests(code)
        assert len(tests) == 1
        assert "'x should be 1'" in tests[0]

    def test_setup_code_prepended(self) -> None:
        code = "expected = [1, 2, 3]\nassert result == expected"
        tests = self.runner._parse_tests(code)
        assert len(tests) == 1
        assert "expected = [1, 2, 3]" in tests[0]

    def test_comments_ignored(self) -> None:
        code = "# This is a comment\nassert x == 1"
        tests = self.runner._parse_tests(code)
        assert len(tests) == 1

    def test_empty_code(self) -> None:
        tests = self.runner._parse_tests("")
        assert len(tests) == 0


class TestBuildWrappedCode:
    """Test the code wrapping logic."""

    def setup_method(self) -> None:
        self.runner = TestRunner.__new__(TestRunner)

    def test_wraps_with_try_except(self) -> None:
        wrapped = self.runner._build_wrapped_code("x = 1", ["assert x == 1"])
        assert "try:" in wrapped
        assert "AssertionError" in wrapped  # Note: Python calls it AssertionError
        assert "_test_results" in wrapped
        assert "x = 1" in wrapped

    def test_multiple_tests_wrapped(self) -> None:
        wrapped = self.runner._build_wrapped_code("x = 1", ["assert x == 1", "assert x > 0"])
        assert wrapped.count("try:") == 2


class TestParseResults:
    """Test result parsing from structured output."""

    def setup_method(self) -> None:
        self.runner = TestRunner.__new__(TestRunner)

    def test_all_pass(self) -> None:
        stdout = "[PASS] Test 1\n[PASS] Test 2\n\n2/2 tests passed"
        result = self.runner._parse_results(stdout, "", 2)
        assert result.passed is True
        assert result.passed_tests == 2
        assert result.total_tests == 2

    def test_mixed_results(self) -> None:
        stdout = "[PASS] Test 1\n[FAIL] Test 2: x != y\n\n1/2 tests passed"
        result = self.runner._parse_results(stdout, "", 2)
        assert result.passed is False
        assert result.passed_tests == 1

    def test_error_in_user_code(self) -> None:
        result = self.runner._parse_results("", "NameError: name 'x' is not defined", 2)
        assert result.passed is False
        assert "NameError" in result.error

    def test_all_fail(self) -> None:
        stdout = "[FAIL] Test 1: wrong\n[FAIL] Test 2: wrong\n\n0/2 tests passed"
        result = self.runner._parse_results(stdout, "", 2)
        assert result.passed is False
        assert result.passed_tests == 0
