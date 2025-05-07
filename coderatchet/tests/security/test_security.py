"""
Security-related tests for the ratchet system.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from coderatchet.core.config import RatchetConfig
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
            match_examples=("../../etc/passwd",),
            non_match_examples=("path/to/file",),
        )

        # Mock the necessary functions
        from unittest.mock import MagicMock, patch

        from coderatchet.core.config import RatchetConfig

        test_config = RatchetConfig(
            name="no_path_traversal",
            pattern=r"\.\./",
            match_examples=("../../etc/passwd",),
            non_match_examples=("path/to/file",),
        )

        def mock_get_python_files(*args, **kwargs):
            return {test_file}

        git_mock = MagicMock()
        git_mock._run_git_command.return_value.stdout = (
            "commit_hash 1683000000 Add test file"
        )

        with patch(
            "coderatchet.core.config.load_ratchet_configs",
            return_value=[test_config],
        ), patch(
            "coderatchet.core.config.create_ratchet_tests",
            return_value=[test],
        ), patch(
            "coderatchet.core.utils.get_python_files",
            side_effect=mock_get_python_files,
        ), patch(
            "coderatchet.core.utils._get_exclusion_patterns",
            return_value=[],
        ), patch(
            "coderatchet.core.recent_failures.GitIntegration",
            return_value=git_mock,
        ), patch(
            "coderatchet.core.recent_failures.get_ratchet_tests",
            return_value={test},
        ):
            # Test that the system detects the path traversal attempt
            failures = get_recently_broken_ratchets(limit=10, include_commits=True)
            assert len(failures) == 1
            assert failures[0].test_name == "no_path_traversal"
            assert "../../../etc/passwd" in failures[0].line_contents
            assert failures[0].commit_hash == "commit_hash"

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

        # Create configs for the tests
        configs = [
            RatchetConfig(
                name="api_keys",
                pattern=r"sk_[a-zA-Z0-9_]+",
                match_examples=(
                    "sk_test_1234567890abcdef",
                    "sk_live_abcdef1234567890",
                ),
                non_match_examples=(
                    "pk_test_1234567890abcdef",
                    "not_an_api_key",
                ),
            ),
            RatchetConfig(
                name="passwords",
                pattern=r"password[0-9]+",
                match_examples=(
                    "password123",
                    "password456",
                ),
                non_match_examples=(
                    "not_a_password",
                    "pass_word",
                ),
            ),
            RatchetConfig(
                name="db_urls",
                pattern=r"postgres://[^@]+@[^/]+/[^\"'\s]+",
                match_examples=(
                    "postgres://user:pass@localhost/db",
                    "postgres://admin:secret@prod.example.com/mydb",
                ),
                non_match_examples=(
                    "mysql://user:pass@localhost/db",
                    "not_a_db_url",
                ),
            ),
        ]

        # Mock git integration
        git_mock = MagicMock()
        git_mock._run_git_command.return_value.stdout = (
            "commit_hash 1683000000 Add test file"
        )

        # Mock the necessary functions
        with patch(
            "coderatchet.core.config.load_ratchet_configs",
            return_value=configs,
        ), patch(
            "coderatchet.core.config.create_ratchet_tests",
            return_value=tests,
        ), patch(
            "coderatchet.core.recent_failures.get_ratchet_tests",
            return_value=set(tests),
        ), patch(
            "coderatchet.core.recent_failures.get_ratchet_test_files",
            return_value=[str(test_file)],
        ), patch(
            "coderatchet.core.recent_failures.GitIntegration",
            return_value=git_mock,
        ):
            # Test for sensitive data
            failures = get_recently_broken_ratchets(limit=10, include_commits=True)
            assert len(failures) == 3  # Should detect all sensitive data
            assert any(f.test_name == "api_keys" for f in failures)
            assert any(f.test_name == "passwords" for f in failures)
            assert any(f.test_name == "db_urls" for f in failures)
