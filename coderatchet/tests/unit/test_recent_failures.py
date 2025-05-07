"""
Tests for recent failures functionality.
"""

import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from coderatchet.core.config import RatchetConfig, get_ratchet_tests
from coderatchet.core.git_integration import GitIntegration
from coderatchet.core.ratchet import RegexBasedRatchetTest, TestFailure
from coderatchet.core.recent_failures import (
    BrokenRatchet,
    GitHistoryManager,
    get_recently_broken_ratchets,
)


def test_get_recently_broken_ratchets(tmp_path):
    """Test getting recently broken ratchets."""
    # Save current directory
    original_dir = Path.cwd()
    try:
        # Change to temp directory
        os.chdir(tmp_path)

        # Initialize git repository
        subprocess.run(["git", "init"], check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], check=True)

        # Create test files
        test_file = tmp_path / "test.py"
        test_file.write_text("print('Hello')\nprint('World')")

        # Add and commit files
        subprocess.run(["git", "add", "test.py"], check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], check=True)

        # Create a ratchet test
        test = RegexBasedRatchetTest(
            name="no_print",
            pattern=r"print\(",
            match_examples=("print('Hello')",),
            non_match_examples=("logging.info('Hello')",),
        )

        # Mock the ratchet tests function and git integration
        with patch(
            "coderatchet.core.recent_failures.get_ratchet_tests"
        ) as mock_get_tests:
            mock_get_tests.return_value = {test}

            # Create mock GitIntegration
            mock_git = MagicMock(spec=GitIntegration)
            mock_git._run_git_command.return_value.stdout = (
                "abc123 1672531200 Initial commit"
            )
            mock_git.get_commit_info.return_value = (
                datetime(2023, 1, 1, tzinfo=timezone.utc),
                "Initial commit",
            )

            # Test without commit info
            failures = get_recently_broken_ratchets(limit=10, include_commits=False)
            assert len(failures) == 2  # Two print statements

            # Test with commit info
            failures = get_recently_broken_ratchets(
                limit=10, include_commits=True, git_integration=mock_git
            )
            assert len(failures) == 2  # Two print statements

            # Verify commit info
            for failure in failures:
                assert isinstance(failure, BrokenRatchet)
                assert failure.commit_hash == "abc123"
                assert failure.commit_date == datetime(2023, 1, 1, tzinfo=timezone.utc)
                assert failure.commit_message == "Initial commit"

    finally:
        # Restore original directory
        os.chdir(original_dir)


def test_get_git_history():
    """Test getting git history."""
    # Create mock GitIntegration
    mock_git = MagicMock(spec=GitIntegration)
    mock_output = "abc123def456789012345678901234567890abcdef 1672531200 Fix test1\ndef456abc789012345678901234567890abcdef123 1672617600 Fix test2"
    mock_git._run_git_command.return_value.stdout = mock_output

    # Create GitHistoryManager with mock
    git_manager = GitHistoryManager(mock_git)

    # Test normal operation
    history = git_manager.get_history()
    assert len(history) == 2
    # Compare timestamps in UTC to avoid timezone issues
    assert history[0][0] == "abc123def456789012345678901234567890abcdef"
    assert history[0][1].astimezone(timezone.utc) == datetime(
        2023, 1, 1, tzinfo=timezone.utc
    )
    assert history[0][2] == "Fix test1"
    assert history[1][0] == "def456abc789012345678901234567890abcdef123"
    assert history[1][1].astimezone(timezone.utc) == datetime(
        2023, 1, 2, tzinfo=timezone.utc
    )
    assert history[1][2] == "Fix test2"

    # Test with since_commit
    history = git_manager.get_history("abc123def456789012345678901234567890abcdef")
    assert len(history) == 2

    # Test with error
    mock_git._run_git_command.side_effect = subprocess.CalledProcessError(1, "git log")
    history = git_manager.get_history()
    assert len(history) == 0

    # Test with invalid timestamp
    mock_git._run_git_command.side_effect = None
    mock_git._run_git_command.return_value.stdout = (
        "abc123def456789012345678901234567890abcdef invalid_timestamp Fix test1"
    )
    history = git_manager.get_history()
    assert len(history) == 0

    # Test with malformed line
    mock_git._run_git_command.return_value.stdout = "abc123def456789012345678901234567890abcdef 1672531200"  # Missing commit message
    history = git_manager.get_history()
    assert len(history) == 0


def test_get_file_commits():
    """Test getting file commits."""
    history = [
        ("abc123", datetime(2023, 1, 1), "Fix test1"),
        ("def456", datetime(2023, 1, 2), "Fix test2"),
    ]

    # Create mock GitIntegration
    mock_git = MagicMock(spec=GitIntegration)
    mock_output = """abc123 1672531200 Fix test1
def456 1672617600 Fix test2"""
    mock_git._run_git_command.return_value.stdout = mock_output

    # Create GitHistoryManager with mock
    git_manager = GitHistoryManager(mock_git)

    commits = git_manager.get_file_commits("test.py", history)
    assert len(commits) == 2
    assert commits[0] == ("abc123", datetime(2023, 1, 1), "Fix test1")
    assert commits[1] == ("def456", datetime(2023, 1, 2), "Fix test2")


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
    with patch(
        "coderatchet.core.recent_failures.get_ratchet_tests"
    ) as mock_get_tests, patch(
        "coderatchet.core.recent_failures.get_ratchet_test_files"
    ) as mock_get_files:
        mock_get_tests.return_value = {test1, test2}
        mock_get_files.return_value = [file1, file2]

        # Test without commit info
        failures = get_recently_broken_ratchets(limit=10, include_commits=False)
        assert len(failures) == 3  # Two print statements and one import

        # Verify failures
        assert all(
            "print" in f.line_contents or "import" in f.line_contents for f in failures
        )


def test_broken_ratchet():
    """Test BrokenRatchet class."""
    # Test with all fields
    ratchet = BrokenRatchet(
        test_name="test1",
        filepath="test.py",
        line_number=42,
        line_contents="print('error')",
        commit_hash="abc123",
        commit_date=datetime(2024, 1, 1),
        commit_message="Fix test",
    )
    assert ratchet.test_name == "test1"
    assert ratchet.filepath == "test.py"
    assert ratchet.line_number == 42
    assert ratchet.line_contents == "print('error')"
    assert ratchet.commit_hash == "abc123"
    assert ratchet.commit_date == datetime(2024, 1, 1)
    assert ratchet.commit_message == "Fix test"

    # Test with minimal fields
    ratchet = BrokenRatchet(
        test_name="test2",
        filepath="test2.py",
        line_number=43,
        line_contents="print('error2')",
    )
    assert ratchet.test_name == "test2"
    assert ratchet.filepath == "test2.py"
    assert ratchet.line_number == 43
    assert ratchet.line_contents == "print('error2')"
    assert ratchet.commit_hash is None
    assert ratchet.commit_date is None
    assert ratchet.commit_message is None


def test_get_file_commits_error_handling():
    """Test error handling in get_file_commits."""
    history = [
        ("abc123def", datetime(2023, 1, 1), "Fix test1"),
        ("def456abc", datetime(2023, 1, 2), "Fix test2"),
    ]

    # Create mock GitIntegration
    mock_git = MagicMock(spec=GitIntegration)
    git_manager = GitHistoryManager(mock_git)

    # Test with non-existent file
    mock_git._run_git_command.side_effect = subprocess.CalledProcessError(
        128, "git log", b"fatal: no such path 'nonexistent.py'"
    )
    commits = git_manager.get_file_commits("nonexistent.py", history)
    assert len(commits) == 0

    # Test with malformed git output
    mock_git._run_git_command.side_effect = None
    mock_git._run_git_command.return_value.stdout = "not a valid commit line"
    commits = git_manager.get_file_commits("test.py", history)
    assert len(commits) == 0

    # Test with partial match to history
    mock_git._run_git_command.return_value.stdout = "abc123def 1672531200 Fix test1"
    commits = git_manager.get_file_commits("test.py", history)
    assert len(commits) == 1
    assert commits[0][0] == "abc123def"  # Should match the full hash from history


def test_get_git_history_error_handling():
    """Test error handling in get_git_history."""
    # Create mock GitIntegration
    mock_git = MagicMock(spec=GitIntegration)
    git_manager = GitHistoryManager(mock_git)

    # Test with non-existent commit
    mock_git._run_git_command.side_effect = subprocess.CalledProcessError(
        128, "git log", b"fatal: bad revision 'nonexistent'"
    )
    history = git_manager.get_history(since_commit="nonexistent")
    assert len(history) == 0

    # Test with invalid git command
    mock_git._run_git_command.side_effect = subprocess.CalledProcessError(
        1, "git log", b"fatal: not a git repository"
    )
    history = git_manager.get_history()
    assert len(history) == 0

    # Test with malformed git output
    mock_git._run_git_command.side_effect = None
    mock_git._run_git_command.return_value.stdout = "invalid git output format"
    history = git_manager.get_history()
    assert len(history) == 0


def test_get_recently_broken_ratchets_multiple(tmp_path):
    """Test getting multiple recently broken ratchets."""
    # Create test files
    file1 = tmp_path / "test1.py"
    file2 = tmp_path / "test2.py"

    # Create test files with content
    file1.write_text("print('Hello')\nimport os")
    file2.write_text("print('World')")

    # Create ratchet tests
    test1 = RegexBasedRatchetTest(
        name="test1",
        pattern=r"print\(",
        match_examples=("print('Hello')",),
        non_match_examples=("logging.info('Hello')",),
    )
    test2 = RegexBasedRatchetTest(
        name="test2",
        pattern=r"^import\s+\w+$",
        match_examples=("import os",),
        non_match_examples=("from os import path",),
    )

    with patch(
        "coderatchet.core.recent_failures.get_ratchet_test_files"
    ) as mock_get_files, patch(
        "coderatchet.core.recent_failures.get_ratchet_tests"
    ) as mock_get_tests:
        mock_get_files.return_value = [file1, file2]
        mock_get_tests.return_value = {test1, test2}  # Return a set instead of a list

        # Test without commit info
        failures = get_recently_broken_ratchets(limit=10, include_commits=False)
        assert len(failures) == 3  # Two print statements and one import
        assert all(isinstance(f, TestFailure) for f in failures)
        assert all(f.test_name in ("test1", "test2") for f in failures)
        assert failures[0].filepath == str(file1)  # print('Hello') in file1
        assert failures[0].line_number == 1
        assert failures[1].filepath == str(file1)  # import os in file1
        assert failures[1].line_number == 2
        assert failures[2].filepath == str(file2)  # print('World') in file2
        assert failures[2].line_number == 1


def test_get_recently_broken_ratchets_empty():
    """Test getting recently broken ratchets with empty results."""
    # Mock empty test list
    with patch(
        "coderatchet.core.recent_failures.get_ratchet_test_files"
    ) as mock_get_files, patch(
        "coderatchet.core.recent_failures.get_ratchet_tests"
    ) as mock_get_tests:
        mock_get_files.return_value = []
        mock_get_tests.return_value = {
            RegexBasedRatchetTest(
                name="no_print",
                pattern=r"print\(",
                match_examples=("print('Hello')",),
                non_match_examples=("logging.info('Hello')",),
            )
        }
        failures = get_recently_broken_ratchets(limit=10, include_commits=True)
        assert len(failures) == 0


def test_get_ratchet_tests_error_handling():
    """Test error handling in ratchet test creation."""
    with patch("coderatchet.core.recent_failures.get_ratchet_tests") as mock_get_tests:
        # Test with config loading error
        mock_get_tests.side_effect = Exception("Failed to load configs")
        with pytest.raises(Exception) as excinfo:
            get_recently_broken_ratchets(limit=10, include_commits=True)
        assert str(excinfo.value) == "Failed to load configs"
