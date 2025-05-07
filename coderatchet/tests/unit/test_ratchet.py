"""
Tests for ratchet functionality.
"""

import re
from pathlib import Path

import pytest

from coderatchet.core.comparison import compare_ratchet_sets
from coderatchet.core.ratchet import (
    FullFileRatchetTest,
    PatternManager,
    RatchetError,
    RatchetTest,
    RegexBasedRatchetTest,
    TestFailure,
    TwoLineRatchetTest,
    TwoPassRatchetTest,
)
from coderatchet.core.recent_failures import get_recently_broken_ratchets
from coderatchet.core.utils import pattern_manager


def test_test_failure():
    """Test TestFailure dataclass."""
    failure = TestFailure(
        test_name="test1",
        filepath="test.py",
        line_number=42,
        line_contents="print('Hello')",
    )

    assert failure.test_name == "test1"
    assert failure.filepath == "test.py"
    assert failure.line_number == 42
    assert failure.line_contents == "print('Hello')"


def test_ratchet_test_basic():
    """Test basic RatchetTest functionality."""
    test = RatchetTest(
        name="test1",
        allowed_count=5,
        exclude_test_files=True,
        match_examples=("print('Hello')",),
        non_match_examples=("logging.info('Hello')",),
        description="Test print statements",
    )

    assert test.name == "test1"
    assert test.allowed_count == 5
    assert test.exclude_test_files is True
    assert test.match_examples == ("print('Hello')",)
    assert test.non_match_examples == ("logging.info('Hello')",)
    assert test.description == "Test print statements"
    assert test.failures == []

    # Test file inclusion
    assert (
        test.should_include_file(Path("test.py")) is True
    )  # Regular Python file should be included
    assert (
        test.should_include_file(Path("test_something.py")) is False
    )  # Test file should be excluded
    assert (
        test.should_include_file(Path("not_a_test.py")) is True
    )  # Regular Python file should be included


def test_ratchet_test_file_inclusion():
    """Test file inclusion patterns."""
    # Test with custom include pattern
    test = RatchetTest(
        name="test1",
        include_file_regex=re.compile(r"test.*\.py$"),
    )

    assert test.should_include_file(Path("test_file.py")) is True
    assert test.should_include_file(Path("normal.py")) is False

    # Test with exclude_test_files
    test = RatchetTest(
        name="test1",
        exclude_test_files=True,
    )

    assert test.should_include_file(Path("test_file.py")) is False
    assert test.should_include_file(Path("normal.py")) is True


def test_ratchet_test_failure_handling():
    """Test failure handling in RatchetTest."""
    test = RatchetTest(name="test1")

    # Test adding failures
    failure1 = TestFailure(
        test_name="test1",
        filepath="test.py",
        line_number=1,
        line_contents="print('Hello')",
    )
    failure2 = TestFailure(
        test_name="test1",
        filepath="test.py",
        line_number=2,
        line_contents="print('World')",
    )

    test.add_failure(failure1)
    assert len(test.failures) == 1
    assert test.failures[0] == failure1

    test.add_failure(failure2)
    assert len(test.failures) == 2
    assert test.failures[1] == failure2

    # Test clearing failures
    test.clear_failures()
    assert len(test.failures) == 0


def test_regex_based_ratchet_test():
    """Test RegexBasedRatchetTest functionality."""
    test = RegexBasedRatchetTest(
        name="test1",
        pattern="print\\(",
        match_examples=("print('Hello')",),
        non_match_examples=("logging.info('Hello')",),
    )

    # Test regex compilation
    assert test.regex.pattern == "print\\("

    # Test matching
    test.collect_failures_from_lines(["print('Hello')"], "test.py")
    assert len(test.failures) == 1
    assert test.failures[0].line_contents == "print('Hello')"

    # Test non-matching
    test.clear_failures()
    test.collect_failures_from_lines(["logging.info('Hello')"], "test.py")
    assert len(test.failures) == 0

    # Test example validation
    test.test_examples()  # Should pass

    # Test with invalid pattern
    with pytest.raises(RatchetError):
        RegexBasedRatchetTest(
            name="invalid",
            pattern="[",  # Invalid regex pattern - unclosed character class
            match_examples=("[",),
            non_match_examples=("x",),
        )


def test_two_line_ratchet_test():
    """Test TwoLineRatchetTest functionality."""
    test = TwoLineRatchetTest(
        name="test1",
        pattern="import\\s+",
        last_line_pattern="os\\.",
        match_examples=("import os", "os.path"),
        non_match_examples=("from os import path",),
    )

    # Test matching
    test.collect_failures_from_lines(["import os", "os.path"], "test.py")
    assert len(test.failures) == 1
    assert test.failures[0].line_contents == "import os\nos.path"

    # Test non-matching
    test.clear_failures()
    test.collect_failures_from_lines(["from os import path"], "test.py")
    assert len(test.failures) == 0


def test_full_file_ratchet_test():
    """Test FullFileRatchetTest functionality."""
    test = FullFileRatchetTest(
        name="test1",
        pattern="MIT License",
        match_examples=("MIT License",),
        non_match_examples=("Apache License",),
    )

    # Test matching
    test.collect_failures_from_lines(
        [
            "MIT License",
            "Copyright (c) 2023",
        ],
        "test.py",
    )
    assert len(test.failures) == 1
    assert test.failures[0].line_contents == "MIT License\nCopyright (c) 2023"

    # Test non-matching
    test.clear_failures()
    test.collect_failures_from_lines(
        [
            "Apache License",
            "Version 2.0",
        ],
        "test.py",
    )
    assert len(test.failures) == 0


def test_two_pass_ratchet_test():
    """Test TwoPassRatchetTest functionality."""
    first_pass = RegexBasedRatchetTest(
        name="first_pass",
        pattern="class\\s+\\w+",
        match_examples=("class MyClass:",),
        non_match_examples=("def my_function()",),
    )

    test = TwoPassRatchetTest(
        name="test1",
        first_pass=first_pass,
        second_pass_pattern=r"self\.\w+(?:\s*\(.*\)|\s*=.*|\s*$)",
        match_examples=("self.value = 42", "self.method()", "self.x"),
        non_match_examples=("self", "other.value"),
    )

    # Test pattern validation
    assert test._second_pass_regex.pattern == r"self\.\w+(?:\s*\(.*\)|\s*=.*|\s*$)"

    # Test matching
    test.collect_failures_from_lines(
        ["class MyClass:", "    def __init__(self):", "        self.value = 42"],
        "test.py",
    )
    assert len(test.failures) == 1
    assert test.failures[0].line_contents == "class MyClass:"

    # Test non-matching
    test.clear_failures()
    test.collect_failures_from_lines(
        [
            "class MyClass:",
            "    def __init__(self):",
            "        value = 42",  # No self.value
        ],
        "test.py",
    )
    assert len(test.failures) == 0

    # Test example validation
    test.test_examples()  # Should pass


def test_pattern_manager():
    """Test PatternManager functionality."""
    manager = PatternManager()

    # Test pattern optimization
    pattern = manager.optimize_pattern("a|b|c")
    assert pattern == "a|b|c"  # Pattern manager doesn't optimize simple patterns

    # Test pattern caching
    pattern1 = manager.get_pattern("test\\d+")
    pattern2 = manager.get_pattern("test\\d+")
    assert pattern1.pattern == pattern2.pattern  # Same pattern should be cached
    assert pattern1 is pattern2  # Same instance should be returned

    # Test cache clearing
    manager.clear_cache()
    pattern3 = manager.get_pattern("test\\d+")
    assert (
        pattern3.pattern == pattern1.pattern
    )  # After clearing cache, should get same pattern
    assert pattern3 is not pattern1  # But should be a new instance


def test_regex_join_with_or():
    """Test joining regex patterns with OR."""
    # Test basic pattern joining
    patterns = ["foo", "bar", "baz"]
    joined = pattern_manager.join_patterns(patterns)
    assert isinstance(joined, re.Pattern)
    assert joined.pattern == "(?:foo)|(?:bar)|(?:baz)"

    # Test with empty list
    empty_pattern = pattern_manager.join_patterns([])
    assert isinstance(empty_pattern, re.Pattern)
    assert empty_pattern.pattern == "(?!)"  # Never matching pattern

    # Test with single pattern
    single_pattern = pattern_manager.join_patterns(["foo"])
    assert isinstance(single_pattern, re.Pattern)
    assert single_pattern.pattern == "(?:foo)"

    # Test pattern matching
    test_pattern = pattern_manager.join_patterns(["foo", "bar"])
    assert test_pattern.search("foo") is not None
    assert test_pattern.search("bar") is not None
    assert test_pattern.search("baz") is None


def test_recent_failures(tmp_path):
    """Test recent failures detection."""
    # Create test files
    file1 = tmp_path / "test1.py"
    file2 = tmp_path / "test2.py"

    file1.write_text("print('Hello')\nimport os")
    file2.write_text("print('World')")

    # Create ratchet tests
    test1 = RegexBasedRatchetTest(
        name="test1",
        pattern="print",
        description="Test print statements",
    )
    test2 = RegexBasedRatchetTest(
        name="test2",
        pattern="import",
        description="Test imports",
    )

    # Mock the ratchet tests function and get_ratchet_test_files
    from unittest.mock import patch
    from coderatchet.core.config import get_ratchet_tests
    from coderatchet.core.utils import get_ratchet_test_files

    with patch("coderatchet.core.config.get_ratchet_tests", return_value=[test1, test2]), \
         patch("coderatchet.core.utils.get_ratchet_test_files", return_value=[file1, file2]):
        # Test without commit info
        failures = get_recently_broken_ratchets(limit=10, include_commits=False)
        assert len(failures) == 3  # Two print statements and one import
        assert all(isinstance(f, TestFailure) for f in failures)
        assert all(f.test_name in ("test1", "test2") for f in failures)
        assert all(
            "print" in f.line_contents or "import" in f.line_contents for f in failures
        )


def test_compare_ratchets():
    """Test comparing ratchets between commits."""
    # Create test ratchets
    test1_current = RegexBasedRatchetTest(
        name="test1",
        pattern="print\\(",
        match_examples=("print('Hello')",),
        non_match_examples=("logging.info('Hello')",),
    )
    test2_current = RegexBasedRatchetTest(
        name="test2",
        pattern="^import\\s+\\w+",  # Only match import statements at the start of a line
        match_examples=("import os",),
        non_match_examples=("from os import path",),
    )

    test1_previous = RegexBasedRatchetTest(
        name="test1",
        pattern="print\\(",
        match_examples=("print('Hello')",),
        non_match_examples=("logging.info('Hello')",),
    )
    test3_previous = RegexBasedRatchetTest(
        name="test3",
        pattern="assert\\s+",
        match_examples=("assert True",),
        non_match_examples=("# assert",),
    )

    # Compare ratchets
    added, removed, modified = compare_ratchet_sets(
        [test1_current, test2_current],  # Current ratchets
        [test1_previous, test3_previous],  # Previous ratchets
    )

    # Verify results
    assert len(added) == 1
    assert len(removed) == 1
    assert len(modified) == 0
    assert added[0].name == "test2"
    assert removed[0].name == "test3"
