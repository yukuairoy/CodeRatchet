"""
Tests for utility functions.
"""

import json
import os
import re
import tempfile
from pathlib import Path
from unittest.mock import patch

from coderatchet.core.utils import (
    TestFailure,
    _read_exclude_patterns,
    file_path_to_module_path,
    get_python_files,
    get_ratchet_test_files,
    get_ratchet_values,
    join_regex_patterns,
    load_ratchet_count,
    ratchet_values_path,
    should_exclude_file,
    write_ratchet_counts,
)


def test_should_exclude_file():
    """Test file exclusion logic."""
    # Test basic exclusion
    assert should_exclude_file("test.py", ["*.py"]) == True
    assert should_exclude_file("test.txt", ["*.py"]) == False

    # Test directory exclusion
    assert should_exclude_file("tests/test.py", ["tests/*"]) == True
    assert should_exclude_file("src/test.py", ["tests/*"]) == False

    # Test negation patterns
    assert should_exclude_file("test.py", ["!test.py", "*.py"]) == False
    assert should_exclude_file("other.py", ["!test.py", "*.py"]) == True

    # Test multiple patterns
    assert should_exclude_file("test.py", ["*.txt", "*.py"]) == True
    assert should_exclude_file("test.txt", ["*.txt", "*.py"]) == True
    assert should_exclude_file("test.md", ["*.txt", "*.py"]) == False

    # Test Windows paths
    assert should_exclude_file("tests\\test.py", ["tests/*"]) == True
    assert should_exclude_file("src\\test.py", ["tests/*"]) == False

    # Test with default patterns
    assert should_exclude_file("test.pyc", ["*.pyc"]) is True
    assert should_exclude_file("test.py", ["*.pyc"]) is False

    # Test with directory patterns
    assert should_exclude_file("venv/lib/test.py", ["venv/"]) is True
    assert should_exclude_file("other/lib/test.py", ["venv/"]) is False

    # Test with multiple patterns including negation
    patterns = ["*.pyc", "venv/", "!test.py"]
    assert should_exclude_file("test.pyc", patterns) is True  # Matches *.pyc
    assert should_exclude_file("venv/lib/test.py", patterns) is True  # Matches venv/
    assert should_exclude_file("test.py", patterns) is False  # Matches !test.py
    assert (
        should_exclude_file("other.py", patterns) is True
    )  # No match, but has negation


def test_get_python_files():
    """Test getting Python files from a directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create Python files
        file1 = tmpdir_path / "test1.py"
        file2 = tmpdir_path / "test2.py"
        file3 = tmpdir_path / "subdir/test3.py"

        file1.write_text("print('Hello')")
        file2.write_text("print('World')")
        file3.parent.mkdir()
        file3.write_text("print('Subdir')")

        # Create non-Python files
        (tmpdir_path / "not_python.txt").write_text("Not a Python file")

        # Test getting Python files as list (default)
        files = get_python_files(tmpdir_path)
        assert isinstance(files, list)
        assert len(files) == 3
        assert {f.name for f in files} == {"test1.py", "test2.py", "test3.py"}

        # Test getting Python files as set
        files_set = get_python_files(tmpdir_path, return_set=True)
        assert isinstance(files_set, set)
        assert len(files_set) == 3
        assert {f.name for f in files_set} == {"test1.py", "test2.py", "test3.py"}

        # Test with symlink
        symlink = tmpdir_path / "symlink.py"
        symlink.symlink_to(file1)
        files = get_python_files(tmpdir_path)
        assert len(files) == 3  # Symlink should be excluded


def test_read_exclude_patterns():
    """Test reading exclusion patterns from a file."""
    with tempfile.NamedTemporaryFile(mode="w") as f:
        # Write patterns to file
        f.write(
            """
        # Comment line
        *.pyc
        __pycache__/
        "venv/"
        'build/'
        test_*.py
        """
        )
        f.flush()

        # Test reading patterns
        patterns = _read_exclude_patterns(f.name)
        assert patterns == [
            "*.pyc",
            "__pycache__/",
            "venv/",
            "build/",
            "test_*.py",
        ]

        # Test with base directory
        base_dir = Path("/base/dir")
        patterns = _read_exclude_patterns(f.name, base_dir)
        assert patterns == [
            "*.pyc",
            "__pycache__/",
            "venv/",
            "build/",
            "test_*.py",
        ]

        # Test with non-existent file
        patterns = _read_exclude_patterns("nonexistent.txt")
        assert patterns == []


def test_get_ratchet_test_files(tmp_path):
    """Test getting ratchet test files."""
    # Create test files
    file1 = tmp_path / "test1.py"
    file2 = tmp_path / "test2.py"
    file3 = tmp_path / "test3.txt"
    file4 = tmp_path / "test4.pyc"
    file5 = tmp_path / "__pycache__/test5.py"
    file6 = tmp_path / "venv/test6.py"
    file7 = tmp_path / "important.py"

    # Create directories
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "venv").mkdir()

    file1.write_text("print('foo')")
    file2.write_text("print('bar')")
    file3.write_text("print('baz')")
    file4.write_text("print('qux')")
    file5.write_text("print('quux')")
    file6.write_text("print('corge')")
    file7.write_text("print('grault')")

    # Create exclusion file with patterns
    exclude_file = tmp_path / "ratchet_excluded.txt"
    exclude_file.write_text(
        """
    # Exclude patterns
    *.pyc
    __pycache__
    venv/
    !important.py
    test2.py
    """
    )

    # Change to temporary directory
    original_dir = Path.cwd()
    os.chdir(tmp_path)
    try:
        # Test file collection
        files = get_ratchet_test_files()
        assert len(files) == 2  # Only important.py and test1.py should be included
        assert str(file7) in [str(f) for f in files]
        assert str(file1) in [str(f) for f in files]
    finally:
        os.chdir(original_dir)


def test_ratchet_values_path():
    """Test getting ratchet values file path."""
    path = ratchet_values_path()
    assert path.endswith("ratchet_values.json")
    assert os.path.isabs(path)


def test_get_ratchet_values(tmp_path):
    """Test getting ratchet values."""
    values = {"test1": 5, "test2": 3}
    mock_path = str(tmp_path / "ratchet_values.json")

    with patch("coderatchet.core.utils.ratchet_values_path", return_value=mock_path):
        # Test non-existent file
        assert get_ratchet_values() == {}

        # Test valid file
        with open(mock_path, "w") as f:
            json.dump(values, f)
        assert get_ratchet_values() == values

        # Test invalid JSON
        with open(mock_path, "w") as f:
            f.write("invalid json")
        assert get_ratchet_values() == {}


def test_load_ratchet_count(tmp_path):
    """Test loading ratchet count."""
    values = {"test1": 5, "test2": 3}
    mock_path = str(tmp_path / "ratchet_values.json")

    with patch("coderatchet.core.utils.ratchet_values_path", return_value=mock_path):
        with open(mock_path, "w") as f:
            json.dump(values, f)

        assert load_ratchet_count("test1") == 5
        assert load_ratchet_count("test2") == 3
        assert load_ratchet_count("nonexistent") == 0


def test_write_ratchet_counts(tmp_path):
    """Test writing ratchet counts."""
    mock_path = str(tmp_path / "ratchet_values.json")
    counts = {"test1": 5, "test2": 3}

    with patch("coderatchet.core.utils.ratchet_values_path", return_value=mock_path):
        write_ratchet_counts(counts)
        with open(mock_path) as f:
            saved_counts = json.load(f)
        assert saved_counts == counts


def test_file_path_to_module_path():
    """Test converting file paths to module paths."""
    assert file_path_to_module_path("test.py") == "test"
    assert file_path_to_module_path("dir/test.py") == "dir.test"
    assert file_path_to_module_path("dir/subdir/test.py") == "dir.subdir.test"
    assert file_path_to_module_path("/abs/path/test.py") == "abs.path.test"
    assert file_path_to_module_path("C:/path/test.py") == "path.test"
    assert file_path_to_module_path("test.txt") == "test"


def test_test_failure():
    """Test TestFailure class."""
    failure = TestFailure(
        test_name="test1",
        filepath="test.py",
        line_number=42,
        line_contents="print('error')",
    )

    assert failure.test_name == "test1"
    assert failure.filepath == "test.py"
    assert failure.line_number == 42
    assert failure.line_contents == "print('error')"
    assert str(failure) == "test.py:42: print('error')"


def test_join_regex_patterns():
    """Test joining regex patterns."""
    # Test basic joining
    pattern = join_regex_patterns(["a", "b", "c"])
    assert isinstance(pattern, re.Pattern)
    assert pattern.match("a")
    assert pattern.match("b")
    assert pattern.match("c")
    assert not pattern.match("d")

    # Test with empty list
    pattern = join_regex_patterns([])
    assert isinstance(pattern, re.Pattern)
    assert not pattern.match("")
    assert not pattern.match("anything")

    # Test with single pattern
    pattern = join_regex_patterns(["test"])
    assert isinstance(pattern, re.Pattern)
    assert pattern.match("test")
    assert not pattern.match("other")

    # Test with special characters
    pattern = join_regex_patterns(["a.b", "c.d"], escape=True)
    assert isinstance(pattern, re.Pattern)
    assert pattern.match("a.b")
    assert pattern.match("c.d")
    assert not pattern.match("ab")
    assert not pattern.match("cd")


# Remove duplicate tests that have been moved to test_common.py
