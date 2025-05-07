"""
Functionality for comparing ratchet values between different states.
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import attr
from loguru import logger

from .ratchet import RatchetTest
from .utils import load_ratchet_count


@dataclass
class RatchetComparison:
    """Comparison results for a ratchet test."""

    test_name: str
    current_count: int
    previous_count: int
    difference: int
    percentage_change: float
    is_worse: bool


def compare_ratchets(
    previous_state: str,
    current_state: str = "HEAD",
    include_commits: bool = False,
) -> List[RatchetComparison]:
    """Compare ratchet values between two states.

    Args:
        previous_state: Git reference for the previous state (commit, branch, etc.)
        current_state: Git reference for the current state
        include_commits: Whether to include commit information in the comparison

    Returns:
        List of ratchet comparisons, sorted by severity of change
    """
    # Get ratchet tests
    from .config import get_ratchet_tests

    tests = get_ratchet_tests()

    # Get counts for both states
    with _checkout_state(previous_state):
        previous_counts = _get_ratchet_counts(tests)

    with _checkout_state(current_state):
        current_counts = _get_ratchet_counts(tests)

    # Compare counts
    comparisons = []
    for test in tests:
        current = current_counts.get(test.name, 0)
        previous = previous_counts.get(test.name, 0)
        diff = current - previous
        # Handle special case where both counts are 0
        if current == 0 and previous == 0:
            percent = 0.0
        else:
            percent = (diff / previous * 100) if previous > 0 else float("inf")

        comparisons.append(
            RatchetComparison(
                test_name=test.name,
                current_count=current,
                previous_count=previous,
                difference=diff,
                percentage_change=percent,
                is_worse=diff > 0,
            )
        )

    # Sort by severity (largest positive changes first)
    comparisons.sort(key=lambda x: (-x.difference, x.test_name))
    return comparisons


def _get_ratchet_counts(tests: List[RatchetTest]) -> Dict[str, int]:
    """Get current ratchet counts for all tests."""
    counts = {}
    for test in tests:
        try:
            counts[test.name] = load_ratchet_count(test.name)
        except Exception as e:
            logger.warning(f"Failed to load count for {test.name}: {e}")
            counts[test.name] = 0
    return counts


def _get_ratchet_tests() -> List[RatchetTest]:
    """Get all ratchet tests to check."""
    from .config import create_ratchet_tests, load_ratchet_configs

    configs = load_ratchet_configs()
    return create_ratchet_tests(configs)


class _checkout_state:
    """Context manager for checking out a git state."""

    def __init__(self, state: str):
        self.state = state
        self.stashed = False

    def __enter__(self):
        try:
            # Try to stash local changes
            subprocess.check_call(
                ["git", "stash", "push", "-m", "coderatchet_temp_stash"]
            )
            self.stashed = True
        except subprocess.CalledProcessError:
            # No local changes to stash
            self.stashed = False

        try:
            subprocess.check_call(["git", "checkout", self.state])
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to checkout {self.state}: {e}")
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            subprocess.check_call(["git", "checkout", "-"])
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to restore previous state: {e}")
            raise

        if self.stashed:
            try:
                # Check if there are any stashed changes before trying to pop
                result = subprocess.run(
                    ["git", "stash", "list"], capture_output=True, text=True
                )
                if result.stdout.strip():  # Only pop if there are stashed changes
                    subprocess.check_call(["git", "stash", "pop"])
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to restore stashed changes: {e}")
                raise


@attr.s(frozen=True)
class _TempComparisonRatchetTest(RatchetTest):
    """For troubleshooting/validating ratchet rule changes. See RatchetTest.compare_with"""

    base_ratchet: RatchetTest = attr.ib(kw_only=True)
    compare_with_ratchet: RatchetTest = attr.ib(kw_only=True)

    @classmethod
    def build_from(
        cls, base: RatchetTest, compare_with: RatchetTest
    ) -> "_TempComparisonRatchetTest":
        return cls(
            name=base.name,
            allowed_count=base.allowed_count,
            exclude_test_files=base.exclude_test_files,
            match_examples=base.match_examples,
            non_match_examples=base.non_match_examples,
            base_ratchet=base,
            compare_with_ratchet=compare_with,
        )

    def collect_failures_from_lines(self, lines: List[str], filepath: str = "") -> None:
        object.__setattr__(
            self.base_ratchet, "_failures", []
        )  # Clear any existing failures
        object.__setattr__(
            self.compare_with_ratchet, "_failures", []
        )  # Clear any existing failures

        self.base_ratchet.collect_failures_from_lines(lines, filepath)
        self.compare_with_ratchet.collect_failures_from_lines(lines, filepath)
        object.__setattr__(self, "_failures", self.base_ratchet.failures)

    def get_total_count_from_files(self, files_to_evaluate: List[Path]) -> int:
        object.__setattr__(
            self.base_ratchet, "_failures", []
        )  # Clear any existing failures
        object.__setattr__(
            self.compare_with_ratchet, "_failures", []
        )  # Clear any existing failures

        base_count = self.base_ratchet.get_total_count_from_files(files_to_evaluate)
        compare_count = self.compare_with_ratchet.get_total_count_from_files(
            files_to_evaluate
        )
        # Return the maximum count to ensure we catch all potential violations
        return max(base_count, compare_count)


def compare_ratchet_sets(
    current_ratchets: List[RatchetTest], previous_ratchets: List[RatchetTest]
) -> Tuple[List[RatchetTest], List[RatchetTest], List[Tuple[RatchetTest, RatchetTest]]]:
    """Compare ratchets between two sets.

    Args:
        current_ratchets: List of current ratchet tests
        previous_ratchets: List of previous ratchet tests

    Returns:
        Tuple of (added_ratchets, removed_ratchets, modified_ratchets)
    """
    # Convert to dictionaries for easier comparison
    current_dict = {r.name: r for r in current_ratchets}
    previous_dict = {r.name: r for r in previous_ratchets}

    # Find added, removed, and modified ratchets
    added = [r for name, r in current_dict.items() if name not in previous_dict]
    removed = [r for name, r in previous_dict.items() if name not in current_dict]
    modified = [
        (current_dict[name], previous_dict[name])
        for name in set(current_dict) & set(previous_dict)
        if current_dict[name] != previous_dict[name]
    ]

    return added, removed, modified
