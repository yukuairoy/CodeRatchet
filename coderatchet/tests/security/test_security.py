"""
Security-related tests for the ratchet system.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from coderatchet.core.config import get_ratchet_tests
from coderatchet.core.git_integration import GitIntegration
from coderatchet.core.ratchet import RegexBasedRatchetTest
from coderatchet.core.recent_failures import (
    GitHistoryManager,
    get_recently_broken_ratchets,
)


def test_path_traversal_prevention(tmp_path):
    """Test prevention of path traversal attacks."""
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
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        # Create a file with a malicious path
        test_file = src_dir / "test.py"
        test_file.write_text(
            """# Malicious path
path = "../../../etc/passwd"
"""
        )

        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "Add test file"], check=True)

        # Create a ratchet test for path traversal
        test = RegexBasedRatchetTest(
            name="no_path_traversal",
            pattern=r"\.\./",
            match_examples=["../../etc/passwd"],
            non_match_examples=["path/to/file"],
        )

        # Mock the ratchet tests function and os.path.exists
        with patch(
            "coderatchet.core.config.get_ratchet_tests", return_value=[test]
        ), patch("os.path.exists") as mock_exists:
            # Test that the system doesn't actually access the malicious path
            failures = get_recently_broken_ratchets(limit=10, include_commits=True)
            assert len(failures) == 1
            assert "../../../etc/passwd" in failures[0].line_contents
            # Check that os.path.exists was not called with the malicious path
            for call in mock_exists.call_args_list:
                assert "/etc/passwd" not in str(call[0][0])
    finally:
        # Restore original directory
        os.chdir(original_dir)


def test_command_injection_prevention():
    """Test prevention of command injection in git commands."""
    # Create mock GitIntegration
    mock_git = MagicMock(spec=GitIntegration)
    git_manager = GitHistoryManager(mock_git)

    # Test with malicious commit hash
    malicious_hash = "abc123; rm -rf /"
    mock_git._run_git_command.side_effect = subprocess.CalledProcessError(
        128, "git log", b"fatal: bad revision"
    )
    history = git_manager.get_history(since_commit=malicious_hash)
    # Should not execute the malicious command
    assert len(history) == 0  # Should reject invalid commit hash
    mock_git._run_git_command.assert_called_with(
        ["log", "--format=%H %ct %s", "--", malicious_hash]
    )

    # Test with malicious file path
    malicious_path = "test.py; rm -rf /"
    mock_git._run_git_command.side_effect = subprocess.CalledProcessError(
        128, "git log", b"fatal: no such path"
    )
    commits = git_manager.get_file_commits(malicious_path, [])
    # Should not execute the malicious command
    assert len(commits) == 0  # Should reject invalid file path
    mock_git._run_git_command.assert_called_with(
        ["log", "--format=%H %ct %s", "--", malicious_path]
    )


def test_sensitive_data_detection():
    """Test detection of sensitive data in code."""
    # Create ratchet tests
    tests = [
        RegexBasedRatchetTest(
            name="api_keys",
            pattern=r"sk_[a-zA-Z0-9_]+",  # Match Stripe-like API keys
            match_examples=(
                "sk_test_1234567890abcdef",
                "sk_live_abcdef1234567890",
            ),
            non_match_examples=(
                "pk_test_1234567890abcdef",  # Public key
                "not_an_api_key",
            ),
            exclude_test_files=False,  # Don't exclude test files
        ),
        RegexBasedRatchetTest(
            name="passwords",
            pattern=r"password[0-9]+",  # Match simple passwords
            match_examples=(
                "password123",
                "password456",
            ),
            non_match_examples=(
                "not_a_password",
                "pass_word",
            ),
            exclude_test_files=False,  # Don't exclude test files
        ),
        RegexBasedRatchetTest(
            name="db_urls",
            pattern=r"postgres://[^@]+@[^/]+/[^\"'\s]+",  # Match database URLs
            match_examples=(
                "postgres://user:pass@localhost/db",
                "postgres://admin:secret@prod.example.com/mydb",
            ),
            non_match_examples=(
                "mysql://user:pass@localhost/db",
                "not_a_db_url",
            ),
            exclude_test_files=False,  # Don't exclude test files
        ),
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        test_file = Path(tmpdir) / "test.py"
        test_file.write_text(
            """
            api_key = "sk_test_1234567890abcdef"
            password = "password123"
            db_url = "postgres://user:pass@localhost/db"
        """
        )

        # Initialize Git repository
        subprocess.run(["git", "init"], cwd=tmpdir, check=True)
        subprocess.run(["git", "add", "."], cwd=tmpdir, check=True)
        subprocess.run(
            ["git", "config", "user.name", "Test User"], cwd=tmpdir, check=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"], cwd=tmpdir, check=True
        )
        subprocess.run(["git", "commit", "-m", "Add test file"], cwd=tmpdir, check=True)

        # Mock the ratchet tests function and file collection
        with patch(
            "coderatchet.core.config.get_ratchet_tests", return_value=tests
        ), patch(
            "coderatchet.core.recent_failures.get_ratchet_test_files",
            return_value=[str(test_file)],
        ):
            # Test for sensitive data
            failures = get_recently_broken_ratchets(limit=10, include_commits=True)
            assert len(failures) == 3  # Should detect all sensitive data
            assert any(f.test_name == "api_keys" for f in failures)
            assert any(f.test_name == "passwords" for f in failures)
            assert any(f.test_name == "db_urls" for f in failures)
