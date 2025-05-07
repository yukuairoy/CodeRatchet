"""
Functionality for detecting recently broken ratchets.
"""

import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple, Union

import attr

from .config import get_ratchet_tests
from .git_integration import GitIntegration
from .ratchet import TestFailure
from .utils import get_ratchet_test_files

logger = logging.getLogger(__name__)


@attr.s(frozen=True, auto_attribs=True)
class BrokenRatchet:
    """A broken ratchet with commit information."""

    test_name: str
    filepath: str
    line_number: int
    line_contents: str
    commit_hash: Optional[str] = None
    commit_date: Optional[datetime] = None
    commit_message: Optional[str] = None


class GitHistoryManager:
    """Manages git history and commit information."""

    def __init__(self, git_integration: GitIntegration):
        self.git = git_integration

    def get_history(
        self, since_commit: Optional[str] = None
    ) -> List[Tuple[str, datetime, str]]:
        """Get git commit history.

        Args:
            since_commit: Only get commits since this commit hash

        Returns:
            List of tuples (commit_hash, commit_date, commit_message)
        """
        try:
            cmd = ["log", "--format=%H %ct %s"]
            if since_commit:
                cmd.extend(["--", since_commit])

            result = self.git._run_git_command(cmd)
            history = []

            for line in result.stdout.splitlines():
                parts = line.split(" ", 2)
                if len(parts) == 3:
                    commit_hash, commit_date_str, commit_message = parts
                    try:
                        commit_date = datetime.fromtimestamp(
                            int(commit_date_str), tz=timezone.utc
                        )
                        history.append((commit_hash, commit_date, commit_message))
                    except (ValueError, TypeError):
                        logger.warning(
                            f"Invalid timestamp in git log: {commit_date_str}"
                        )
                        continue

            return history
        except subprocess.CalledProcessError:
            logger.warning(f"Failed to get git history: {since_commit}")
            return []

    def get_file_commits(
        self, filepath: str, history: List[Tuple[str, datetime, str]]
    ) -> List[Tuple[str, datetime, str]]:
        """Get commits that modified a file.

        Args:
            filepath: Path to the file
            history: List of commits to check

        Returns:
            List of tuples containing (commit_hash, commit_date, commit_message)
        """
        try:
            result = self.git._run_git_command(
                ["log", "--format=%H %ct %s", "--", filepath]
            )

            commits = []
            seen_commits = set()

            for line in result.stdout.splitlines():
                if not line.strip():
                    continue
                try:
                    commit_hash, timestamp, message = line.strip().split(" ", 2)
                    if commit_hash not in seen_commits:
                        seen_commits.add(commit_hash)
                        # Find the commit info in history
                        for hist_hash, hist_date, hist_message in history:
                            if commit_hash == hist_hash:
                                commits.append((hist_hash, hist_date, hist_message))
                                break
                except (ValueError, TypeError):
                    logger.warning(f"Failed to parse git log line: {line}")
                    continue

            return commits
        except subprocess.CalledProcessError:
            return []

    def get_blame_info(
        self, filepath: str, line_number: int
    ) -> Optional[Tuple[str, datetime, str]]:
        """Get git blame info for a specific line.

        Args:
            filepath: Path to the file
            line_number: Line number to get blame info for

        Returns:
            Tuple of (commit_hash, commit_date, commit_message) or None if not found
        """
        try:
            result = self.git._run_git_command(
                ["blame", "-L", f"{line_number},{line_number}", "--porcelain", filepath]
            )

            if not result.stdout.strip():
                return None

            # First line contains the commit hash
            commit_hash = result.stdout.split()[0]

            # Get commit info
            commit_info = self.git.get_commit_info(commit_hash)
            if not commit_info:
                return None

            commit_date, commit_message = commit_info
            return commit_hash, commit_date, commit_message

        except (subprocess.CalledProcessError, ValueError, IndexError) as e:
            logger.debug(f"Failed to get git blame info: {e}")
            return None


def get_recently_broken_ratchets(
    limit: int = 10,
    include_commits: bool = False,
    git_integration: Optional[GitIntegration] = None,
    additional_dirs: Optional[List[Path]] = None,
) -> List[Union[TestFailure, BrokenRatchet]]:
    """Get list of recently broken ratchets.

    Args:
        limit: Maximum number of failures to return
        include_commits: Whether to include commit information
        git_integration: Optional GitIntegration instance
        additional_dirs: Optional list of additional directories to search

    Returns:
        List of test failures or broken ratchets
    """
    # Get ratchet tests
    tests = get_ratchet_tests(return_set=True)
    print(f"DEBUG: Found {len(tests)} ratchet tests")
    if not tests:
        return []

    # Get files to check
    files = get_ratchet_test_files(additional_dirs=additional_dirs)
    print(f"DEBUG: Found {len(files)} files to check")
    failures = []

    # Initialize git integration if needed
    if include_commits:
        git = git_integration or GitIntegration()
        git_manager = GitHistoryManager(git)

    # Check each file with each test
    for test in tests:
        print(f"DEBUG: Running test {test.name}")
        for file in files:
            try:
                # Skip if file doesn't exist or can't be read
                if not os.path.exists(file) or not os.access(file, os.R_OK):
                    logger.warning(f"Skipping inaccessible file: {file}")
                    continue

                # Read file content
                with open(file, "r") as f:
                    content = f.read()
                    lines = content.splitlines()

                # Collect failures
                test.collect_failures_from_lines(lines, file)
                if test._failures:  # Access private attribute since it's frozen
                    print(f"DEBUG: Found {len(test._failures)} failures in {file}")
                    failures.extend(test._failures)

            except (IOError, OSError) as e:
                logger.error(f"Failed to read file {file}: {e}")
                continue

    # Remove duplicates while preserving order
    seen = set()
    unique_failures = []
    for failure in failures:
        key = (
            failure.test_name,
            failure.filepath,
            failure.line_number,
            failure.line_contents,
        )
        if key not in seen:
            seen.add(key)
            unique_failures.append(failure)

    # Sort failures by line number
    unique_failures.sort(key=lambda f: (f.filepath, f.line_number))
    print(f"DEBUG: Found {len(unique_failures)} unique failures")

    # Add commit information if requested
    if include_commits:
        failures_with_commits = []
        for failure in unique_failures[:limit]:
            # Get the most recent commit that modified this file
            result = git_manager.git._run_git_command(
                ["log", "-1", "--format=%H %ct %s", "--", failure.filepath]
            )
            if result.stdout.strip():
                commit_hash, timestamp, message = result.stdout.strip().split(" ", 2)
                commit_date = datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
                failures_with_commits.append(
                    BrokenRatchet(
                        test_name=failure.test_name,
                        filepath=failure.filepath,
                        line_number=failure.line_number,
                        line_contents=failure.line_contents,
                        commit_hash=commit_hash,
                        commit_date=commit_date,
                        commit_message=message,
                    )
                )
            else:
                # If no commit info, still include the failure but without commit info
                failures_with_commits.append(
                    BrokenRatchet(
                        test_name=failure.test_name,
                        filepath=failure.filepath,
                        line_number=failure.line_number,
                        line_contents=failure.line_contents,
                    )
                )
        return failures_with_commits[:limit]

    return unique_failures[:limit]


# Remove test functions since they've been moved to test_recent_failures.py
