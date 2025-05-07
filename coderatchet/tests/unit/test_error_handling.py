"""
Tests for error handling.
"""

import os
import subprocess

import pytest

from coderatchet.core.config import ConfigError
from coderatchet.core.git_integration import GitError, GitIntegration
from coderatchet.core.ratchet import RegexBasedRatchetTest
from coderatchet.core.utils import RatchetError


def test_invalid_regex_pattern():
    """Test handling of invalid regex patterns."""
    with pytest.raises(RatchetError):
        RegexBasedRatchetTest(
            name="invalid",
            pattern="[",  # Invalid regex pattern
            match_examples=["["],
            non_match_examples=["x"],
        )


def test_file_permission_error(tmp_path):
    """Test handling of file permission errors."""
    # Create a file and make it unreadable
    test_file = tmp_path / "test.py"
    test_file.write_text("print('Hello')")
    test_file.chmod(0o000)  # No permissions

    test = RegexBasedRatchetTest(
        name="test",
        pattern="print\\(",
        match_examples=["print('Hello')"],
        non_match_examples=["logging.info('Hello')"],
    )

    with pytest.raises(RatchetError):
        test.collect_failures_from_file(test_file)


def test_malformed_config_file(tmp_path):
    """Test handling of malformed configuration files."""
    config_file = tmp_path / "coderatchet.yaml"
    config_file.write_text(
        """
    ratchets:
        invalid: yaml
        - this is not valid
        - yaml syntax
    """
    )

    with pytest.raises(ConfigError):
        from coderatchet.core.config import load_config

        load_config(config_file, fallback_to_default=False)


def test_git_network_error(tmp_path):
    """Test handling of Git network errors."""
    # Initialize git repository
    subprocess.run(["git", "init"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True
    )

    # Create a test file and commit it
    test_file = tmp_path / "test.py"
    test_file.write_text("print('test')")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=tmp_path, check=True)

    # Add a non-existent remote to simulate network error
    subprocess.run(
        ["git", "remote", "add", "origin", "https://non.existent.url/repo.git"],
        cwd=tmp_path,
        check=True,
    )

    git = GitIntegration(tmp_path)
    with pytest.raises(GitError, match="Git command failed"):
        # Try to get file content from a non-existent remote commit
        git.get_file_content_at_commit("test.py", "origin/main")


def test_empty_file_handling(tmp_path):
    """Test handling of empty files."""
    empty_file = tmp_path / "empty.py"
    empty_file.write_text("")

    test = RegexBasedRatchetTest(
        name="test",
        pattern="print\\(",
        match_examples=["print('Hello')"],
        non_match_examples=["logging.info('Hello')"],
    )

    # Should not raise any errors
    test.collect_failures_from_file(empty_file)
    assert len(test.failures) == 0


def test_non_ascii_content(tmp_path):
    """Test handling of non-ASCII content."""
    test_file = tmp_path / "test.py"
    test_file.write_text(
        """
    # This is a comment with non-ASCII characters: é, ñ, 你好
    def hello():
        print("Hello")  # Should still match
    """
    )

    test = RegexBasedRatchetTest(
        name="test",
        pattern="print\\(",
        match_examples=["print('Hello')"],
        non_match_examples=["logging.info('Hello')"],
    )

    test.collect_failures_from_file(test_file)
    assert len(test.failures) == 1


def test_different_line_endings(tmp_path):
    """Test handling of different line endings."""
    test_file = tmp_path / "test.py"
    test_file.write_text("print('Hello')\r\nprint('World')\r\n")  # CRLF

    test = RegexBasedRatchetTest(
        name="test",
        pattern="print\\(",
        match_examples=["print('Hello')"],
        non_match_examples=["logging.info('Hello')"],
    )

    test.collect_failures_from_file(test_file)
    assert len(test.failures) == 2


def test_large_file_handling(tmp_path):
    """Test handling of large files."""
    test_file = tmp_path / "large.py"
    # Create a large file with many lines
    with open(test_file, "w") as f:
        for i in range(10000):
            f.write(f"print('Line {i}')\n")

    test = RegexBasedRatchetTest(
        name="test",
        pattern="print\\(",
        match_examples=["print('Hello')"],
        non_match_examples=["logging.info('Hello')"],
    )

    # Should not raise memory errors
    test.collect_failures_from_file(test_file)
    assert len(test.failures) == 10000


def test_git_detached_head(tmp_path):
    """Test handling of Git detached HEAD state."""
    # Initialize git repository
    subprocess.run(["git", "init"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True
    )

    # Create a test file and make multiple commits
    test_file = tmp_path / "test.py"
    test_file.write_text("print('version 1')")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "First commit"], cwd=tmp_path, check=True)
    first_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    test_file.write_text("print('version 2')")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "Second commit"], cwd=tmp_path, check=True)

    # Checkout the first commit to create detached HEAD
    subprocess.run(["git", "checkout", first_commit], cwd=tmp_path, check=True)

    git = GitIntegration(tmp_path)
    with pytest.raises(GitError, match="Git repository is in detached HEAD state"):
        git.get_current_branch()


def test_git_merge_conflict(tmp_path):
    """Test handling of Git merge conflicts."""
    # Initialize git repository
    subprocess.run(["git", "init"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True
    )

    # Create initial file and commit
    test_file = tmp_path / "test.py"
    test_file.write_text("print('main branch')")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=tmp_path, check=True)

    # Create and switch to feature branch
    subprocess.run(["git", "checkout", "-b", "feature"], cwd=tmp_path, check=True)
    test_file.write_text("print('feature branch')")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "Feature commit"], cwd=tmp_path, check=True)

    # Switch back to main and make conflicting change
    subprocess.run(["git", "checkout", "main"], cwd=tmp_path, check=True)
    test_file.write_text("print('conflicting change')")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "Main commit"], cwd=tmp_path, check=True)

    # Try to merge feature branch which should cause conflicts
    subprocess.run(["git", "merge", "feature"], cwd=tmp_path, check=False)

    git = GitIntegration(tmp_path)
    with pytest.raises(GitError, match="Repository has merge conflicts"):
        git.get_changed_files()


def test_config_env_var_substitution(tmp_path):
    """Test handling of environment variable substitution in configs."""
    config_file = tmp_path / "coderatchet.yaml"
    config_file.write_text(
        """
    ratchets:
        test:
            pattern: ${PATTERN}
            match_examples: ["${EXAMPLE}"]
    """
    )

    # Set environment variables
    os.environ["PATTERN"] = "print\\("
    os.environ["EXAMPLE"] = "print('Hello')"

    try:
        from coderatchet.core.config import load_config

        config = load_config(config_file)
        assert config["ratchets"]["test"]["pattern"] == "print\\("
        assert config["ratchets"]["test"]["match_examples"][0] == "print('Hello')"
    finally:
        # Clean up environment variables
        del os.environ["PATTERN"]
        del os.environ["EXAMPLE"]


def test_config_inheritance_cycle(tmp_path):
    """Test handling of circular config inheritance."""
    config1 = tmp_path / "config1.yaml"
    config2 = tmp_path / "config2.yaml"

    config1.write_text(
        """
    extends: config2.yaml
    ratchets:
        test1:
            pattern: print
    """
    )

    config2.write_text(
        """
    extends: config1.yaml
    ratchets:
        test2:
            pattern: import
    """
    )

    with pytest.raises(ConfigError):
        from coderatchet.core.config import load_config

        load_config(config1, fallback_to_default=False)


def test_invalid_config_values(tmp_path):
    """Test handling of invalid configuration values."""
    config_file = tmp_path / "coderatchet.yaml"
    config_file.write_text(
        """
    ratchets:
        test:
            pattern: print
            allowed_count: "not a number"
            match_examples: 42
    """
    )

    with pytest.raises(ConfigError):
        from coderatchet.core.config import load_config

        load_config(config_file, fallback_to_default=False)
