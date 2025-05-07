"""Tests for CI integration functionality."""

import os

from coderatchet.core.ratchet import RegexBasedRatchetTest
from coderatchet.examples.advanced.ci_integration import CIRatchetRunner


def test_ci_runner_init():
    """Test CIRatchetRunner initialization."""
    ratchets = [
        RegexBasedRatchetTest(
            name="test",
            pattern=r"print\(",
            description="Test pattern",
        )
    ]
    runner = CIRatchetRunner(ratchets, base_branch="develop", fail_on_violations=False)

    assert runner.ratchets == ratchets
    assert runner.base_branch == "develop"
    assert not runner.fail_on_violations


def test_ci_runner_no_changes(tmp_path):
    """Test CIRatchetRunner with no file changes."""
    ratchets = [
        RegexBasedRatchetTest(
            name="test",
            pattern=r"print\(",
            description="Test pattern",
        )
    ]
    runner = CIRatchetRunner(ratchets)

    # Mock git integration to return no changes
    runner.git.get_changed_files = lambda _: []

    # Run checks
    success = runner.run()
    assert success, "CI should pass when no files are changed"


def test_ci_runner_with_violations(tmp_path):
    """Test CIRatchetRunner with violations."""
    # Create test files
    file1 = tmp_path / "test1.py"
    file2 = tmp_path / "test2.py"

    file1.write_text(
        """
    print('Hello')  # Violation
    try:
        pass
    except:  # Another violation
        pass
    """
    )

    file2.write_text(
        """
    logging.info('Hello')  # No violation
    try:
        pass
    except ValueError:  # No violation
        pass
    """
    )

    # Create ratchets
    ratchets = [
        RegexBasedRatchetTest(
            name="no_print",
            pattern=r"print\(",
            description="No print statements",
        ),
        RegexBasedRatchetTest(
            name="no_bare_except",
            pattern=r"except\s*:",
            description="No bare except",
        ),
    ]

    # Test with fail_on_violations=True
    runner = CIRatchetRunner(ratchets, fail_on_violations=True)
    runner.git.get_changed_files = lambda _: [str(file1), str(file2)]

    success = runner.run()
    assert not success, "CI should fail when violations are found"

    # Test with fail_on_violations=False
    runner.fail_on_violations = False
    success = runner.run()
    assert success, "CI should pass when violations are allowed"


def test_ci_runner_non_python_files(tmp_path):
    """Test CIRatchetRunner with non-Python files."""
    # Create test files
    py_file = tmp_path / "test.py"
    txt_file = tmp_path / "test.txt"

    py_file.write_text("print('Hello')")  # Violation
    txt_file.write_text("print('Hello')")  # Should be ignored

    ratchets = [
        RegexBasedRatchetTest(
            name="no_print",
            pattern=r"print\(",
            description="No print statements",
        )
    ]

    runner = CIRatchetRunner(ratchets)
    runner.git.get_changed_files = lambda _: [str(py_file), str(txt_file)]

    success = runner.run()
    assert not success, "CI should fail due to Python file violation"


def test_ci_runner_file_errors(tmp_path):
    """Test CIRatchetRunner with file read errors."""
    # Create a file without read permissions
    file_path = tmp_path / "test.py"
    file_path.write_text("print('Hello')")
    os.chmod(file_path, 0o000)  # Remove all permissions

    ratchets = [
        RegexBasedRatchetTest(
            name="no_print",
            pattern=r"print\(",
            description="No print statements",
        )
    ]

    runner = CIRatchetRunner(ratchets)
    runner.git.get_changed_files = lambda _: [str(file_path)]

    try:
        success = runner.run()
        assert success, "CI should handle file read errors gracefully"
    finally:
        os.chmod(file_path, 0o644)  # Restore permissions
