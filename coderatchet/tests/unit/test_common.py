"""
Common test functions shared across multiple test modules.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from coderatchet.core.ratchet import RegexBasedRatchetTest
from coderatchet.core.utils import get_ratchet_test_files, should_exclude_file
from coderatchet.core.config import get_ratchet_tests


def test_should_exclude_file():
    """Test file exclusion logic."""
    # Test basic patterns
    assert should_exclude_file("test.pyc", ["*.pyc"]) is True
    assert should_exclude_file("test.py", ["*.pyc"]) is False

    # Test directory patterns
    assert should_exclude_file("venv/lib/test.py", ["venv/"]) is True
    assert should_exclude_file("other/lib/test.py", ["venv/"]) is False

    # Test negation patterns
    assert should_exclude_file("test.py", ["!test.py"]) is False
    assert should_exclude_file("other.py", ["!test.py"]) is False

    # Test multiple patterns
    patterns = ["*.pyc", "venv/", "!test.py"]
    assert should_exclude_file("test.pyc", patterns) is True  # Matches *.pyc
    assert should_exclude_file("venv/lib/test.py", patterns) is True  # Matches venv/
    assert should_exclude_file("test.py", patterns) is False  # Matches !test.py
    assert should_exclude_file("other.py", patterns) is False


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

    # Save current directory
    original_dir = Path.cwd()
    try:
        # Change to temp directory
        os.chdir(tmp_path)

        # Test file exclusion
        files = get_ratchet_test_files()
        file_paths = [str(f) for f in files]
        assert any(
            "included.py" in p for p in file_paths
        ), "included.py should be found"
        assert not any(
            "excluded.py" in p for p in file_paths
        ), "excluded.py should be excluded"
    finally:
        # Restore original directory
        os.chdir(original_dir)


def test_get_ratchet_tests():
    """Test getting ratchet tests from configs."""
    # Create mock configs
    mock_config1 = MagicMock()
    mock_config2 = MagicMock()

    # Create mock ratchet tests
    test1 = RegexBasedRatchetTest(
        name="test1",
        pattern="print\\(",
        match_examples=("print('Hello')",),
        non_match_examples=("logging.info('Hello')",),
    )
    test2 = RegexBasedRatchetTest(
        name="test2",
        pattern=r"^import\s+\w+$",  # Only match simple import statements
        match_examples=("import os",),
        non_match_examples=("from os import path",),
    )

    # Mock the config loading and test creation
    with patch(
        "coderatchet.core.config.load_ratchet_configs"
    ) as mock_load_configs, patch(
        "coderatchet.core.config.create_ratchet_tests"
    ) as mock_create_tests:
        # Test with empty configs
        mock_load_configs.return_value = []
        mock_create_tests.return_value = []
        tests = get_ratchet_tests()
        assert len(tests) == 0
        assert isinstance(tests, list)

        # Test with single config (list return)
        mock_load_configs.return_value = [mock_config1]
        mock_create_tests.return_value = [test1]
        tests = get_ratchet_tests()
        assert len(tests) == 1
        assert isinstance(tests, list)
        assert tests[0].name == "test1"

        # Test with single config (set return)
        tests = get_ratchet_tests(return_set=True)
        assert len(tests) == 1
        assert isinstance(tests, set)
        assert next(iter(tests)).name == "test1"

        # Test with multiple configs (list return)
        mock_load_configs.return_value = [mock_config1, mock_config2]
        mock_create_tests.return_value = [test1, test2]
        tests = get_ratchet_tests()
        assert len(tests) == 2
        assert isinstance(tests, list)
        test_names = {t.name for t in tests}
        assert test_names == {"test1", "test2"}

        # Test with multiple configs (set return)
        tests = get_ratchet_tests(return_set=True)
        assert len(tests) == 2
        assert isinstance(tests, set)
        test_names = {t.name for t in tests}
        assert test_names == {"test1", "test2"}
