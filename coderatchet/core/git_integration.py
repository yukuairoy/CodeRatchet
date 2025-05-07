"""Git integration functionality."""

import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union


class GitError(Exception):
    """Base exception for Git-related errors."""

    pass


class GitIntegration:
    """Git integration for CodeRatchet."""

    def __init__(self, repo_path: Optional[Union[str, Path]] = None):
        """Initialize Git integration.

        Args:
            repo_path: Path to git repository. If None, uses current directory.

        Raises:
            GitError: If not a git repository
        """
        if repo_path is None:
            repo_path = Path.cwd()
        else:
            repo_path = Path(repo_path)

        # Check if directory exists
        if not repo_path.exists():
            raise GitError(f"Directory does not exist: {repo_path}")

        # Check if it's a git repository
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                raise GitError(f"Not a git repository: {repo_path}")
        except subprocess.CalledProcessError:
            raise GitError(f"Not a git repository: {repo_path}")

        self.repo_path = repo_path

    def _run_git_command(
        self, cmd: List[str], check: bool = True
    ) -> subprocess.CompletedProcess:
        """Run a git command and handle errors consistently.

        Args:
            cmd: List of command arguments
            check: Whether to check the return code

        Returns:
            CompletedProcess object

        Raises:
            GitError: If command fails and check is True
        """
        # Validate command arguments to prevent command injection
        for arg in cmd:
            if not isinstance(arg, str):
                raise GitError(f"Invalid command argument type: {type(arg)}")
            # Allow Git format specifiers (%H, %s, etc.) and other Git-specific characters
            if any(
                c in arg
                for c in [";", "|", "&", ">", "<", "`", "$", "{", "}", "[", "]"]
            ):
                # Only block if it's not a Git format specifier
                if not (arg.startswith("--format=") or arg.startswith("--pretty=")):
                    raise GitError(f"Invalid characters in command argument: {arg}")

        try:
            return subprocess.run(
                ["git"] + cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=check,
            )
        except subprocess.CalledProcessError as e:
            if e.returncode == 128:
                if "not a git repository" in (e.stderr or "").lower():
                    raise GitError("Not a git repository")
                elif "bad revision" in (e.stderr or "").lower():
                    raise GitError("Invalid git revision")
                elif "detached HEAD" in (e.stderr or "").lower():
                    raise GitError("Git repository is in detached HEAD state")
            raise GitError(f"Git command failed: {e.stderr if e.stderr else str(e)}")
        except Exception as e:
            raise GitError(f"Unexpected error running git command: {e}")

    def _get_git_output_lines(self, cmd: List[str], check: bool = True) -> List[str]:
        """Helper method to run git command and return non-empty output lines.

        Args:
            cmd: List of command arguments
            check: Whether to check the return code

        Returns:
            List of non-empty output lines

        Raises:
            GitError: If command fails and check is True
        """
        result = self._run_git_command(cmd, check)
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    def _get_git_paths(self, cmd: List[str], check: bool = True) -> List[Path]:
        """Helper method to run git command and return list of paths.

        Args:
            cmd: List of command arguments
            check: Whether to check the return code

        Returns:
            List of Path objects

        Raises:
            GitError: If command fails and check is True
        """
        return [
            self.repo_path / line for line in self._get_git_output_lines(cmd, check)
        ]

    def is_git_repo(self) -> bool:
        """Check if repository is a Git repository.

        Returns:
            True if repository is a Git repository, False otherwise
        """
        result = self._run_git_command(
            ["rev-parse", "--is-inside-work-tree"], check=False
        )
        return result.returncode == 0

    def is_detached_head(self) -> bool:
        """Check if repository is in detached HEAD state.

        Returns:
            True if in detached HEAD state, False otherwise
        """
        result = self._run_git_command(["symbolic-ref", "-q", "HEAD"], check=False)
        return result.returncode == 1

    def get_current_branch(self) -> str:
        """Get current Git branch name.

        Returns:
            Current branch name

        Raises:
            GitError: If in detached HEAD state
        """
        if self.is_detached_head():
            raise GitError("Git repository is in detached HEAD state")
        result = self._run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])
        return result.stdout.strip()

    def get_changed_files(self, base_branch: Optional[str] = None) -> List[Path]:
        """Get list of files changed compared to base branch.

        Args:
            base_branch: Base branch to compare against. If None, compares against HEAD.

        Returns:
            List of changed file paths

        Raises:
            GitError: If there are merge conflicts or repository is in detached HEAD state
        """
        if self.is_detached_head():
            raise GitError("Repository is in detached HEAD state")

        if self.has_merge_conflicts():
            raise GitError("Repository has merge conflicts")

        cmd = ["diff", "--name-only"]
        if base_branch:
            merge_base = self._run_git_command(
                ["merge-base", base_branch, "HEAD"]
            ).stdout.strip()
            cmd.append(merge_base)
        else:
            cmd.append("HEAD")

        return self._get_git_paths(cmd)

    def get_file_history(
        self, filepath: Union[str, Path]
    ) -> List[Tuple[str, datetime, str]]:
        """Get commit history for a file.

        Args:
            filepath: Path to the file

        Returns:
            List of tuples (commit_hash, commit_date, commit_message)
        """
        filepath = Path(filepath)
        if not filepath.is_absolute():
            filepath = self.repo_path / filepath

        result = self._run_git_command(
            ["log", "--format=%H|%aI|%s", "--follow", "--", str(filepath)]
        )

        history = []
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            commit_hash, date_str, message = line.strip().split("|", 2)
            history.append((commit_hash, datetime.fromisoformat(date_str), message))
        return history

    def get_file_content_at_commit(
        self, filepath: Union[str, Path], commit_hash: str
    ) -> Union[str, bytes]:
        """Get file content at a specific commit.

        Args:
            filepath: Path to the file
            commit_hash: Commit hash

        Returns:
            File content as string or bytes for binary files

        Raises:
            GitError: If file or commit not found
        """
        filepath = Path(filepath)
        if filepath.is_absolute():
            try:
                filepath = filepath.relative_to(self.repo_path)
            except ValueError:
                raise GitError(f"File {filepath} is not in repository {self.repo_path}")

        result = self._run_git_command(["show", f"{commit_hash}:{filepath}"])
        return result.stdout if isinstance(result.stdout, str) else result.stdout

    def get_commit_info(self, commit_hash: str) -> Optional[Tuple[datetime, str]]:
        """Get commit information.

        Args:
            commit_hash: Commit hash

        Returns:
            Tuple of (commit_date, commit_message) or None if commit not found

        Raises:
            GitError: If repository has merge conflicts or commit not found
        """
        if self.has_merge_conflicts():
            raise GitError(
                "Cannot get commit info while repository has merge conflicts"
            )

        result = self._run_git_command(
            ["show", "-s", "--format=%aI|%s", commit_hash], check=False
        )

        if result.returncode != 0:
            raise GitError("Invalid git revision")

        if not result.stdout.strip():
            return None

        date_str, message = result.stdout.strip().split("|", 1)
        return datetime.fromisoformat(date_str), message

    def has_merge_conflicts(self) -> bool:
        """Check if repository has merge conflicts.

        Returns:
            True if repository has merge conflicts, False otherwise
        """
        return bool(
            self._get_git_output_lines(["diff", "--name-only", "--diff-filter=U"])
        )

    def get_merge_conflicts(self) -> List[Path]:
        """Get list of files with merge conflicts.

        Returns:
            List of file paths with merge conflicts
        """
        return self._get_git_paths(["diff", "--name-only", "--diff-filter=U"])

    def add_submodule(self, url: str, path: str) -> None:
        """Add a Git submodule.

        Args:
            url: Submodule repository URL
            path: Path where to add the submodule
        """
        if self.is_detached_head():
            raise GitError("Git repository is in detached HEAD state")
        try:
            # First try to clone the repository to verify it exists
            subprocess.check_output(
                ["git", "clone", "--depth", "1", url, path],
                stderr=subprocess.STDOUT,
                cwd=self.repo_path,
            )

            # Then add it as a submodule
            subprocess.check_output(
                ["git", "submodule", "add", "-f", url, path],
                stderr=subprocess.STDOUT,
                cwd=self.repo_path,
            )
        except subprocess.CalledProcessError as e:
            raise GitError(f"Failed to add submodule: {e.output.decode()}")

    def init_submodules(self) -> None:
        """Initialize Git submodules."""
        if self.is_detached_head():
            raise GitError("Git repository is in detached HEAD state")
        try:
            subprocess.check_output(
                ["git", "submodule", "init"],
                stderr=subprocess.STDOUT,
                cwd=self.repo_path,
            )
        except subprocess.CalledProcessError as e:
            raise GitError(f"Failed to initialize submodules: {e.output.decode()}")

    def update_submodules(self) -> None:
        """Update Git submodules."""
        if self.is_detached_head():
            raise GitError("Git repository is in detached HEAD state")
        try:
            subprocess.check_output(
                ["git", "submodule", "update", "--init", "--recursive"],
                stderr=subprocess.STDOUT,
                cwd=self.repo_path,
            )
        except subprocess.CalledProcessError as e:
            raise GitError(f"Failed to update submodules: {e.output.decode()}")

    def remove_submodule(self, path: str) -> None:
        """Remove a Git submodule.

        Args:
            path: Path to the submodule
        """
        if self.is_detached_head():
            raise GitError("Git repository is in detached HEAD state")
        try:
            # Remove the submodule from .git/config
            subprocess.check_output(
                ["git", "submodule", "deinit", "-f", path],
                stderr=subprocess.STDOUT,
                cwd=self.repo_path,
            )

            # Remove the submodule from .git/modules
            subprocess.check_output(
                ["rm", "-rf", f".git/modules/{path}"],
                stderr=subprocess.STDOUT,
                cwd=self.repo_path,
            )

            # Remove the submodule from the working tree
            subprocess.check_output(
                ["git", "rm", "-f", path],
                stderr=subprocess.STDOUT,
                cwd=self.repo_path,
            )
        except subprocess.CalledProcessError as e:
            raise GitError(f"Failed to remove submodule: {e.output.decode()}")

    def get_submodule_status(self, path: str) -> Tuple[str, str]:
        """Get status of a Git submodule.

        Args:
            path: Path to the submodule

        Returns:
            Tuple of (commit hash, status)
        """
        if self.is_detached_head():
            raise GitError("Git repository is in detached HEAD state")
        try:
            output = (
                subprocess.check_output(
                    ["git", "submodule", "status", path],
                    stderr=subprocess.STDOUT,
                    cwd=self.repo_path,
                )
                .decode()
                .strip()
            )
            if not output:
                raise GitError(f"Submodule not found: {path}")
            status = output[0]
            commit_hash = output[1:41]
            return commit_hash, {
                " ": "up to date",
                "+": "needs update",
                "-": "not initialized",
                "U": "merge conflicts",
            }.get(status, "unknown")
        except subprocess.CalledProcessError as e:
            raise GitError(f"Failed to get submodule status: {e.output.decode()}")

    def sync_submodules(self) -> None:
        """Sync Git submodules."""
        if self.is_detached_head():
            raise GitError("Git repository is in detached HEAD state")
        try:
            subprocess.check_output(
                ["git", "submodule", "sync", "--recursive"],
                stderr=subprocess.STDOUT,
                cwd=self.repo_path,
            )
        except subprocess.CalledProcessError as e:
            raise GitError(f"Failed to sync submodules: {e.output.decode()}")

    def foreach_submodule(self, command: str) -> Dict[str, str]:
        """Run a command in each submodule.

        Args:
            command: Command to run

        Returns:
            Dictionary mapping submodule paths to command output
        """
        if self.is_detached_head():
            raise GitError("Git repository is in detached HEAD state")
        try:
            output = subprocess.check_output(
                ["git", "submodule", "foreach", command],
                stderr=subprocess.STDOUT,
                cwd=self.repo_path,
            ).decode()
            results = {}
            current_submodule = None
            current_output = []
            for line in output.splitlines():
                if line.startswith("Entering '"):
                    if current_submodule:
                        results[current_submodule] = "\n".join(current_output)
                    current_submodule = line[10:-1]
                    current_output = []
                else:
                    current_output.append(line)
            if current_submodule:
                results[current_submodule] = "\n".join(current_output)
            return results
        except subprocess.CalledProcessError as e:
            raise GitError(f"Failed to run command in submodules: {e.output.decode()}")

    def get_submodule_remote_url(self, path: str) -> str:
        """Get remote URL of a Git submodule.

        Args:
            path: Path to the submodule

        Returns:
            Remote URL
        """
        if self.is_detached_head():
            raise GitError("Git repository is in detached HEAD state")
        try:
            output = (
                subprocess.check_output(
                    ["git", "config", "-f", ".gitmodules", f"submodule.{path}.url"],
                    stderr=subprocess.STDOUT,
                    cwd=self.repo_path,
                )
                .decode()
                .strip()
            )
            return output
        except subprocess.CalledProcessError as e:
            raise GitError(f"Failed to get submodule remote URL: {e.output.decode()}")

    def set_submodule_remote_url(self, path: str, url: str) -> None:
        """Set remote URL of a Git submodule.

        Args:
            path: Path to the submodule
            url: New remote URL
        """
        if self.is_detached_head():
            raise GitError("Git repository is in detached HEAD state")
        try:
            subprocess.check_output(
                ["git", "config", "-f", ".gitmodules", f"submodule.{path}.url", url],
                stderr=subprocess.STDOUT,
                cwd=self.repo_path,
            )
            subprocess.check_output(
                ["git", "submodule", "sync", path],
                stderr=subprocess.STDOUT,
                cwd=self.repo_path,
            )
        except subprocess.CalledProcessError as e:
            raise GitError(f"Failed to set submodule remote URL: {e.output.decode()}")

    def get_submodule_branch(self, path: str) -> str:
        """Get branch of a Git submodule.

        Args:
            path: Path to the submodule

        Returns:
            Branch name
        """
        if self.is_detached_head():
            raise GitError("Git repository is in detached HEAD state")
        try:
            output = (
                subprocess.check_output(
                    ["git", "config", "-f", ".gitmodules", f"submodule.{path}.branch"],
                    stderr=subprocess.STDOUT,
                    cwd=self.repo_path,
                )
                .decode()
                .strip()
            )
            return output
        except subprocess.CalledProcessError as e:
            raise GitError(f"Failed to get submodule branch: {e.output.decode()}")

    def set_submodule_branch(self, path: str, branch: str) -> None:
        """Set branch of a Git submodule.

        Args:
            path: Path to the submodule
            branch: Branch name
        """
        if self.is_detached_head():
            raise GitError("Git repository is in detached HEAD state")
        try:
            subprocess.check_output(
                [
                    "git",
                    "config",
                    "-f",
                    ".gitmodules",
                    f"submodule.{path}.branch",
                    branch,
                ],
                stderr=subprocess.STDOUT,
                cwd=self.repo_path,
            )
            subprocess.check_output(
                ["git", "submodule", "sync", path],
                stderr=subprocess.STDOUT,
                cwd=self.repo_path,
            )
        except subprocess.CalledProcessError as e:
            raise GitError(f"Failed to set submodule branch: {e.output.decode()}")

    def get_submodule_path(self, path: str) -> str:
        """Get path of a Git submodule.

        Args:
            path: Path to the submodule

        Returns:
            Absolute path
        """
        if self.is_detached_head():
            raise GitError("Git repository is in detached HEAD state")
        try:
            output = (
                subprocess.check_output(
                    ["git", "config", "-f", ".gitmodules", f"submodule.{path}.path"],
                    stderr=subprocess.STDOUT,
                    cwd=self.repo_path,
                )
                .decode()
                .strip()
            )
            return str(Path(self.repo_path) / output)
        except subprocess.CalledProcessError as e:
            raise GitError(f"Failed to get submodule path: {e.output.decode()}")

    def set_submodule_path(self, path: str, new_path: str) -> None:
        """Set path of a Git submodule.

        Args:
            path: Current path to the submodule
            new_path: New path
        """
        if self.is_detached_head():
            raise GitError("Git repository is in detached HEAD state")
        try:
            subprocess.check_output(
                [
                    "git",
                    "config",
                    "-f",
                    ".gitmodules",
                    f"submodule.{path}.path",
                    new_path,
                ],
                stderr=subprocess.STDOUT,
                cwd=self.repo_path,
            )
            subprocess.check_output(
                ["git", "submodule", "sync", path],
                stderr=subprocess.STDOUT,
                cwd=self.repo_path,
            )
        except subprocess.CalledProcessError as e:
            raise GitError(f"Failed to set submodule path: {e.output.decode()}")

    def get_submodule_ignore(self, path: str) -> str:
        """Get ignore setting of a Git submodule.

        Args:
            path: Path to the submodule

        Returns:
            Ignore setting
        """
        if self.is_detached_head():
            raise GitError("Git repository is in detached HEAD state")
        try:
            output = (
                subprocess.check_output(
                    ["git", "config", "-f", ".gitmodules", f"submodule.{path}.ignore"],
                    stderr=subprocess.STDOUT,
                    cwd=self.repo_path,
                )
                .decode()
                .strip()
            )
            return output
        except subprocess.CalledProcessError as e:
            raise GitError(
                f"Failed to get submodule ignore setting: {e.output.decode()}"
            )

    def set_submodule_ignore(self, path: str, ignore: str) -> None:
        """Set ignore setting of a Git submodule.

        Args:
            path: Path to the submodule
            ignore: Ignore setting
        """
        if self.is_detached_head():
            raise GitError("Git repository is in detached HEAD state")
        try:
            subprocess.check_output(
                [
                    "git",
                    "config",
                    "-f",
                    ".gitmodules",
                    f"submodule.{path}.ignore",
                    ignore,
                ],
                stderr=subprocess.STDOUT,
                cwd=self.repo_path,
            )
            subprocess.check_output(
                ["git", "submodule", "sync", path],
                stderr=subprocess.STDOUT,
                cwd=self.repo_path,
            )
        except subprocess.CalledProcessError as e:
            raise GitError(
                f"Failed to set submodule ignore setting: {e.output.decode()}"
            )

    def get_submodule_update(self, path: str) -> str:
        """Get update setting of a Git submodule.

        Args:
            path: Path to the submodule

        Returns:
            Update setting
        """
        if self.is_detached_head():
            raise GitError("Git repository is in detached HEAD state")
        try:
            output = (
                subprocess.check_output(
                    ["git", "config", "-f", ".gitmodules", f"submodule.{path}.update"],
                    stderr=subprocess.STDOUT,
                    cwd=self.repo_path,
                )
                .decode()
                .strip()
            )
            return output
        except subprocess.CalledProcessError as e:
            raise GitError(
                f"Failed to get submodule update setting: {e.output.decode()}"
            )

    def set_submodule_update(self, path: str, update: str) -> None:
        """Set update setting of a Git submodule.

        Args:
            path: Path to the submodule
            update: Update setting
        """
        if self.is_detached_head():
            raise GitError("Git repository is in detached HEAD state")
        try:
            subprocess.check_output(
                [
                    "git",
                    "config",
                    "-f",
                    ".gitmodules",
                    f"submodule.{path}.update",
                    update,
                ],
                stderr=subprocess.STDOUT,
                cwd=self.repo_path,
            )
            subprocess.check_output(
                ["git", "submodule", "sync", path],
                stderr=subprocess.STDOUT,
                cwd=self.repo_path,
            )
        except subprocess.CalledProcessError as e:
            raise GitError(
                f"Failed to set submodule update setting: {e.output.decode()}"
            )

    def get_submodule_shallow(self, path: str) -> bool:
        """Get shallow clone setting of a Git submodule.

        Args:
            path: Path to the submodule

        Returns:
            True if shallow clone is enabled
        """
        if self.is_detached_head():
            raise GitError("Git repository is in detached HEAD state")
        try:
            output = (
                subprocess.check_output(
                    ["git", "config", "-f", ".gitmodules", f"submodule.{path}.shallow"],
                    stderr=subprocess.STDOUT,
                    cwd=self.repo_path,
                )
                .decode()
                .strip()
            )
            return output.lower() == "true"
        except subprocess.CalledProcessError as e:
            raise GitError(
                f"Failed to get submodule shallow setting: {e.output.decode()}"
            )

    def set_submodule_shallow(self, path: str, shallow: bool) -> None:
        """Set shallow clone setting of a Git submodule.

        Args:
            path: Path to the submodule
            shallow: True to enable shallow clone
        """
        if self.is_detached_head():
            raise GitError("Git repository is in detached HEAD state")
        try:
            subprocess.check_output(
                [
                    "git",
                    "config",
                    "-f",
                    ".gitmodules",
                    f"submodule.{path}.shallow",
                    str(shallow).lower(),
                ],
                stderr=subprocess.STDOUT,
                cwd=self.repo_path,
            )
            subprocess.check_output(
                ["git", "submodule", "sync", path],
                stderr=subprocess.STDOUT,
                cwd=self.repo_path,
            )
        except subprocess.CalledProcessError as e:
            raise GitError(
                f"Failed to set submodule shallow setting: {e.output.decode()}"
            )

    def get_submodule_recursive(self, path: str) -> bool:
        """Get recursive clone setting of a Git submodule.

        Args:
            path: Path to the submodule

        Returns:
            True if recursive clone is enabled
        """
        if self.is_detached_head():
            raise GitError("Git repository is in detached HEAD state")
        try:
            output = (
                subprocess.check_output(
                    [
                        "git",
                        "config",
                        "-f",
                        ".gitmodules",
                        f"submodule.{path}.recursive",
                    ],
                    stderr=subprocess.STDOUT,
                    cwd=self.repo_path,
                )
                .decode()
                .strip()
            )
            return output.lower() == "true"
        except subprocess.CalledProcessError as e:
            raise GitError(
                f"Failed to get submodule recursive setting: {e.output.decode()}"
            )

    def set_submodule_recursive(self, path: str, recursive: bool) -> None:
        """Set recursive clone setting of a Git submodule.

        Args:
            path: Path to the submodule
            recursive: True to enable recursive clone
        """
        if self.is_detached_head():
            raise GitError("Git repository is in detached HEAD state")
        try:
            subprocess.check_output(
                [
                    "git",
                    "config",
                    "-f",
                    ".gitmodules",
                    f"submodule.{path}.recursive",
                    str(recursive).lower(),
                ],
                stderr=subprocess.STDOUT,
                cwd=self.repo_path,
            )
            subprocess.check_output(
                ["git", "submodule", "sync", path],
                stderr=subprocess.STDOUT,
                cwd=self.repo_path,
            )
        except subprocess.CalledProcessError as e:
            raise GitError(
                f"Failed to set submodule recursive setting: {e.output.decode()}"
            )

    def get_submodule_fetchRecurseSubmodules(self, path: str) -> bool:
        """Get fetch recurse submodules setting of a Git submodule.

        Args:
            path: Path to the submodule

        Returns:
            True if fetch recurse submodules is enabled
        """
        if self.is_detached_head():
            raise GitError("Git repository is in detached HEAD state")
        try:
            output = (
                subprocess.check_output(
                    [
                        "git",
                        "config",
                        "-f",
                        ".gitmodules",
                        f"submodule.{path}.fetchRecurseSubmodules",
                    ],
                    stderr=subprocess.STDOUT,
                    cwd=self.repo_path,
                )
                .decode()
                .strip()
            )
            return output.lower() == "true"
        except subprocess.CalledProcessError as e:
            raise GitError(
                f"Failed to get submodule fetch recurse submodules setting: {e.output.decode()}"
            )

    def set_submodule_fetchRecurseSubmodules(
        self, path: str, fetch_recurse: bool
    ) -> None:
        """Set fetch recurse submodules setting of a Git submodule.

        Args:
            path: Path to the submodule
            fetch_recurse: True to enable fetch recurse submodules
        """
        if self.is_detached_head():
            raise GitError("Git repository is in detached HEAD state")
        try:
            subprocess.check_output(
                [
                    "git",
                    "config",
                    "-f",
                    ".gitmodules",
                    f"submodule.{path}.fetchRecurseSubmodules",
                    str(fetch_recurse).lower(),
                ],
                stderr=subprocess.STDOUT,
                cwd=self.repo_path,
            )
            subprocess.check_output(
                ["git", "submodule", "sync", path],
                stderr=subprocess.STDOUT,
                cwd=self.repo_path,
            )
        except subprocess.CalledProcessError as e:
            raise GitError(
                f"Failed to set submodule fetch recurse submodules setting: {e.output.decode()}"
            )

    def get_remotes(self) -> List[str]:
        """Get list of Git remotes.

        Returns:
            List of remote names
        """
        return self._get_git_output_lines(["remote"])

    def get_branches(self) -> List[str]:
        """Get list of Git branches.

        Returns:
            List of branch names
        """
        return self._get_git_output_lines(
            ["branch", "--list", "--format=%(refname:short)"]
        )

    def get_merge_base(self, commit1: str, commit2: str) -> str:
        """Get the merge base of two commits.

        Args:
            commit1: First commit reference
            commit2: Second commit reference

        Returns:
            Merge base commit hash
        """
        result = self._run_git_command(["merge-base", commit1, commit2])
        return result.stdout.strip()

    def get_commit_files(self, commit_hash: str) -> List[Path]:
        """Get list of files changed in a commit.

        Args:
            commit_hash: Commit hash

        Returns:
            List of changed file paths
        """
        return self._get_git_paths(
            ["diff-tree", "--no-commit-id", "--name-only", "-r", commit_hash]
        )

    def get_file_blame(
        self, filepath: Union[str, Path]
    ) -> List[Tuple[str, str, int, str]]:
        """Get blame information for a file.

        Args:
            filepath: Path to file

        Returns:
            List of (commit_hash, author, line_number, line_content) tuples
        """
        filepath = Path(filepath)
        if filepath.is_absolute():
            try:
                filepath = filepath.relative_to(self.repo_path)
            except ValueError:
                raise GitError(f"File {filepath} is not in repository {self.repo_path}")

        # Use a simpler format that's easier to parse
        result = self._run_git_command(
            [
                "blame",
                "--line-porcelain",  # Output in a more structured format
                str(filepath),
            ]
        )

        blame_info = []
        lines = result.stdout.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]
            if not line.strip():
                i += 1
                continue

            # Each section starts with the commit hash and line info
            if line[0].isalnum():
                parts = line.split()
                if len(parts) >= 3:
                    commit_hash = parts[0]
                    line_number = int(parts[2])

                    # Skip to author line
                    while i < len(lines) and not lines[i].startswith("author "):
                        i += 1
                    if i < len(lines):
                        author = lines[i][7:]  # Remove 'author ' prefix

                        # Skip to content line
                        while i < len(lines) and not lines[i].startswith("\t"):
                            i += 1
                        if i < len(lines):
                            content = lines[i][1:]  # Remove tab prefix
                            blame_info.append(
                                (commit_hash, author, line_number, content)
                            )
            i += 1

        return sorted(blame_info, key=lambda x: x[2])  # Sort by line number

    def get_stash_list(self) -> List[Tuple[str, str]]:
        """Get list of stashes.

        Returns:
            List of (stash_hash, stash_message) tuples
        """
        result = self._run_git_command(["stash", "list", "--format=%H %s"])
        stashes = []
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            parts = line.split(" ", 1)
            if len(parts) == 2:
                stash_hash, message = parts
                # Remove branch prefix from message if present
                if message.startswith("On "):
                    message = message.split(": ", 1)[1]
                stashes.append((stash_hash, message))
        return stashes

    def get_tag_list(self) -> List[str]:
        """Get list of Git tags.

        Returns:
            List of tag names
        """
        return self._get_git_output_lines(["tag", "--list"])

    def get_config_value(self, key: str) -> Optional[str]:
        """Get Git config value.

        Args:
            key: Config key

        Returns:
            Config value or None if not found
        """
        result = self._run_git_command(["config", "--get", key], check=False)
        return result.stdout.strip() if result.returncode == 0 else None

    def set_config_value(self, key: str, value: str) -> None:
        """Set Git config value.

        Args:
            key: Config key
            value: Config value
        """
        self._run_git_command(["config", key, value])

    def get_hook_path(self) -> Path:
        """Get path to Git hooks directory.

        Returns:
            Path to hooks directory
        """
        result = self._run_git_command(["rev-parse", "--git-path", "hooks"])
        return Path(result.stdout.strip())

    def get_repo_root(self) -> Path:
        """Get repository root path.

        Returns:
            Repository root path
        """
        result = self._run_git_command(["rev-parse", "--show-toplevel"])
        return Path(result.stdout.strip())

    def get_git_history(
        self, limit: Optional[int] = None
    ) -> List[Tuple[str, datetime, str]]:
        """Get Git commit history.

        Args:
            limit: Maximum number of commits to return. If None, returns all commits.

        Returns:
            List of (commit_hash, commit_date, commit_message) tuples

        Raises:
            GitError: If there is an error getting the Git history
        """
        if self.is_detached_head():
            raise GitError("Git repository is in detached HEAD state")

        cmd = ["log", "--format=%H %at %s"]
        if limit is not None:
            cmd.append(f"-n{limit}")

        result = self._run_git_command(cmd)

        history = []
        for line in result.stdout.splitlines():
            try:
                commit_hash, timestamp, *message_parts = line.split()
                commit_date = datetime.fromtimestamp(int(timestamp))
                commit_message = " ".join(message_parts)
                history.append((commit_hash, commit_date, commit_message))
            except (ValueError, IndexError) as e:
                raise GitError(f"Invalid git log output: {e}")

        return history


def init_git_repo(repo_path: Path) -> None:
    """Initialize a Git repository.

    Args:
        repo_path: Path to initialize repository in

    Raises:
        GitError: If repository initialization fails
    """
    try:
        subprocess.run(
            ["git", "init"], cwd=repo_path, check=True, capture_output=True, text=True
        )
    except subprocess.CalledProcessError as e:
        raise GitError(f"Failed to initialize Git repository: {e.stderr}")
    except Exception as e:
        raise GitError(f"Unexpected error initializing Git repository: {e}")


def add_and_commit(repo_path: Path, message: str) -> None:
    """Add all changes and create a commit.

    Args:
        repo_path: Path to repository
        message: Commit message

    Raises:
        GitError: If commit fails
    """
    try:
        # Add all changes
        subprocess.run(
            ["git", "add", "."],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
        )

        # Configure Git user if not set
        try:
            subprocess.run(
                ["git", "config", "user.name"],
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError:
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True,
            )

        # Create commit
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        raise GitError(f"Failed to create commit: {e.stderr}")
    except Exception as e:
        raise GitError(f"Unexpected error creating commit: {e}")


def is_git_repo(path: Path) -> bool:
    """Check if path is a Git repository.

    Args:
        path: Path to check

    Returns:
        True if path is a Git repository, False otherwise
    """
    try:
        subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=path,
            check=True,
            capture_output=True,
        )
        return True
    except (subprocess.CalledProcessError, OSError):
        return False
