"""Examples of CI/CD integration with CodeRatchet."""

import os
import sys
from typing import List

from coderatchet.core.git_integration import GitError, GitIntegration
from coderatchet.core.ratchet import RatchetTest, RegexBasedRatchetTest
from coderatchet.utils.logger import logger


def get_ci_ratchets() -> List[RatchetTest]:
    """Get CI-specific ratchet tests.

    Returns:
        List of ratchet tests for CI/CD best practices
    """
    return [
        RegexBasedRatchetTest(
            name="no_debug_in_ci",
            pattern=r"print\s*\(['\"]DEBUG:",
            description="No debug prints in CI",
            match_examples=[
                "print('DEBUG: test')",
                'print("DEBUG: value")',
            ],
            non_match_examples=[
                "print('Info: test')",
                'logger.debug("test")',
            ],
        ),
        RegexBasedRatchetTest(
            name="no_hardcoded_ci_tokens",
            pattern=r"(?i)(?:token|secret|password|key)\s*=\s*['\"][^'\"]+['\"]",
            description="No hardcoded CI tokens",
            match_examples=[
                'TOKEN="abc123"',
                "password='secret'",
                'API_KEY = "xyz789"',
            ],
            non_match_examples=[
                'token = os.environ["TOKEN"]',
                "password = get_password()",
            ],
        ),
    ]


class CIRatchetRunner:
    """Helper class for running ratchets in CI environments."""

    def __init__(
        self,
        ratchets: List[RatchetTest],
        base_branch: str = "main",
        fail_on_violations: bool = True,
    ):
        """Initialize the CI runner.

        Args:
            ratchets: List of ratchet tests to run
            base_branch: The base branch to compare against
            fail_on_violations: Whether to fail the CI if violations are found
        """
        self.ratchets = ratchets
        self.base_branch = base_branch
        self.fail_on_violations = fail_on_violations
        self.git = GitIntegration()

    def run(self) -> bool:
        """Run the ratchet tests and return whether they passed.

        Returns:
            bool: True if all tests passed or violations are allowed, False otherwise

        Raises:
            GitError: If there are issues with Git operations
            IOError: If there are issues reading files
        """
        try:
            # Get changed files
            try:
                changed_files = self.git.get_changed_files(self.base_branch)
            except GitError as e:
                logger.error(f"Failed to get changed files: {e}")
                if "merge conflicts" in str(e).lower():
                    logger.warning("Skipping ratchet checks due to merge conflicts")
                    return True
                raise

            if not changed_files:
                logger.info("No files changed, skipping ratchet checks")
                return True

            # Clear any existing failures
            for ratchet in self.ratchets:
                ratchet.clear_failures()

            # Run ratchets on changed files
            all_failures = []
            for file_path in changed_files:
                if not file_path.endswith(".py"):
                    continue

                try:
                    with open(file_path, "r") as f:
                        lines = f.readlines()

                    for ratchet in self.ratchets:
                        ratchet.collect_failures_from_lines(lines, file_path)
                except IOError as e:
                    logger.error(f"Error reading file {file_path}: {e}")
                    if "Permission denied" in str(e):
                        logger.warning(
                            f"Skipping file {file_path} due to permission issues"
                        )
                        continue
                    raise
                except Exception as e:
                    logger.error(f"Unexpected error processing file {file_path}: {e}")
                    continue

            # Check for failures
            for ratchet in self.ratchets:
                all_failures.extend(ratchet.failures)

            if all_failures and self.fail_on_violations:
                logger.error(f"Found {len(all_failures)} ratchet violations")
                return False

            return True

        except Exception as e:
            logger.error(f"Failed to run ratchet checks: {e}")
            raise


def run_ci_checks():
    """Example function to run CI checks."""
    from .basic_ratchets import get_basic_ratchets
    from .custom_ratchets import get_custom_ratchets

    # Get all ratchets
    ratchets = get_basic_ratchets() + get_custom_ratchets()

    # Create CI runner
    runner = CIRatchetRunner(
        ratchets=ratchets, base_branch="main", fail_on_violations=True
    )

    # Run checks
    success = runner.run()
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    run_ci_checks()
