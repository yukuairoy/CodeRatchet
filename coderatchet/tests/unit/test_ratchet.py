"""
Tests for ratchet functionality.
"""

import os
import re
import tempfile
from pathlib import Path

import pytest

from coderatchet.core.comparison import compare_ratchet_sets
from coderatchet.core.ratchet import (
    FullFileRatchetTest,
    RatchetError,
    RatchetTest,
    RegexBasedRatchetTest,
    TwoLineRatchetTest,
    TwoPassRatchetTest,
    run_ratchets_on_file,
)
from coderatchet.core.recent_failures import BrokenRatchet, get_recently_broken_ratchets
from coderatchet.core.test_failure import TestFailure
from coderatchet.core.utils import PatternManager, pattern_manager


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


def test_full_file_ratchet():
    """Test FullFileRatchetTest functionality."""
    # Create test with basic pattern
    test = FullFileRatchetTest(
        name="test",
        pattern="print\\(",
        description="Test print statements",
        match_examples=["print('Hello')"],
        non_match_examples=["logging.info('Hello')"],
    )

    # Test with matching content
    content = [
        "def function():",
        "    print('Hello')",  # Should match
        "    return True",
    ]
    test.collect_failures_from_lines(content, "test.py")
    assert len(test.failures) == 1
    failure = test.failures[0]
    assert failure.test_name == "test"
    assert failure.filepath == "test.py"
    assert failure.line_number == 1  # First line since we match the whole file
    assert failure.line_contents == "\n".join(content)

    # Test with non-matching content
    test.clear_failures()
    content = [
        "def function():",
        "    logging.info('Hello')",  # Should not match
        "    return True",
    ]
    test.collect_failures_from_lines(content, "test.py")
    assert len(test.failures) == 0

    # Test with regex flags
    test = FullFileRatchetTest(
        name="test",
        pattern="PRINT\\(",
        description="Test case-insensitive print statements",
        match_examples=["print('Hello')"],
        non_match_examples=["logging.info('Hello')"],
        regex_flags=re.IGNORECASE,
    )

    # Test case-insensitive matching
    content = [
        "def function():",
        "    PRINT('Hello')",  # Should match due to IGNORECASE flag
        "    return True",
    ]
    test.collect_failures_from_lines(content, "test.py")
    assert len(test.failures) == 1
    assert test.failures[0].line_contents == "\n".join(content)

    # Test with multiline pattern
    test = FullFileRatchetTest(
        name="test",
        pattern="def\\s+\\w+\\s*\\([^)]*\\)\\s*:",
        description="Test function definitions",
        match_examples=["def function():"],
        non_match_examples=["class MyClass:"],
    )

    # Test multiline matching
    content = [
        "def function(",  # Split across lines
        "    arg1,",
        "    arg2",
        "):",
        "    return True",
    ]
    test.collect_failures_from_lines(content, "test.py")
    assert len(test.failures) == 1
    assert test.failures[0].line_contents == "\n".join(content)

    # Test with empty file
    test.clear_failures()
    test.collect_failures_from_lines([], "test.py")
    assert len(test.failures) == 0

    # Test with invalid pattern
    with pytest.raises(RatchetError):
        FullFileRatchetTest(
            name="test",
            pattern="invalid[",  # Invalid regex
        )

    # Test with invalid example
    with pytest.raises(RatchetError):
        FullFileRatchetTest(
            name="test",
            pattern="print\\(",
            match_examples=["invalid"],  # Should match pattern
        )


def test_two_pass_ratchet():
    """Test TwoPassRatchetTest functionality."""
    # Create first pass test
    first_pass = RegexBasedRatchetTest(
        name="function_def",
        pattern=r"def\s+\w+\s*\([^)]*\)\s*:",
        match_examples=["def test():"],
        non_match_examples=["class Test:"],
    )

    # Test initialization with valid patterns
    test = TwoPassRatchetTest(
        name="function_test",
        first_pass=first_pass,
        second_pass_pattern=r"^\s*$",  # Match empty or whitespace-only lines
        match_examples=["", "    "],  # Empty line and whitespace-only line
        non_match_examples=["    print('test')", "    return True"],  # Non-empty lines
    )
    assert test.second_pass_pattern == r"^\s*$"

    # Test initialization with invalid second pass pattern
    with pytest.raises(RatchetError, match="Invalid second pass pattern"):
        TwoPassRatchetTest(
            name="invalid_test",
            first_pass=first_pass,
            second_pass_pattern="[",  # Invalid regex
            match_examples=["def test():"],
            non_match_examples=["class Test:"],
        )

    # Test failure collection
    test.clear_failures()
    test.collect_failures_from_lines(
        [
            "def test():",
            "    print('test')",  # Non-empty function
            "def empty():",
            "    ",  # Empty function with whitespace
            "def another():",
            "",  # Empty function with no content
            "def non_empty():",
            "    return True",  # Non-empty function
        ],
        "test.py",
    )
    assert len(test.failures) == 2  # Should find two empty functions

    # Test with custom second pass pattern generation
    def generate_pattern(failure: TestFailure) -> str:
        return r"^\s*$"  # Match empty or whitespace-only lines

    test = TwoPassRatchetTest(
        name="custom_test",
        first_pass=first_pass,
        second_pass_pattern=r"^\s*$",
        first_pass_failure_to_second_pass_regex_part=generate_pattern,
        first_pass_failure_filepath_for_testing="test.py",
        match_examples=["", "    "],  # Empty line and whitespace-only line
        non_match_examples=["    print('test')", "    return True"],  # Non-empty lines
    )
    test.collect_failures_from_lines(
        [
            "def test():",
            "    print('test')",  # Non-empty function
            "def empty():",
            "    ",  # Empty function with whitespace
            "def another():",
            "",  # Empty function with no content
            "def non_empty():",
            "    return True",  # Non-empty function
        ],
        "test.py",
    )
    assert len(test.failures) == 2  # Should find two empty functions


def test_pattern_manager():
    """Test PatternManager functionality."""
    manager = PatternManager()

    # Test basic pattern compilation
    pattern = manager.get_pattern("test")
    assert isinstance(pattern, re.Pattern)
    assert pattern.search("test")
    assert not pattern.search("other")

    # Test pattern caching
    pattern2 = manager.get_pattern("test")
    assert pattern is pattern2  # Should return cached pattern

    # Test pattern optimization
    pattern = manager.get_pattern("test|test")  # Should be optimized to just "test"
    assert pattern.search("test")
    assert not pattern.search("other")

    # Test pattern joining
    joined = manager.join_patterns(["test", "other"])
    assert isinstance(joined, re.Pattern)
    assert joined.search("test")
    assert joined.search("other")
    assert not joined.search("neither")

    # Test cache clearing
    manager.clear_cache()
    pattern3 = manager.get_pattern("test")
    assert pattern3 is not pattern  # Should be a new pattern after cache clear

    # Test empty pattern list
    empty = manager.join_patterns([])
    assert isinstance(empty, re.Pattern)
    assert not empty.search("anything")  # Should never match

    # Test single pattern
    single = manager.join_patterns(["test"])
    assert isinstance(single, re.Pattern)
    assert single.search("test")
    assert not single.search("other")

    # Test pattern escaping
    special = manager.get_pattern("test+")
    assert isinstance(special, re.Pattern)
    assert special.search("test+")
    assert not special.search("test")

    # Test pattern with flags
    pattern = manager.get_pattern("test", escape=False)
    assert isinstance(pattern, re.Pattern)
    assert pattern.search("test")
    assert not pattern.search("TEST")  # Case sensitive by default


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

    # Mock the necessary functions
    from unittest.mock import MagicMock, patch

    from coderatchet.core.config import RatchetConfig

    test1_config = RatchetConfig(
        name="test1",
        pattern="print",
        match_examples=["print('Hello')"],
        non_match_examples=["logging.info('Hello')"],
    )
    test2_config = RatchetConfig(
        name="test2",
        pattern="import",
        match_examples=["import os"],
        non_match_examples=["from os import path"],
    )

    def mock_get_python_files(*args, **kwargs):
        return {file1, file2}

    with patch(
        "coderatchet.core.config.load_ratchet_configs",
        return_value=[test1_config, test2_config],
    ), patch(
        "coderatchet.core.config.create_ratchet_tests",
        return_value=[test1, test2],
    ), patch(
        "coderatchet.core.utils.get_python_files",
        side_effect=mock_get_python_files,
    ), patch(
        "coderatchet.core.utils._get_exclusion_patterns",
        return_value=[],
    ), patch(
        "coderatchet.core.recent_failures.GitIntegration", MagicMock
    ):
        # Test without commit info
        failures = get_recently_broken_ratchets(limit=10, include_commits=False)
        print(f"DEBUG: Number of failures: {len(failures)}")
        print(f"DEBUG: Failure types: {[type(f).__name__ for f in failures]}")
        print(f"DEBUG: First failure: {failures[0] if failures else None}")
        assert len(failures) == 3  # Two print statements and one import
        assert all(isinstance(f, (TestFailure, BrokenRatchet)) for f in failures)
        assert all(f.test_name in ("test1", "test2") for f in failures)
        assert all(
            "print" in f.line_contents or "import" in f.line_contents for f in failures
        )

        # Verify the specific failures
        print_failures = [f for f in failures if "print" in f.line_contents]
        import_failures = [f for f in failures if "import" in f.line_contents]
        assert len(print_failures) == 2
        assert len(import_failures) == 1


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


def test_ratchet_test_base():
    """Test base RatchetTest class."""
    # Test initialization
    test = RatchetTest(
        name="test_ratchet",
        description="Test description",
        allowed_count=0,
        exclude_test_files=True,
        match_examples=("example1",),
        non_match_examples=("non_example1",),
    )
    assert test.name == "test_ratchet"
    assert test.description == "Test description"
    assert test.allowed_count == 0
    assert test.exclude_test_files is True
    assert test.match_examples == ("example1",)
    assert test.non_match_examples == ("non_example1",)
    assert len(test.failures) == 0

    # Test file inclusion/exclusion
    assert test.should_include_file("regular_file.py") is True
    assert test.should_include_file("test_file.py") is False  # Excluded as test file
    assert (
        test.should_include_file("test_something.py") is False
    )  # Excluded as test file
    assert test.should_include_file("not_a_test.py") is True

    # Test failure handling
    failure1 = TestFailure(
        test_name="test_ratchet",
        filepath="test.py",
        line_number=1,
        line_contents="example1",
    )
    failure2 = TestFailure(
        test_name="test_ratchet",
        filepath="test.py",
        line_number=2,
        line_contents="example2",
    )

    # Test adding failures
    test.add_failure(failure1)
    assert len(test.failures) == 1
    assert test.failures[0] == failure1

    test.add_failure(failure2)
    assert len(test.failures) == 2
    assert test.failures[1] == failure2

    # Test clearing failures
    test.clear_failures()
    assert len(test.failures) == 0

    # Test hash equality
    test2 = RatchetTest(
        name="test_ratchet",
        description="Test description",
        allowed_count=0,
        exclude_test_files=True,
        match_examples=("example1",),
        non_match_examples=("non_example1",),
    )
    assert hash(test) == hash(test2)

    # Test with custom include pattern
    test_with_pattern = RatchetTest(
        name="test_pattern",
        include_file_regex=re.compile(r"\.txt$"),
        match_examples=("example1",),
        non_match_examples=("non_example1",),
    )
    assert test_with_pattern.should_include_file("file.txt") is True
    assert test_with_pattern.should_include_file("file.py") is False


def test_regex_based_ratchet():
    """Test RegexBasedRatchetTest class."""
    # Test initialization with valid pattern
    test = RegexBasedRatchetTest(
        name="print_test",
        pattern=r"print\(",
        match_examples=("print('test')",),
        non_match_examples=("log('test')",),
    )
    assert test.pattern == r"print\("
    assert test.match_examples == ("print('test')",)
    assert test.non_match_examples == ("log('test')",)

    # Test failure collection
    test.clear_failures()
    test.collect_failures_from_lines(
        ["print('test')", "log('test')", "print('another test')"], "test.py"
    )
    assert len(test.failures) == 2
    assert all("print" in f.line_contents for f in test.failures)

    # Test file pattern inclusion
    test = RegexBasedRatchetTest(
        name="python_test",
        pattern=r"print\(",
        match_examples=("print('test')",),
        non_match_examples=("log('test')",),
        include_file_regex=re.compile(r"\.py$"),
    )
    assert test.should_include_file("test.py")
    assert not test.should_include_file("test.txt")


def test_file_operations():
    """Test file operations."""
    # Create test file
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as tmp:
        tmp.write(b"print('test')\nprint('another test')\n")
        tmp.flush()
        tmp.close()

        try:
            # Test run_ratchets_on_file
            test = RegexBasedRatchetTest(
                name="print_test",
                pattern=r"print\(",
                match_examples=("print('test')",),
                non_match_examples=("log('test')",),
            )
            failures = run_ratchets_on_file(tmp.name, [test])
            assert len(failures) == 2

            # Test with non-existent file
            with pytest.raises(RatchetError, match="File not found"):
                run_ratchets_on_file("nonexistent.py", [test])

            # Test with binary file
            with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as binary:
                binary.write(b"\xff\xfe\x00\x00\xff\xff\xff\xff")  # Invalid UTF-8
                binary.flush()
                binary.close()

                try:
                    with pytest.raises(
                        RatchetError,
                        match="Failed to read.*'utf-8' codec can't decode byte 0xff",
                    ):
                        test.collect_failures_from_file(binary.name)
                finally:
                    os.unlink(binary.name)

        finally:
            os.unlink(tmp.name)


def test_test_failure():
    """Test TestFailure class."""
    failure = TestFailure(
        test_name="test_ratchet",
        filepath="test.py",
        line_number=1,
        line_contents="print('test')",
    )
    assert failure.test_name == "test_ratchet"
    assert failure.filepath == "test.py"
    assert failure.line_number == 1
    assert failure.line_contents == "print('test')"

    # Test string representation
    assert str(failure) == "test.py:1: print('test')"

    # Test equality
    failure2 = TestFailure(
        test_name="test_ratchet",
        filepath="test.py",
        line_number=1,
        line_contents="print('test')",
    )
    assert failure == failure2

    failure3 = TestFailure(
        test_name="test_ratchet",
        filepath="test.py",
        line_number=2,  # Different line number
        line_contents="print('test')",
    )
    assert failure != failure3
