"""Unit tests for git integration functionality."""

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

    # Create a test file and commit it
    test_file = git_repo / "test.txt"
    test_file.write_text("test content")
    git._run_git_command(["add", "test.txt"])
    git._run_git_command(["config", "user.name", "Test User"])
    git._run_git_command(["config", "user.email", "test@example.com"])
    git._run_git_command(["commit", "-m", "Initial commit"])

    # Test invalid command argument type
    with pytest.raises(GitError, match="Invalid command argument type"):
        git._run_git_command([123])  # type: ignore

    # Test command injection prevention
    with pytest.raises(GitError, match="Invalid characters in command argument"):
        git._run_git_command(["log; rm -rf /"])

    # Test git format specifiers are allowed
    result = git._run_git_command(["log", "--format=%H"])
    assert result.returncode == 0
    assert len(result.stdout.strip()) == 40  # Git hash is 40 characters

    # Test other git-specific characters are blocked
    with pytest.raises(GitError, match="Invalid characters in command argument"):
        git._run_git_command(["log", "--author={user}"])

    # Test multiple arguments
    result = git._run_git_command(["log", "--oneline", "--format=%h"])
    assert result.returncode == 0
    assert len(result.stdout.strip()) == 7  # Short hash is 7 characters


def test_git_repo_status(git_repo):
    """Test git repository status methods."""
    git = GitIntegration(git_repo)

    # Test is_git_repo
    assert git.is_git_repo()

    # Test is_detached_head
    assert not git.is_detached_head()

    # Create a test file and commit it
    test_file = git_repo / "test.txt"
    test_file.write_text("test content")
    add_and_commit(git_repo, "Initial commit")

    # Check out a detached HEAD
    subprocess.run(["git", "checkout", "HEAD~0"], cwd=git_repo, check=True)
    assert git.is_detached_head()


def test_branch_operations(git_repo):
    """Test branch-related operations."""
    git = GitIntegration(git_repo)

    # Create test file and initial commit
    test_file = git_repo / "test.txt"
    test_file.write_text("test content")
    add_and_commit(git_repo, "Initial commit")

    # Test get_current_branch
    assert git.get_current_branch() == "main"

    # Test get_branches with no branches
    branches = git.get_branches()
    assert len(branches) == 1
    assert "main" in branches

    # Create and test multiple branches
    subprocess.run(["git", "branch", "feature1"], cwd=git_repo, check=True)
    subprocess.run(["git", "branch", "feature2"], cwd=git_repo, check=True)
    branches = git.get_branches()
    assert len(branches) == 3
    assert all(b in branches for b in ["main", "feature1", "feature2"])

    # Test switching branches
    subprocess.run(["git", "checkout", "feature1"], cwd=git_repo, check=True)
    assert git.get_current_branch() == "feature1"

    # Test detached HEAD state error
    subprocess.run(["git", "checkout", "HEAD~0"], cwd=git_repo, check=True)
    with pytest.raises(GitError, match="Git repository is in detached HEAD state"):
        git.get_current_branch()


def test_file_operations(git_repo):
    """Test file-related operations."""
    git = GitIntegration(git_repo)

    # Create initial commit
    initial_file = git_repo / "initial.txt"
    initial_file.write_text("initial content")
    add_and_commit(git_repo, "Initial commit")

    # Test with no changes
    assert len(git.get_changed_files()) == 0

    # Create test file
    test_file = git_repo / "test.txt"
    test_file.write_text("test content")

    # Test untracked file
    changed_files = git.get_changed_files()
    assert len(changed_files) == 1
    assert changed_files[0].name == "test.txt"

    # Add and commit
    add_and_commit(git_repo, "Add test file")

    # Test no changes after commit
    changed_files = git.get_changed_files()
    assert len(changed_files) == 0

    # Modify file
    test_file.write_text("modified content")
    changed_files = git.get_changed_files()
    assert len(changed_files) == 1
    assert changed_files[0].name == "test.txt"

    # Test with base branch comparison
    subprocess.run(["git", "checkout", "-b", "feature"], cwd=git_repo, check=True)
    new_file = git_repo / "new.txt"
    new_file.write_text("new content")
    add_and_commit(git_repo, "Add new file")

    # Modify test.txt in feature branch
    test_file.write_text("feature branch content")
    add_and_commit(git_repo, "Modify test.txt in feature")

    # Compare with main branch
    changed_files = git.get_changed_files("main")
    assert len(changed_files) == 2
    assert any(f.name == "new.txt" for f in changed_files)
    assert any(f.name == "test.txt" for f in changed_files)

    # Test with untracked file in feature branch
    untracked_file = git_repo / "untracked.txt"
    untracked_file.write_text("untracked content")
    changed_files = git.get_changed_files("main")
    assert len(changed_files) == 3
    assert any(f.name == "untracked.txt" for f in changed_files)

    # Test with merge conflicts
    subprocess.run(["git", "checkout", "main"], cwd=git_repo, check=True)
    test_file.write_text("conflicting content")
    add_and_commit(git_repo, "Conflicting change")

    with pytest.raises(GitError, match="Repository has merge conflicts"):
        subprocess.run(["git", "merge", "feature"], cwd=git_repo, check=False)
        git.get_changed_files()


def test_commit_operations(git_repo):
    """Test commit-related operations."""
    git = GitIntegration(git_repo)

    # Test with no commits
    with pytest.raises(GitError, match="Invalid git revision"):
        git.get_commit_info("HEAD")

    # Create test file and commit
    test_file = git_repo / "test.txt"
    test_file.write_text("test content")
    add_and_commit(git_repo, "Initial commit")

    # Get commit hash
    commit_hash = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=git_repo,
        text=True,
    ).strip()

    # Test get_commit_info
    commit_info = git.get_commit_info(commit_hash)
    assert commit_info is not None
    commit_date, commit_message = commit_info
    assert isinstance(commit_date, datetime)
    assert commit_message == "Initial commit"

    # Test get_commit_files
    files = git.get_commit_files(commit_hash)
    assert len(files) == 1
    assert files[0].name == "test.txt"

    # Test with invalid commit hash
    with pytest.raises(GitError, match="Invalid git revision"):
        git.get_commit_info("invalid_hash")

    # Test with merge conflicts
    subprocess.run(["git", "checkout", "-b", "feature"], cwd=git_repo, check=True)
    test_file.write_text("feature content")
    add_and_commit(git_repo, "Feature change")

    subprocess.run(["git", "checkout", "main"], cwd=git_repo, check=True)
    test_file.write_text("main content")
    add_and_commit(git_repo, "Main change")

    subprocess.run(["git", "merge", "feature"], cwd=git_repo, check=False)
    with pytest.raises(
        GitError, match="Cannot get commit info while repository has merge conflicts"
    ):
        git.get_commit_info("HEAD")

    # Test get_merge_base
    merge_base = git.get_merge_base("main", "feature")
    assert merge_base == commit_hash


def test_file_history(git_repo):
    """Test file history operations."""
    git = GitIntegration(git_repo)

    # Test with non-existent file
    with pytest.raises(GitError):
        git.get_file_history(git_repo / "nonexistent.txt")

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
    modified_content = git.get_file_content_at_commit(test_file, history[0][0])
    assert modified_content == "modified content"

    # Test with renamed file
    new_path = git_repo / "renamed.txt"
    subprocess.run(["git", "mv", "test.txt", "renamed.txt"], cwd=git_repo, check=True)
    add_and_commit(git_repo, "Rename file")

    # History should follow renames
    history = git.get_file_history(new_path)
    assert len(history) == 3
    assert history[0][2] == "Rename file"
    assert history[1][2] == "Modify file"
    assert history[2][2] == "Initial commit"

    # Test with absolute path
    abs_path = new_path.resolve()
    history = git.get_file_history(abs_path)
    assert len(history) == 3

    # Test with invalid commit hash
    with pytest.raises(
        GitError, match="Git command failed: fatal: invalid object name"
    ):
        git.get_file_content_at_commit(new_path, "invalid_hash")

    # Test with file outside repository
    outside_file = Path("/tmp/outside.txt")
    with pytest.raises(
        GitError, match="Git command failed: fatal: .* is outside repository"
    ):
        git.get_file_history(outside_file)


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

    # Create initial commit in main repo
    test_file = git_repo / "test.txt"
    test_file.write_text("main repo content")
    add_and_commit(git_repo, "Initial commit")

    # Create a bare repository for submodule
    with tempfile.TemporaryDirectory() as tmpdir:
        bare_repo = Path(tmpdir) / "bare.git"
        subprocess.run(["git", "init", "--bare", str(bare_repo)], check=True)

        # Clone the bare repo to create submodule content
        submodule_content = Path(tmpdir) / "submodule_content"
        subprocess.run(
            ["git", "clone", str(bare_repo), str(submodule_content)], check=True
        )

        # Configure git user in submodule
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=submodule_content,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=submodule_content,
            check=True,
        )

        # Add content to submodule
        test_file = submodule_content / "test.txt"
        test_file.write_text("submodule content")
        add_and_commit(submodule_content, "Initial commit in submodule")

        # Push to bare repo
        subprocess.run(
            ["git", "push", "origin", "main"], cwd=submodule_content, check=True
        )

        # Add submodule to main repo
        git.add_submodule(str(bare_repo), "submodule")

        # Initialize and update submodules
        git.init_submodules()
        git.update_submodules()

        # Configure submodule branch
        git.set_submodule_branch("submodule", "main")

        # Force update the submodule to ensure it's in sync
        subprocess.run(
            ["git", "submodule", "update", "--init", "--recursive", "--force"],
            cwd=git_repo,
            check=True,
        )

        # Commit the submodule changes
        subprocess.run(
            ["git", "add", "submodule"],
            cwd=git_repo,
            check=True,
        )
        add_and_commit(git_repo, "Update submodule")

        # Debug: Print submodule status
        result = subprocess.run(
            ["git", "submodule", "status"],
            cwd=git_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        print(f"Submodule status output: {result.stdout}")

        # Test submodule status
        status = git.get_submodule_status("submodule")
        print(f"Status tuple: {status}")
        # The status should be "unknown" since there's no leading space
        assert status[1] == "unknown"

        # Test submodule sync
        git.sync_submodules()

        # Test foreach_submodule
        results = git.foreach_submodule("git status")
        assert "submodule" in results

        # Test submodule configuration
        git.set_submodule_ignore("submodule", "all")
        git.set_submodule_update("submodule", "rebase")
        git.set_submodule_shallow("submodule", True)
        git.set_submodule_recursive("submodule", True)
        git.set_submodule_fetchRecurseSubmodules("submodule", True)

        # Test getting submodule configuration
        assert git.get_submodule_branch("submodule") == "main"
        assert git.get_submodule_ignore("submodule") == "all"
        assert git.get_submodule_update("submodule") == "rebase"
        assert git.get_submodule_shallow("submodule") is True
        assert git.get_submodule_recursive("submodule") is True
        assert git.get_submodule_fetchRecurseSubmodules("submodule") is True

        # Test detached HEAD state
        subprocess.run(["git", "checkout", "HEAD~0"], cwd=git_repo, check=True)
        with pytest.raises(GitError, match="Git repository is in detached HEAD state"):
            git.get_submodule_status("submodule")


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

    # Test multiple config values
    git.set_config_value("test.name", "John Doe")
    git.set_config_value("test.email", "john@example.com")
    assert git.get_config_value("test.name") == "John Doe"
    assert git.get_config_value("test.email") == "john@example.com"

    # Test overwriting config value
    git.set_config_value("test.key", "new value")
    assert git.get_config_value("test.key") == "new value"

    # Test boolean config values
    git.set_config_value("test.bool", "true")
    assert git.get_config_value("test.bool") == "true"

    # Test with special characters
    git.set_config_value("test.special", "value with spaces")
    assert git.get_config_value("test.special") == "value with spaces"

    # Test hook path
    hook_path = git.get_hook_path()
    assert hook_path.is_dir()
    assert (hook_path / "pre-commit.sample").exists()

    # Test repo root
    repo_root = git.get_repo_root()
    assert str(repo_root).replace("/private", "") == str(git_repo)


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
