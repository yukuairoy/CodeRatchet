"""
Tests for edge cases and complex scenarios in ratchet functionality.
"""

import os
import tempfile
from pathlib import Path

import pytest

from coderatchet.core.ratchet import (
    RegexBasedRatchetTest,
    TestFailure,
    TwoPassRatchetTest,
)
from coderatchet.core.utils import RatchetError, pattern_manager


def test_regex_based_ratchet_edge_cases():
    """Test regex ratchet with edge cases."""
    # Test with empty file
    test = RegexBasedRatchetTest(
        name="empty_file",
        pattern="print\\(",
        match_examples=["print('Hello')"],
        non_match_examples=["logging.info('Hello')"],
    )
    test.collect_failures_from_lines([], "empty.py")
    assert len(test.failures) == 0

    # Test with only comments
    test.clear_failures()
    test.collect_failures_from_lines(
        ["# This is a comment", "# Another comment"], "comments.py"
    )
    assert len(test.failures) == 0

    # Test with unicode characters
    test.clear_failures()
    test.collect_failures_from_lines(
        ["print('Hello 世界')", "print('こんにちは')"], "unicode.py"
    )
    assert len(test.failures) == 2

    # Test with different line endings
    test.clear_failures()
    test.collect_failures_from_lines(
        ["print('Hello')\r\n", "print('World')\n"], "line_endings.py"
    )
    assert len(test.failures) == 2


def test_two_pass_ratchet_complex_cases():
    """Test two-pass ratchet with complex scenarios."""
    # Test with nested functions
    test = TwoPassRatchetTest(
        name="nested_functions",
        first_pass=RegexBasedRatchetTest(
            name="function_def",
            pattern=r"def\s+\w+\s*\([^)]*\)\s*:",
            match_examples=["def outer():"],
            non_match_examples=["class MyClass:"],
        ),
        second_pass_pattern=r"^(?!\s*$).+$",  # Match any non-empty line
        first_pass_failure_to_second_pass_regex_part=lambda f: r"^(?!\s*$).+$",
        first_pass_failure_filepath_for_testing="test.py",
    )

    content = [
        "def outer():",
        "    def inner():",
        "        print('Hello')",
        "    return inner",
    ]
    test.collect_failures_from_lines(content, "nested.py")
    assert len(test.failures) > 0

    # Test with decorated functions
    test = TwoPassRatchetTest(
        name="decorated_functions",
        first_pass=RegexBasedRatchetTest(
            name="function_def",
            pattern=r"def\s+\w+\s*\([^)]*\)\s*:",
            match_examples=["@decorator\ndef func():"],
            non_match_examples=["class MyClass:"],
        ),
        second_pass_pattern=r"^(?!\s*$).+$",  # Match any non-empty line
        first_pass_failure_to_second_pass_regex_part=lambda f: r"^(?!\s*$).+$",
        first_pass_failure_filepath_for_testing="test.py",
    )

    content = [
        "@decorator",
        "def decorated():",
        "    print('Hello')",
    ]
    test.collect_failures_from_lines(content, "decorated.py")
    assert len(test.failures) > 0

    # Test with type hints
    test = TwoPassRatchetTest(
        name="type_hints",
        first_pass=RegexBasedRatchetTest(
            name="function_def",
            pattern=r"def\s+\w+\s*\([^)]*\)\s*(?:->\s*[\w\[\]]*\s*)?:",
            match_examples=["def func(x: int) -> str:"],
            non_match_examples=["class MyClass:"],
        ),
        second_pass_pattern=r"^(?!\s*$).+$",  # Match any non-empty line
        first_pass_failure_to_second_pass_regex_part=lambda f: r"^(?!\s*$).+$",
        first_pass_failure_filepath_for_testing="test.py",
    )

    content = [
        "def typed_func(x: int, y: str) -> bool:",
        "    return x > 0 and len(y) > 0",
    ]
    test.collect_failures_from_lines(content, "typed.py")
    assert len(test.failures) > 0


def test_ratchet_performance():
    """Test ratchet performance with large inputs."""
    # Test with large file
    test = RegexBasedRatchetTest(
        name="large_file",
        pattern="print\\(",
        match_examples=["print('Hello')"],
        non_match_examples=["logging.info('Hello')"],
    )

    # Generate large content
    large_content = ["print('Line {}')".format(i) for i in range(10000)]
    test.collect_failures_from_lines(large_content, "large.py")
    assert len(test.failures) == 10000

    # Test with complex pattern
    test = RegexBasedRatchetTest(
        name="complex_pattern",
        pattern=r"(?:(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,})",
        match_examples=["example.com", "sub.example.com"],
        non_match_examples=["not a domain"],
    )

    content = ["example.com", "sub.example.com", "not a domain"] * 1000
    test.collect_failures_from_lines(content, "domains.py")
    assert len(test.failures) == 2000  # Should match only valid domains


def test_ratchet_error_handling():
    """Test error handling in ratchet tests."""
    # Test with invalid file path
    test = RegexBasedRatchetTest(
        name="invalid_path",
        pattern="print\\(",
        match_examples=["print('Hello')"],
        non_match_examples=["logging.info('Hello')"],
    )

    with pytest.raises(RatchetError):
        test.collect_failures_from_file("/nonexistent/path/file.py")

    # Test with permission denied
    with tempfile.NamedTemporaryFile() as tmp:
        os.chmod(tmp.name, 0o000)  # Remove all permissions
        with pytest.raises(RatchetError):
            test.collect_failures_from_file(tmp.name)

    # Test with invalid pattern
    with pytest.raises(RatchetError):
        RegexBasedRatchetTest(
            name="invalid_pattern",
            pattern="[",  # Invalid regex
            match_examples=["["],
            non_match_examples=["x"],
        )


def test_ratchet_file_handling():
    """Test file handling in ratchet tests."""
    # Test with different file types
    test = RegexBasedRatchetTest(
        name="file_types",
        pattern="print\\(",
        match_examples=["print('Hello')"],
        non_match_examples=["logging.info('Hello')"],
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create different file types
        files = {
            "test.py": "print('Python')",
            "test.txt": "print('Text')",
            "test.md": "print('Markdown')",
        }

        for filename, content in files.items():
            filepath = Path(tmpdir) / filename
            filepath.write_text(content)
            test.collect_failures_from_file(str(filepath))
            assert len(test.failures) > 0
            test.clear_failures()

    # Test with binary files
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as tmp:
        # Write complex binary data that will definitely cause a UnicodeDecodeError
        tmp.write(b"\xff\xfe\x00\x00\xff\xff\xff\xff")  # Invalid UTF-8 sequence
        tmp.flush()
        tmp.close()  # Ensure file is closed before testing
        try:
            test.collect_failures_from_file(tmp.name)
            pytest.fail("Expected RatchetError for binary file")
        except RatchetError as e:
            assert "Failed to read" in str(e)
            assert "codec can't decode" in str(
                e
            )  # More flexible check for decode error
        finally:
            os.unlink(tmp.name)  # Clean up the temporary file
