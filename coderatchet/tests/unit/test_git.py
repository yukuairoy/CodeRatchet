"""Unit tests for git integration."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from coderatchet.core.git_integration import GitError, GitIntegration


@patch("subprocess.run")
def test_git_integration_init(mock_run):
    """Test GitIntegration initialization."""
    # Test with default path (current directory)
    mock_run.return_value = MagicMock(returncode=0, stdout="true\n")
    with patch("pathlib.Path.exists", return_value=True):
        git = GitIntegration()
        assert git.repo_path == Path.cwd()

    # Test with custom path
    mock_run.return_value = MagicMock(returncode=0, stdout="true\n")
    with patch("pathlib.Path.exists", return_value=True):
        git = GitIntegration("/test/repo")
        assert git.repo_path == Path("/test/repo")

    # Test with non-existent directory
    with patch("pathlib.Path.exists", return_value=False):
        with pytest.raises(GitError, match="Directory does not exist"):
            GitIntegration("/test/repo")

    # Test with non-git directory
    mock_run.return_value = MagicMock(
        returncode=1, stderr="fatal: not a git repository"
    )
    with patch("pathlib.Path.exists", return_value=True):
        with pytest.raises(GitError, match="Not a git repository"):
            GitIntegration("/test/repo")


@patch("subprocess.run")
def test_is_git_repo(mock_run):
    """Test checking if directory is a git repository."""
    # Setup
    mock_run.return_value = MagicMock(returncode=0, stdout="true\n")
    with patch("pathlib.Path.exists", return_value=True):
        git = GitIntegration("/test/repo")

        # Test when it is a git repo
        mock_run.reset_mock()
        mock_run.return_value = MagicMock(returncode=0, stdout="true\n")
        assert git.is_git_repo() is True
        mock_run.assert_called_once_with(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=Path("/test/repo"),
            capture_output=True,
            text=True,
            check=False,
        )

        # Test when it is not a git repo
        mock_run.reset_mock()
        mock_run.return_value = MagicMock(
            returncode=1, stderr="fatal: not a git repository"
        )
        assert git.is_git_repo() is False
        mock_run.assert_called_once_with(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=Path("/test/repo"),
            capture_output=True,
            text=True,
            check=False,
        )


@patch("subprocess.run")
def test_is_detached_head(mock_run):
    """Test checking if repository is in detached HEAD state."""
    # Setup
    mock_run.return_value = MagicMock(returncode=0, stdout="true\n")
    with patch("pathlib.Path.exists", return_value=True):
        git = GitIntegration("/test/repo")

        # Test when not in detached HEAD
        mock_run.return_value = MagicMock(returncode=0, stdout="refs/heads/main\n")
        assert git.is_detached_head() is False

        # Test when in detached HEAD
        mock_run.return_value = MagicMock(
            returncode=1, stderr="fatal: ref HEAD is not a symbolic ref"
        )
        assert git.is_detached_head() is True


@patch("subprocess.run")
def test_get_changed_files(mock_run):
    """Test getting changed files."""
    # Setup
    mock_run.return_value = MagicMock(returncode=0, stdout="true\n")
    with patch("pathlib.Path.exists", return_value=True):
        git = GitIntegration("/test/repo")
        git.is_detached_head = MagicMock(return_value=False)
        git.has_merge_conflicts = MagicMock(return_value=False)

        # Test getting changed files
        mock_run.return_value = MagicMock(returncode=0, stdout="file1.py\nfile2.py\n")
        files = git.get_changed_files()
        assert len(files) == 2
        assert files[0] == Path("/test/repo/file1.py")
        assert files[1] == Path("/test/repo/file2.py")

        # Test with base branch
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc123\n"),  # merge-base
            MagicMock(returncode=0, stdout="file1.py\nfile2.py\n"),  # diff
        ]
        files = git.get_changed_files("main")
        assert len(files) == 2

        # Test with detached HEAD
        git.is_detached_head.return_value = True
        with pytest.raises(GitError, match="Repository is in detached HEAD state"):
            git.get_changed_files()

        # Test with merge conflicts
        git.is_detached_head.return_value = False
        git.has_merge_conflicts.return_value = True
        with pytest.raises(GitError, match="Repository has merge conflicts"):
            git.get_changed_files()


@patch("subprocess.run")
def test_get_file_history(mock_run):
    """Test getting file history."""
    # Setup
    mock_run.return_value = MagicMock(returncode=0, stdout="true\n")
    with patch("pathlib.Path.exists", return_value=True):
        git = GitIntegration("/test/repo")

        # Test getting file history
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="abc123|2024-01-01T12:00:00+00:00|Initial commit\n"
            "def456|2024-01-02T12:00:00+00:00|Update file\n",
        )
        history = git.get_file_history("test.py")
        assert len(history) == 2
        assert history[0][0] == "abc123"
        assert history[0][1] == datetime.fromisoformat("2024-01-01T12:00:00+00:00")
        assert history[0][2] == "Initial commit"
        assert history[1][0] == "def456"
        assert history[1][1] == datetime.fromisoformat("2024-01-02T12:00:00+00:00")
        assert history[1][2] == "Update file"


@patch("subprocess.run")
def test_get_file_content_at_commit(mock_run):
    """Test getting file content at a specific commit."""
    # Setup
    mock_run.return_value = MagicMock(returncode=0, stdout="true\n")
    with patch("pathlib.Path.exists", return_value=True):
        git = GitIntegration("/test/repo")

        # Test getting file content
        mock_run.return_value = MagicMock(returncode=0, stdout="print('hello')\n")
        content = git.get_file_content_at_commit("test.py", "abc123")
        assert content == "print('hello')\n"

        # Test with binary file
        mock_run.return_value = MagicMock(
            returncode=0, stdout=b"binary content", stderr=""
        )
        content = git.get_file_content_at_commit("test.bin", "abc123")
        assert content == b"binary content"  # Compare with bytes


@patch("subprocess.run")
def test_get_commit_info(mock_run):
    """Test getting commit information."""
    # Setup
    mock_run.return_value = MagicMock(returncode=0, stdout="true\n")
    with patch("pathlib.Path.exists", return_value=True):
        git = GitIntegration("/test/repo")
        git.has_merge_conflicts = MagicMock(
            return_value=False
        )  # Mock has_merge_conflicts

        # Test getting commit info
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="2024-01-01T12:00:00+00:00|Initial commit",  # No trailing newline
        )
        info = git.get_commit_info("abc123")
        assert info[0] == datetime.fromisoformat("2024-01-01T12:00:00+00:00")
        assert info[1] == "Initial commit"

        # Test with invalid commit
        mock_run.return_value = MagicMock(returncode=1, stderr="fatal: bad revision")
        with pytest.raises(GitError, match="Invalid git revision"):
            git.get_commit_info("invalid")


@patch("subprocess.run")
def test_has_merge_conflicts(mock_run):
    """Test checking for merge conflicts."""
    # Setup
    mock_run.return_value = MagicMock(returncode=0, stdout="true\n")
    with patch("pathlib.Path.exists", return_value=True):
        git = GitIntegration("/test/repo")

        # Test when there are conflicts
        mock_run.return_value = MagicMock(returncode=0, stdout="file1.py\nfile2.py\n")
        assert git.has_merge_conflicts() is True

        # Test when there are no conflicts
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        assert git.has_merge_conflicts() is False


@patch("subprocess.run")
def test_get_merge_conflicts(mock_run):
    """Test getting merge conflict files."""
    # Setup
    mock_run.return_value = MagicMock(returncode=0, stdout="true\n")
    with patch("pathlib.Path.exists", return_value=True):
        git = GitIntegration("/test/repo")

        # Test getting conflict files
        mock_run.return_value = MagicMock(returncode=0, stdout="file1.py\nfile2.py\n")
        conflicts = git.get_merge_conflicts()
        assert len(conflicts) == 2
        assert conflicts[0] == Path("/test/repo/file1.py")
        assert conflicts[1] == Path("/test/repo/file2.py")


@patch("subprocess.run")
def test_get_current_branch(mock_run):
    """Test getting current branch name."""
    # Setup
    mock_run.return_value = MagicMock(returncode=0, stdout="true\n")
    with patch("pathlib.Path.exists", return_value=True):
        git = GitIntegration("/test/repo")

        # Test getting current branch
        mock_run.return_value = MagicMock(returncode=0, stdout="main\n")
        assert git.get_current_branch() == "main"

        # Test in detached HEAD state
        mock_run.return_value = MagicMock(
            returncode=1, stderr="fatal: ref HEAD is not a symbolic ref"
        )
        with pytest.raises(GitError, match="Git repository is in detached HEAD state"):
            git.get_current_branch()


@patch("subprocess.run")
def test_get_remotes(mock_run):
    """Test getting git remotes."""
    # Setup
    mock_run.return_value = MagicMock(returncode=0, stdout="true\n")
    with patch("pathlib.Path.exists", return_value=True):
        git = GitIntegration("/test/repo")

        # Test getting remotes
        mock_run.return_value = MagicMock(returncode=0, stdout="origin\nupstream\n")
        remotes = git.get_remotes()
        assert len(remotes) == 2
        assert "origin" in remotes
        assert "upstream" in remotes


@patch("subprocess.run")
def test_get_branches(mock_run):
    """Test getting git branches."""
    # Setup
    mock_run.return_value = MagicMock(returncode=0, stdout="true\n")
    with patch("pathlib.Path.exists", return_value=True):
        git = GitIntegration("/test/repo")

        # Test getting branches
        mock_run.return_value = MagicMock(
            returncode=0, stdout="main\ndevelop\nfeature/new\n"
        )
        branches = git.get_branches()
        assert len(branches) == 3
        assert "main" in branches
        assert "develop" in branches
        assert "feature/new" in branches


@patch("subprocess.run")
def test_get_tag_list(mock_run):
    """Test getting git tags."""
    # Setup
    mock_run.return_value = MagicMock(returncode=0, stdout="true\n")
    with patch("pathlib.Path.exists", return_value=True):
        git = GitIntegration("/test/repo")

        # Test getting tags
        mock_run.return_value = MagicMock(
            returncode=0, stdout="v1.0.0\nv1.1.0\nv2.0.0\n"
        )
        tags = git.get_tag_list()
        assert len(tags) == 3
        assert "v1.0.0" in tags
        assert "v1.1.0" in tags
        assert "v2.0.0" in tags


@patch("subprocess.run")
def test_get_config_value(mock_run):
    """Test getting git config values."""
    # Setup
    mock_run.return_value = MagicMock(returncode=0, stdout="true\n")
    with patch("pathlib.Path.exists", return_value=True):
        git = GitIntegration("/test/repo")

        # Test getting config value
        mock_run.return_value = MagicMock(returncode=0, stdout="value\n")
        value = git.get_config_value("user.name")
        assert value == "value"

        # Test with non-existent config
        mock_run.return_value = MagicMock(returncode=1, stderr="fatal: not found")
        value = git.get_config_value("nonexistent")
        assert value is None


@patch("subprocess.run")
def test_set_config_value(mock_run):
    """Test setting git config values."""
    # Setup
    mock_run.return_value = MagicMock(returncode=0, stdout="true\n")
    with patch("pathlib.Path.exists", return_value=True):
        git = GitIntegration("/test/repo")

        # Test setting config value
        mock_run.return_value = MagicMock(returncode=0)
        git.set_config_value("user.name", "value")
        mock_run.assert_called_with(
            ["git", "config", "user.name", "value"],
            cwd=Path("/test/repo"),
            capture_output=True,
            text=True,
            check=True,
        )


@patch("subprocess.run")
def test_get_hook_path(mock_run):
    """Test getting git hook path."""
    # Setup
    mock_run.return_value = MagicMock(returncode=0, stdout="true\n")
    with patch("pathlib.Path.exists", return_value=True):
        git = GitIntegration("/test/repo")

        # Test getting hook path
        mock_run.return_value = MagicMock(
            returncode=0, stdout="/test/repo/.git/hooks\n"
        )
        hook_path = git.get_hook_path()
        assert hook_path == Path("/test/repo/.git/hooks")


@patch("subprocess.run")
def test_get_repo_root(mock_run):
    """Test getting repository root path."""
    # Setup
    mock_run.return_value = MagicMock(returncode=0, stdout="true\n")
    with patch("pathlib.Path.exists", return_value=True):
        git = GitIntegration("/test/repo")

        # Test getting repo root
        mock_run.return_value = MagicMock(returncode=0, stdout="/test/repo\n")
        root = git.get_repo_root()
        assert root == Path("/test/repo")
