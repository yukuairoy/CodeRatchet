"""Unit tests for git integration functionality."""

import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from coderatchet.core.git_integration import (
    GitError,
    GitIntegration,
    add_and_commit,
    is_git_repo,
)


@pytest.fixture
def git_repo():
    """Create a temporary git repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Initialize git repository
        subprocess.run(["git", "init"], cwd=tmpdir, check=True)

        # Configure git user
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmpdir,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmpdir,
            check=True,
        )

        yield Path(tmpdir)


def test_git_integration_init(git_repo):
    """Test GitIntegration initialization."""
    # Test with valid repo
    git = GitIntegration(git_repo)
    assert git.repo_path == git_repo

    # Test with non-existent directory
    with pytest.raises(GitError, match="Directory does not exist"):
        GitIntegration("/nonexistent/path")

    # Test with non-git directory
    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(GitError, match="Not a git repository"):
            GitIntegration(tmpdir)


def test_git_command_validation(git_repo):
    """Test git command validation."""
    git = GitIntegration(git_repo)

    # Test invalid command argument type
    with pytest.raises(GitError, match="Invalid command argument type"):
        git._run_git_command([123])  # type: ignore

    # Test command injection prevention
    with pytest.raises(GitError, match="Invalid characters in command argument"):
        git._run_git_command(["log; rm -rf /"])

    # Test git format specifiers are allowed
    result = git._run_git_command(["log", "--format=%H"])
    assert result.returncode == 0


def test_git_repo_status(git_repo):
    """Test git repository status methods."""
    git = GitIntegration(git_repo)

    # Test is_git_repo
    assert git.is_git_repo()

    # Test is_detached_head
    assert not git.is_detached_head()

    # Create a commit and check out a detached HEAD
    add_and_commit(git_repo, "Initial commit")
    subprocess.run(["git", "checkout", "HEAD~0"], cwd=git_repo, check=True)
    assert git.is_detached_head()


def test_branch_operations(git_repo):
    """Test branch-related operations."""
    git = GitIntegration(git_repo)

    # Create initial commit
    add_and_commit(git_repo, "Initial commit")

    # Test get_current_branch
    assert git.get_current_branch() == "main"

    # Test get_branches
    subprocess.run(["git", "branch", "test-branch"], cwd=git_repo, check=True)
    branches = git.get_branches()
    assert "main" in branches
    assert "test-branch" in branches


def test_file_operations(git_repo):
    """Test file-related operations."""
    git = GitIntegration(git_repo)

    # Create test file
    test_file = git_repo / "test.txt"
    test_file.write_text("test content")

    # Add and commit
    add_and_commit(git_repo, "Add test file")

    # Test get_changed_files
    changed_files = git.get_changed_files()
    assert len(changed_files) == 0  # No changes after commit

    # Modify file
    test_file.write_text("modified content")
    changed_files = git.get_changed_files()
    assert len(changed_files) == 1
    assert changed_files[0].name == "test.txt"


def test_commit_operations(git_repo):
    """Test commit-related operations."""
    git = GitIntegration(git_repo)

    # Create test file and commit
    test_file = git_repo / "test.txt"
    test_file.write_text("test content")
    add_and_commit(git_repo, "Initial commit")

    # Test get_commit_info
    commit_hash = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=git_repo,
        text=True,
    ).strip()

    commit_info = git.get_commit_info(commit_hash)
    assert commit_info is not None
    commit_date, commit_message = commit_info
    assert isinstance(commit_date, datetime)
    assert commit_message == "Initial commit"

    # Test get_commit_files
    files = git.get_commit_files(commit_hash)
    assert len(files) == 1
    assert files[0].name == "test.txt"


def test_file_history(git_repo):
    """Test file history operations."""
    git = GitIntegration(git_repo)

    # Create and modify test file
    test_file = git_repo / "test.txt"
    test_file.write_text("initial content")
    add_and_commit(git_repo, "Initial commit")

    test_file.write_text("modified content")
    add_and_commit(git_repo, "Modify file")

    # Test get_file_history
    history = git.get_file_history(test_file)
    assert len(history) == 2
    assert history[0][2] == "Modify file"
    assert history[1][2] == "Initial commit"

    # Test get_file_content_at_commit
    initial_content = git.get_file_content_at_commit(test_file, history[1][0])
    assert initial_content == "initial content"


def test_merge_conflicts(git_repo):
    """Test merge conflict detection."""
    git = GitIntegration(git_repo)

    # Create initial commit
    test_file = git_repo / "test.txt"
    test_file.write_text("initial content")
    add_and_commit(git_repo, "Initial commit")

    # Create branch and modify file
    subprocess.run(["git", "checkout", "-b", "feature"], cwd=git_repo, check=True)
    test_file.write_text("feature content")
    add_and_commit(git_repo, "Feature change")

    # Modify file in main branch
    subprocess.run(["git", "checkout", "main"], cwd=git_repo, check=True)
    test_file.write_text("main content")
    add_and_commit(git_repo, "Main change")

    # Attempt merge to create conflict
    subprocess.run(["git", "merge", "feature"], cwd=git_repo, check=False)

    # Test conflict detection
    assert git.has_merge_conflicts()
    conflicts = git.get_merge_conflicts()
    assert len(conflicts) == 1
    assert conflicts[0].name == "test.txt"


def test_submodule_operations(git_repo):
    """Test submodule operations."""
    git = GitIntegration(git_repo)

    # Create a submodule
    with tempfile.TemporaryDirectory() as submodule_dir:
        subprocess.run(["git", "init"], cwd=submodule_dir, check=True)
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=submodule_dir,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=submodule_dir,
            check=True,
        )

        # Add a file to submodule
        test_file = Path(submodule_dir) / "test.txt"
        test_file.write_text("submodule content")
        subprocess.run(["git", "add", "test.txt"], cwd=submodule_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial submodule commit"],
            cwd=submodule_dir,
            check=True,
        )

        # Add submodule to main repo
        subprocess.run(
            ["git", "submodule", "add", submodule_dir, "submodule"],
            cwd=git_repo,
            check=True,
        )
        add_and_commit(git_repo, "Add submodule")

        # Test submodule status
        status = git.get_submodule_status("submodule")
        assert status[1] == "up to date"

        # Test submodule sync
        git.sync_submodules()

        # Test foreach_submodule
        results = git.foreach_submodule("git status")
        assert "submodule" in results


def test_config_operations(git_repo):
    """Test git config operations."""
    git = GitIntegration(git_repo)

    # Test set and get config value
    git.set_config_value("test.key", "test value")
    value = git.get_config_value("test.key")
    assert value == "test value"

    # Test get_config_value with non-existent key
    value = git.get_config_value("nonexistent.key")
    assert value is None


def test_utility_functions():
    """Test utility functions."""
    # Test is_git_repo
    with tempfile.TemporaryDirectory() as tmpdir:
        assert not is_git_repo(Path(tmpdir))

        subprocess.run(["git", "init"], cwd=tmpdir, check=True)
        assert is_git_repo(Path(tmpdir))

    # Test add_and_commit
    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(["git", "init"], cwd=tmpdir, check=True)
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmpdir,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmpdir,
            check=True,
        )

        test_file = Path(tmpdir) / "test.txt"
        test_file.write_text("test content")

        add_and_commit(Path(tmpdir), "Test commit")

        # Verify commit was created
        result = subprocess.run(
            ["git", "log", "--format=%s"],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "Test commit" in result.stdout
