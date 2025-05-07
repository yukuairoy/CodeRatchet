"""Integration tests for Git integration."""

import os
import subprocess
from datetime import datetime

import pytest

from coderatchet.core.git_integration import GitError, GitIntegration


def test_git_repo_initialization(tmp_path):
    """Test Git repository initialization."""
    # Test with non-git directory
    with pytest.raises(GitError):
        GitIntegration(tmp_path)

    # Initialize git repository
    subprocess.run(["git", "init"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True
    )

    # Test with git repository
    git = GitIntegration(tmp_path)
    assert git.repo_path == tmp_path

    # Test with current directory
    os.chdir(tmp_path)
    git = GitIntegration()
    assert git.repo_path == tmp_path


def test_git_branch_operations(tmp_path):
    """Test Git branch operations."""
    # Initialize repository
    subprocess.run(["git", "init"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True
    )

    # Create initial commit
    test_file = tmp_path / "test.py"
    test_file.write_text("print('Initial')")
    subprocess.run(["git", "add", "test.py"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=tmp_path, check=True)

    git = GitIntegration(tmp_path)

    # Test get_current_branch
    assert git.get_current_branch() == "main"

    # Test branch creation and switching
    subprocess.run(["git", "checkout", "-b", "feature"], cwd=tmp_path, check=True)
    assert git.get_current_branch() == "feature"

    # Test get_branches
    branches = git.get_branches()
    assert "main" in branches
    assert "feature" in branches


def test_git_file_operations(tmp_path):
    """Test Git file operations."""
    # Initialize repository
    subprocess.run(["git", "init"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True
    )

    # Create initial commit
    test_file = tmp_path / "test.py"
    test_file.write_text("print('Initial')")
    subprocess.run(["git", "add", "test.py"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=tmp_path, check=True)

    git = GitIntegration(tmp_path)

    # Test get_changed_files
    changed_files = git.get_changed_files()
    assert len(changed_files) == 0  # No changes after commit

    # Make a change
    test_file.write_text("print('Modified')")
    changed_files = git.get_changed_files()
    assert len(changed_files) == 1
    assert changed_files[0].name == "test.py"

    # Test get_file_history
    history = git.get_file_history("test.py")
    assert len(history) == 1
    commit_hash, commit_date, commit_message = history[0]
    assert isinstance(commit_date, datetime)
    assert commit_message == "Initial commit"

    # Test get_file_content_at_commit
    content = git.get_file_content_at_commit("test.py", commit_hash)
    assert content == "print('Initial')"

    # Test get_commit_info
    commit_info = git.get_commit_info(commit_hash)
    assert commit_info is not None
    commit_date, commit_message = commit_info
    assert isinstance(commit_date, datetime)
    assert commit_message == "Initial commit"


def test_git_merge_conflict_handling(tmp_path):
    """Test handling of Git merge conflicts."""
    # Initialize repository
    subprocess.run(["git", "init"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True
    )

    # Create initial commit
    test_file = tmp_path / "test.py"
    test_file.write_text("print('Initial')")
    subprocess.run(["git", "add", "test.py"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=tmp_path, check=True)

    # Create feature branch
    subprocess.run(["git", "checkout", "-b", "feature"], cwd=tmp_path, check=True)
    test_file.write_text("print('Feature')")
    subprocess.run(["git", "add", "test.py"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "Feature change"], cwd=tmp_path, check=True)

    # Switch back to main and make conflicting change
    subprocess.run(["git", "checkout", "main"], cwd=tmp_path, check=True)
    test_file.write_text("print('Main')")
    subprocess.run(["git", "add", "test.py"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "Main change"], cwd=tmp_path, check=True)

    # Attempt merge (should create conflict)
    try:
        subprocess.run(["git", "merge", "feature"], cwd=tmp_path, check=True)
    except subprocess.CalledProcessError:
        pass  # Expected to fail

    git = GitIntegration(tmp_path)

    # Test merge conflict detection
    assert git.has_merge_conflicts()
    conflicts = git.get_merge_conflicts()
    assert len(conflicts) == 1
    assert conflicts[0].name == "test.py"

    # Test that operations fail during conflict
    with pytest.raises(GitError):
        git.get_changed_files()

    with pytest.raises(GitError):
        git.get_commit_info("HEAD")

    # Abort merge
    subprocess.run(["git", "merge", "--abort"], cwd=tmp_path, check=True)


def test_git_detached_head_handling(tmp_path):
    """Test handling of detached HEAD state."""
    # Initialize repository
    subprocess.run(["git", "init"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True
    )

    # Create initial commit
    test_file = tmp_path / "test.py"
    test_file.write_text("print('Initial')")
    subprocess.run(["git", "add", "test.py"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=tmp_path, check=True)

    # Get commit hash
    commit_hash = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True
    ).strip()

    # Checkout commit directly (detached HEAD)
    subprocess.run(["git", "checkout", commit_hash], cwd=tmp_path, check=True)

    git = GitIntegration(tmp_path)

    # Test detached HEAD detection
    assert git.is_detached_head()

    # Test that operations fail in detached HEAD state
    with pytest.raises(GitError):
        git.get_current_branch()

    with pytest.raises(GitError):
        git.get_changed_files()


def test_git_config_operations(tmp_path):
    """Test Git configuration operations."""
    # Initialize repository
    subprocess.run(["git", "init"], cwd=tmp_path, check=True)

    git = GitIntegration(tmp_path)

    # Test setting and getting config values
    git.set_config_value("user.name", "Test User")
    assert git.get_config_value("user.name") == "Test User"

    git.set_config_value("user.email", "test@example.com")
    assert git.get_config_value("user.email") == "test@example.com"

    # Test getting non-existent config
    assert git.get_config_value("nonexistent.key") is None


def test_git_repo_path_operations(tmp_path):
    """Test Git repository path operations."""
    # Initialize repository
    subprocess.run(["git", "init"], cwd=tmp_path, check=True)

    git = GitIntegration(tmp_path)

    # Test getting repository root
    assert git.get_repo_root() == tmp_path

    # Test getting hooks path
    hooks_path = git.get_hook_path()
    assert hooks_path.is_dir()
    assert hooks_path.parent.name == ".git"


def test_git_blame_operations(tmp_path):
    """Test Git blame operations."""
    # Initialize repository
    subprocess.run(["git", "init"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True
    )

    # Create initial commit
    test_file = tmp_path / "test.py"
    test_file.write_text("print('Line 1')\nprint('Line 2')")
    subprocess.run(["git", "add", "test.py"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=tmp_path, check=True)

    git = GitIntegration(tmp_path)

    # Test blame information
    blame_info = git.get_file_blame("test.py")
    assert len(blame_info) == 2  # Two lines

    # Check blame information format
    for commit_hash, author, line_number, content in blame_info:
        assert isinstance(commit_hash, str)
        assert isinstance(author, str)
        assert isinstance(line_number, int)
        assert isinstance(content, str)
        assert "print" in content


def test_git_stash_operations(tmp_path):
    """Test Git stash operations."""
    # Initialize repository
    subprocess.run(["git", "init"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True
    )

    # Create initial commit
    test_file = tmp_path / "test.py"
    test_file.write_text("print('Initial')")
    subprocess.run(["git", "add", "test.py"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=tmp_path, check=True)

    # Make changes and stash them
    test_file.write_text("print('Modified')")
    subprocess.run(["git", "stash", "save", "Test stash"], cwd=tmp_path, check=True)

    git = GitIntegration(tmp_path)

    # Test getting stash list
    stash_list = git.get_stash_list()
    assert len(stash_list) == 1
    stash_hash, stash_message = stash_list[0]
    assert isinstance(stash_hash, str)
    assert stash_message == "Test stash"


def test_git_tag_operations(tmp_path):
    """Test Git tag operations."""
    # Initialize repository
    subprocess.run(["git", "init"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True
    )

    # Create initial commit
    test_file = tmp_path / "test.py"
    test_file.write_text("print('Initial')")
    subprocess.run(["git", "add", "test.py"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=tmp_path, check=True)

    # Create tags
    subprocess.run(["git", "tag", "v1.0"], cwd=tmp_path, check=True)
    subprocess.run(["git", "tag", "v1.1"], cwd=tmp_path, check=True)

    git = GitIntegration(tmp_path)

    # Test getting tag list
    tags = git.get_tag_list()
    assert len(tags) == 2
    assert "v1.0" in tags
    assert "v1.1" in tags


def test_git_history_operations(tmp_path):
    """Test Git history operations."""
    # Initialize repository
    subprocess.run(["git", "init"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True
    )

    # Create initial commit
    test_file = tmp_path / "test.py"
    test_file.write_text("print('Initial')")
    subprocess.run(["git", "add", "test.py"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=tmp_path, check=True)

    # Create second commit
    test_file.write_text("print('Modified')")
    subprocess.run(["git", "add", "test.py"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "Second commit"], cwd=tmp_path, check=True)

    git = GitIntegration(tmp_path)

    # Test get_git_history without limit
    history = git.get_git_history()
    assert len(history) == 2

    # Check most recent commit
    commit_hash, commit_date, commit_message = history[0]
    assert isinstance(commit_hash, str)
    assert isinstance(commit_date, datetime)
    assert commit_message == "Second commit"

    # Check older commit
    commit_hash, commit_date, commit_message = history[1]
    assert isinstance(commit_hash, str)
    assert isinstance(commit_date, datetime)
    assert commit_message == "Initial commit"

    # Test get_git_history with limit
    history = git.get_git_history(limit=1)
    assert len(history) == 1
    commit_hash, commit_date, commit_message = history[0]
    assert commit_message == "Second commit"

    # Test in detached HEAD state
    commit_hash = subprocess.check_output(
        ["git", "rev-parse", "HEAD^"], cwd=tmp_path, text=True
    ).strip()
    subprocess.run(["git", "checkout", commit_hash], cwd=tmp_path, check=True)

    with pytest.raises(GitError):
        git.get_git_history()
