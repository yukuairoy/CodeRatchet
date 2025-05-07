"""
Tests for core functionality.
"""

import os
import re
import tempfile
from pathlib import Path

import pytest

from coderatchet.core.ratchet import (
    FullFileRatchetTest,
    RatchetError,
    RegexBasedRatchetTest,
    TwoLineRatchetTest,
    TwoPassRatchetTest,
)
from coderatchet.core.utils import (
    get_ratchet_test_files,
    get_ratchet_values,
    ratchet_values_path,
    write_ratchet_counts,
)


def test_regex_based_ratchet():
    """Test basic regex-based ratchet functionality."""
    test = RegexBasedRatchetTest(
        name="test_print",
        pattern="print\\(",
        description="Test print statement detection",
        match_examples=["print('Hello')"],
        non_match_examples=["logging.info('Hello')"],
    )

    # Test with matching content
    test.collect_failures_from_lines(["print('Hello')"], "test.py")
    assert len(test.failures) == 1
    failure = test.failures[0]
    assert failure.test_name == "test_print"
    assert failure.filepath == "test.py"
    assert failure.line_number == 1
    assert failure.line_contents == "print('Hello')"

    # Test with non-matching content
    test.clear_failures()
    test.collect_failures_from_lines(["logging.info('Hello')"], "test.py")
    assert len(test.failures) == 0

    # Test example validation
    test.test_examples()


def test_two_line_ratchet():
    """Test two-line ratchet functionality."""
    test = TwoLineRatchetTest(
        name="test_import",
        pattern=r"^import\s+",  # Match 'import' at the start of the line
        description="Test import statement detection",
        match_examples=["import os"],
        non_match_examples=["from os import path"],
    )

    # Initialize the last line regex using object.__setattr__
    object.__setattr__(test, "_last_line_regex", re.compile("^$"))

    # Test with matching content
    test.collect_failures_from_lines(["import os", ""], "test.py")
    assert len(test.failures) == 1
    failure = test.failures[0]
    assert failure.test_name == "test_import"
    assert failure.filepath == "test.py"
    assert failure.line_number == 1
    assert failure.line_contents == "import os\n"

    # Test with non-matching content
    test.clear_failures()
    test.collect_failures_from_lines(["from os import path", ""], "test.py")
    assert len(test.failures) == 0


def test_full_file_ratchet():
    """Test full file ratchet functionality."""
    test = FullFileRatchetTest(
        name="test_license",
        pattern="MIT License",
        match_examples=["MIT License"],
        non_match_examples=["Apache License"],
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
            "Copyright (c) 2023",
        ],
        "test.py",
    )
    assert len(test.failures) == 0

    # Test example validation
    test.test_examples()  # Should pass


def test_two_pass_ratchet():
    """Test two-pass ratchet functionality."""
    first_pass = RegexBasedRatchetTest(
        name="first_pass",
        pattern=r"class\s+\w+",
        match_examples=["class MyClass:"],
        non_match_examples=["def my_function():"],
    )

    test = TwoPassRatchetTest(
        name="test_class_usage",
        first_pass=first_pass,
        second_pass_pattern=r"self\.\w+",
        match_examples=["self.value = 42"],
        non_match_examples=["value = 42"],
    )

    # Test matching
    test.collect_failures_from_lines(
        [
            "class MyClass:",
            "    def __init__(self):",
            "        self.value = 42",
        ],
        "test.py",
    )

    assert len(test.failures) == 1
    assert test.failures[0].line_contents == "        self.value = 42"
    assert test.failures[0].line_number == 2

    # Test non-matching
    test.clear_failures()
    test.collect_failures_from_lines(
        [
            "def my_function():",
            "    value = 42",
        ],
        "test.py",
    )
    assert len(test.failures) == 0

    # Test multiple matches
    test.clear_failures()
    test.collect_failures_from_lines(
        [
            "class FirstClass:",
            "    def __init__(self):",
            "        self.value = 42",
            "",
            "class SecondClass:",
            "    def method(self):",
            "        self.other = 'test'",
        ],
        "test.py",
    )
    assert len(test.failures) == 2
    assert test.failures[0].line_contents == "        self.value = 42"
    assert test.failures[0].line_number == 2
    assert test.failures[1].line_contents == "        self.other = 'test'"
    assert test.failures[1].line_number == 6

    # Test no matches in first pass
    test.clear_failures()
    test.collect_failures_from_lines(
        [
            "def function_one():",
            "    value = 42",
            "",
            "def function_two():",
            "    other = 'test'",
        ],
        "test.py",
    )
    assert len(test.failures) == 0

    # Test matches in first pass but not in second pass
    test.clear_failures()
    test.collect_failures_from_lines(
        [
            "class EmptyClass:",
            "    pass",
            "",
            "class SimpleClass:",
            "    def method(self):",
            "        pass",
        ],
        "test.py",
    )
    assert len(test.failures) == 0

    # Test invalid patterns
    with pytest.raises(RatchetError):
        TwoPassRatchetTest(
            name="invalid_test",
            first_pass=first_pass,
            second_pass_pattern=r"[invalid",
            match_examples=["self.value = 42"],
            non_match_examples=["value = 42"],
        )

    # Test empty lines
    test.clear_failures()
    test.collect_failures_from_lines(
        [
            "",
            "class MyClass:",
            "",
            "    def __init__(self):",
            "",
            "        self.value = 42",
            "",
        ],
        "test.py",
    )
    assert len(test.failures) == 1
    assert test.failures[0].line_contents == "        self.value = 42"
    assert test.failures[0].line_number == 5


def test_ratchet_test_examples():
    """Test ratchet test example validation."""
    # Test with correct examples
    test = RegexBasedRatchetTest(
        name="test_examples",
        pattern="foo",
        match_examples=["foo", "foobar"],
        non_match_examples=["bar", "baz"],
    )
    test.test_examples()  # Should pass

    # Test with incorrect examples
    with pytest.raises(RatchetError):
        test_bad = RegexBasedRatchetTest(
            name="test_examples",
            pattern="foo",
            match_examples=["bar"],  # Should not match
            non_match_examples=["foo"],  # Should match
        )


def test_ratchet_file_exclusion():
    """Test ratchet test file exclusion."""
    test = RegexBasedRatchetTest(
        name="test_exclusion",
        pattern="print",
        exclude_test_files=True,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        # Create test files
        test_file = tmpdir_path / "test_test.py"
        normal_file = tmpdir_path / "normal.py"

        test_file.write_text("print('test')")
        normal_file.write_text("print('normal')")

        # Save current directory
        original_dir = Path.cwd()
        try:
            # Change to temp directory
            os.chdir(tmpdir_path)

            # Test should exclude test files
            test.get_total_count_from_files([test_file, normal_file])
            assert len(test.failures) == 1
            assert test.failures[0].filepath == str(normal_file)
            assert test.failures[0].line_contents == "print('normal')"
        finally:
            # Restore original directory
            os.chdir(original_dir)


def test_ratchet_file_inclusion():
    """Test ratchet test file inclusion."""
    test = RegexBasedRatchetTest(
        name="test_inclusion",
        pattern="print",
        include_file_regex=re.compile(r"test.*\.py$"),
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        test_file = Path(tmpdir) / "test_file.py"
        normal_file = Path(tmpdir) / "normal.py"

        test_file.write_text("print('test')")
        normal_file.write_text("print('normal')")

        # Test should only include matching files
        test.get_total_count_from_files([test_file, normal_file])
        assert len(test.failures) == 1
        failure = test.failures[0]
        assert failure.test_name == "test_inclusion"
        assert failure.filepath == str(test_file)
        assert failure.line_number == 1
        assert failure.line_contents == "print('test')"

        # Test with non-matching file
        test.clear_failures()
        test.get_total_count_from_files([normal_file])
        assert len(test.failures) == 0


def test_ratchet_values():
    """Test ratchet values functionality."""
    # Save original values file if it exists
    test_file = Path(ratchet_values_path())
    original_content = None
    if test_file.exists():
        original_content = test_file.read_text()

    try:
        # Create test file
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text('{"test": 1}')

        # Test loading values
        values = get_ratchet_values()
        assert values["test"] == 1

        # Test writing values
        write_ratchet_counts({"test": 2})
        values = get_ratchet_values()
        assert values["test"] == 2
    finally:
        # Clean up
        if original_content is not None:
            test_file.write_text(original_content)
        elif test_file.exists():
            test_file.unlink()


def test_file_exclusion(tmp_path):
    """Test file exclusion functionality."""
    # Create test files
    included_file = tmp_path / "included.py"
    excluded_file = tmp_path / "excluded.py"
    included_file.write_text("print('Hello')")
    excluded_file.write_text("print('Hello')")

    # Create ratchet_excluded.txt
    exclude_file = tmp_path / "ratchet_excluded.txt"
    exclude_file.write_text("excluded.py")

    # Test file exclusion
    files = get_ratchet_test_files(additional_dirs=[tmp_path])
    assert str(included_file) in [str(f) for f in files]
    assert str(excluded_file) not in [str(f) for f in files]

    # Test negation pattern
    exclude_file.write_text("!included.py\n*.py")
    files = get_ratchet_test_files(additional_dirs=[tmp_path])
    assert str(included_file) in [str(f) for f in files]
    assert str(excluded_file) not in [str(f) for f in files]
