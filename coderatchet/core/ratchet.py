"""
Core ratchet test classes and functionality.
"""

import ast
import re
from pathlib import Path
from typing import Callable, List, Optional, Pattern, Tuple, TypeVar, Union

import attr
from coderatchet.core.errors import ConfigError
from loguru import logger

from .utils import RatchetError, load_ratchet_count

_NEVER_MATCHING_REGEX: re.Pattern = re.compile("(?!)")
T = TypeVar("T", bound="RatchetTest")


@attr.s(frozen=True, auto_attribs=True)
class TestFailure:
    """A failure of a ratchet test."""

    test_name: str
    filepath: str
    line_number: int
    line_contents: str
    commit_hash: Optional[str] = None
    commit_message: Optional[str] = None
    commit_author: Optional[str] = None
    commit_date: Optional[str] = None

    def __str__(self) -> str:
        """Get a string representation of the failure."""
        return f"{self.filepath}:{self.line_number}: {self.line_contents}"

    @classmethod
    def from_failure(cls, failure: "TestFailure", **kwargs) -> "TestFailure":
        """Create a new TestFailure from an existing one with optional overrides.

        Args:
            failure: The existing failure to copy
            **kwargs: Optional attributes to override

        Returns:
            New TestFailure instance
        """
        return cls(
            test_name=kwargs.get("test_name", failure.test_name),
            filepath=kwargs.get("filepath", failure.filepath),
            line_number=kwargs.get("line_number", failure.line_number),
            line_contents=kwargs.get("line_contents", failure.line_contents),
            commit_hash=kwargs.get("commit_hash", failure.commit_hash),
            commit_date=kwargs.get("commit_date", failure.commit_date),
            commit_message=kwargs.get("commit_message", failure.commit_message),
        )


@attr.s(frozen=True, auto_attribs=True)
class RatchetTest:
    """Base class for all ratchet tests."""

    name: str = attr.ib(kw_only=True)
    allowed_count: int = attr.ib(kw_only=True)
    exclude_test_files: bool = attr.ib(default=False, kw_only=True)
    match_examples: Tuple[str, ...] = attr.ib(factory=tuple, kw_only=True)
    non_match_examples: Tuple[str, ...] = attr.ib(factory=tuple, kw_only=True)
    include_file_regex: Optional[Pattern] = attr.ib(
        default=None, hash=False, kw_only=True
    )
    description: str = attr.ib(default="", kw_only=True)
    _failures: Tuple[TestFailure, ...] = attr.ib(factory=tuple, init=False, hash=False)

    @allowed_count.default
    def _get_allowed_count(self) -> int:
        """Get the allowed count from the ratchet values file."""
        return load_ratchet_count(self.name)

    @property
    def failures(self) -> List[TestFailure]:
        """Get the list of failures."""
        return list(self._failures)

    def __attrs_post_init__(self):
        """Initialize mutable state."""
        if self.exclude_test_files:
            object.__setattr__(
                self,
                "include_file_regex",
                re.compile(r"^(?!.*test_.*\.py$).*\.py$"),
            )

    def collect_failures_from_lines(self, lines: List[str], filepath: str) -> None:
        """Collect failures from lines of code.

        Args:
            lines: Lines of code to check
            filepath: Path to the file being checked
        """
        logger.debug(f"Collecting failures from {filepath}")
        if not self.should_include_file(filepath):
            return

        failures = []
        for i, line in enumerate(lines, 1):
            line = line.rstrip()
            match = self.regex.search(line)
            if match:
                logger.debug(f"Found match in {filepath}:{i}: {line}")
                failures.append(
                    TestFailure(
                        test_name=self.name,
                        filepath=filepath,
                        line_number=i,
                        line_contents=line,
                    )
                )
        object.__setattr__(self, "_failures", tuple(failures))

    def get_total_count_from_files(self, files: List[Path]) -> int:
        """Get total count of violations from files."""
        self.clear_failures()
        for filepath in files:
            if self.should_include_file(filepath):
                self.collect_failures_from_file(filepath)
        return len(self.failures)

    def test_examples(self) -> None:
        """Test that the examples match or don't match as expected."""
        if not hasattr(self, "regex"):
            return  # Skip if the test doesn't use regex patterns

        # Validate match examples
        for example in self.match_examples:
            if not self.regex.search(example):
                raise RatchetError(
                    f"Match example '{example}' does not match pattern '{self.pattern}'"
                )

        # Validate non-match examples
        for example in self.non_match_examples:
            if self.regex.search(example):
                raise RatchetError(
                    f"Non-match example '{example}' matches pattern '{self.pattern}'"
                )

    def add_failure(self, failure: TestFailure) -> None:
        """Add a failure to the list of failures."""
        object.__setattr__(self, "_failures", self._failures + (failure,))

    def clear_failures(self) -> None:
        """Clear the list of failures."""
        object.__setattr__(self, "_failures", tuple())

    def should_include_file(self, filepath: Path) -> bool:
        """Determine if a file should be included in the test."""
        filepath_str = str(filepath)
        logger.debug(f"Checking file inclusion for {filepath_str}")
        if self.exclude_test_files and "test_" in filepath_str:
            logger.debug(f"Excluding {filepath_str} due to test_ pattern")
            return False
        if self.include_file_regex:
            matches = bool(self.include_file_regex.search(filepath_str))
            logger.debug(f"File {filepath_str} matches include pattern: {matches}")
            return matches
        return True

    def collect_failures_from_file(self, filepath: Path) -> None:
        """Collect failures from a file."""
        try:
            with open(filepath) as f:
                lines = f.readlines()
            self.collect_failures_from_lines(lines, str(filepath))
        except (IOError, UnicodeDecodeError) as e:
            logger.warning(f"Failed to read {filepath}: {e}")
            raise RatchetError(f"Failed to read {filepath}: {e}")

    def __hash__(self):
        """Get a hash of the test."""
        return hash(
            (
                self.name,
                self.allowed_count,
                self.exclude_test_files,
                self.match_examples,  # Already a tuple
                self.non_match_examples,  # Already a tuple
                self.description,
            )
        )


@attr.s(frozen=True, auto_attribs=True)
class RegexBasedRatchetTest(RatchetTest):
    """A ratchet test that uses a regex pattern to match lines."""

    pattern: str
    _regex: Pattern = attr.ib(factory=lambda: None, init=False)
    match_examples: Tuple[str, ...] = attr.ib(factory=tuple)
    non_match_examples: Tuple[str, ...] = attr.ib(factory=tuple)
    include_file_regex: Optional[Pattern] = attr.ib(factory=lambda: None, hash=False)

    def __attrs_post_init__(self):
        """Initialize the regex pattern and validate after instance creation."""
        super().__attrs_post_init__()
        try:
            # Validate the pattern immediately
            regex = re.compile(self.pattern)
            # Validate examples
            for example in self.match_examples:
                if not regex.search(example):
                    raise RatchetError(
                        f"Match example '{example}' does not match pattern '{self.pattern}'"
                    )
            for example in self.non_match_examples:
                if regex.search(example):
                    raise RatchetError(
                        f"Non-match example '{example}' matches pattern '{self.pattern}'"
                    )
            object.__setattr__(self, "_regex", regex)
        except re.error as e:
            raise RatchetError(f"Invalid regex pattern '{self.pattern}': {str(e)}")

    @property
    def regex(self) -> Pattern:
        """Get the compiled regex pattern."""
        return self._regex

    def collect_failures_from_lines(self, lines: List[str], filepath: str) -> None:
        """Collect failures from a list of lines.

        Args:
            lines: List of lines to check
            filepath: Path to the file being checked
        """
        logger.debug(f"Collecting failures from {filepath}")
        if not self.should_include_file(filepath):
            return

        failures = []
        for i, line in enumerate(lines, start=1):
            if self.regex.search(line):
                logger.debug(f"Found match in {filepath}:{i}: {line}")
                failures.append(
                    TestFailure(
                        test_name=self.name,
                        filepath=str(filepath),
                        line_number=i,
                        line_contents=line,
                    )
                )
        object.__setattr__(self, "_failures", tuple(failures))

    def collect_failures_from_file(self, filepath: Path) -> None:
        """Collect failures from a file.

        Args:
            filepath: Path to the file to check
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
            self.collect_failures_from_lines(lines, str(filepath))
        except (IOError, UnicodeDecodeError) as e:
            raise RatchetError(f"Failed to read {filepath}: {str(e)}")

    def should_include_file(self, filepath: Union[str, Path]) -> bool:
        """Check if a file should be included in the test.

        Args:
            filepath: Path to the file to check

        Returns:
            True if the file should be included, False otherwise
        """
        logger.debug(f"Checking file inclusion for {filepath}")
        filepath_str = str(filepath)
        if self.exclude_test_files and "test_" in filepath_str:
            logger.debug(f"Excluding {filepath_str} due to test_ pattern")
            return False
        if self.include_file_regex:
            matches = bool(self.include_file_regex.search(filepath_str))
            logger.debug(f"File {filepath_str} matches include pattern: {matches}")
            return matches
        return True

    def clear_failures(self) -> None:
        """Clear the list of failures."""
        object.__setattr__(self, "_failures", tuple())

    @property
    def failures(self) -> List[TestFailure]:
        """Get all failures."""
        return list(self._failures)

    def test_examples(self) -> None:
        """Test that examples match and non-examples don't match."""
        for example in self.match_examples:
            if not self.regex.search(example):
                raise RatchetError(
                    f"Match example '{example}' does not match pattern '{self.pattern}'"
                )
        for example in self.non_match_examples:
            if self.regex.search(example):
                raise RatchetError(
                    f"Non-match example '{example}' matches pattern '{self.pattern}'"
                )


@attr.s(frozen=True)
class TwoLineRatchetTest(RatchetTest):
    """A ratchet test that matches patterns across two consecutive lines."""

    pattern: str = attr.ib(kw_only=True)
    last_line_pattern: str = attr.ib(default=None, kw_only=True)
    _regex: Optional[Pattern] = attr.ib(init=False, default=None, hash=False)
    _last_line_regex: Optional[Pattern] = attr.ib(init=False, default=None, hash=False)
    _last_line: Optional[str] = attr.ib(init=False, default=None, hash=False)
    _last_line_number: Optional[int] = attr.ib(init=False, default=None, hash=False)
    _last_filepath: Optional[str] = attr.ib(init=False, default=None, hash=False)

    @property
    def regex(self) -> Pattern:
        """Get the compiled regex pattern."""
        if self._regex is None:
            object.__setattr__(self, "_regex", re.compile(self.pattern))
        return self._regex

    @property
    def last_line_regex(self) -> Pattern:
        """Get the compiled regex pattern for the last line."""
        if self._last_line_regex is None:
            pattern = (
                self.last_line_pattern if self.last_line_pattern is not None else ".*"
            )
            object.__setattr__(self, "_last_line_regex", re.compile(pattern))
        return self._last_line_regex

    def collect_failures_from_lines(self, lines: List[str], filepath: str) -> None:
        """Collect failures from lines of code."""
        if self.include_file_regex and not self.include_file_regex.search(filepath):
            return

        # Reset state
        last_line = None
        last_line_number = None
        failures = []

        for i, line in enumerate(lines, 1):
            line = line.rstrip()
            if last_line is not None:
                if self.regex.search(last_line) and self.last_line_regex.search(line):
                    failures.append(
                        TestFailure(
                            test_name=self.name,
                            filepath=filepath,
                            line_number=last_line_number,
                            line_contents=f"{last_line}\n{line}",
                        )
                    )
            last_line = line
            last_line_number = i

        # Set failures once at the end
        object.__setattr__(self, "_failures", tuple(failures))

    def get_total_count_from_files(self, files: List[Path]) -> int:
        """Get total count of violations from files."""
        self.clear_failures()
        object.__setattr__(self, "_last_line", None)
        object.__setattr__(self, "_last_line_number", None)
        object.__setattr__(self, "_last_filepath", None)
        return super().get_total_count_from_files(files)


@attr.s(frozen=True, auto_attribs=True)
class FullFileRatchetTest(RegexBasedRatchetTest):
    """A ratchet test that matches against the entire file content."""

    regex_flags: int = 0

    def collect_failures_from_lines(self, lines: List[str], filepath: str) -> None:
        """Collect failures from a list of lines.

        Args:
            lines: List of lines to check
            filepath: Path to the file being checked
        """
        logger.debug(f"Collecting failures from {filepath}")
        if not self.should_include_file(filepath):
            return

        # Join lines into a single string with newlines
        content = "\n".join(lines)

        # Check if the pattern matches
        if self.regex.search(content, self.regex_flags):
            failures = (
                TestFailure(
                    test_name=self.name,
                    filepath=filepath,
                    line_number=1,  # First line since we're matching the whole file
                    line_contents=content,
                ),
            )
            object.__setattr__(self, "_failures", tuple(failures))


def to_second_pass(failure):
    class_name = failure.line_contents.split()[1].rstrip(":")
    return f"self\\.{class_name}\\."


@attr.s(frozen=True, auto_attribs=True)
class TwoPassRatchetTest(RatchetTest):
    """Two-pass ratchet test that uses two regex patterns."""

    first_pass: RegexBasedRatchetTest = attr.ib()
    second_pass_pattern: str = attr.ib()
    match_examples: Tuple[str, ...] = attr.ib(factory=tuple)
    non_match_examples: Tuple[str, ...] = attr.ib(factory=tuple)
    first_pass_failure_to_second_pass_regex_part: Optional[
        Callable[[TestFailure], str]
    ] = attr.ib(default=None)
    first_pass_failure_filepath_for_testing: Optional[str] = attr.ib(default=None)
    _second_pass_regex: Optional[Pattern] = attr.ib(init=False, default=None)
    _failures: Tuple[TestFailure, ...] = attr.ib(init=False, factory=tuple)

    def __attrs_post_init__(self):
        """Initialize after instance creation."""
        # Since we're frozen, we need to use object.__setattr__
        object.__setattr__(
            self, "_second_pass_regex", re.compile(self.second_pass_pattern)
        )

        # Validate examples
        for example in self.match_examples:
            if not self._second_pass_regex.search(example):
                raise RatchetError(
                    f"Match example '{example}' does not match pattern '{self.second_pass_pattern}'"
                )

        for example in self.non_match_examples:
            if self._second_pass_regex.search(example):
                raise RatchetError(
                    f"Non-match example '{example}' matches pattern '{self.second_pass_pattern}'"
                )

        # If we have a function to generate second pass patterns from first pass failures,
        # validate it with the test filepath
        if (
            self.first_pass_failure_to_second_pass_regex_part
            and self.first_pass_failure_filepath_for_testing
        ):
            # Create a test failure
            test_failure = TestFailure(
                test_name=self.first_pass.name,
                filepath=self.first_pass_failure_filepath_for_testing,
                line_number=1,
                line_contents="class MyClass:",
            )
            # Generate the pattern and try to compile it
            try:
                pattern = self.first_pass_failure_to_second_pass_regex_part(
                    test_failure
                )
                re.compile(pattern)
            except (re.error, Exception) as e:
                raise RatchetError(
                    f"Failed to generate or compile second pass pattern: {e}"
                )

    def collect_failures_from_lines(self, lines: List[str], filepath: str) -> None:
        """Collect failures from lines.

        Args:
            lines: Lines to check
            filepath: Path to file being checked
        """
        # First pass: collect failures from first pass test
        self.first_pass.collect_failures_from_lines(lines, filepath)
        first_pass_failures = self.first_pass.failures

        # Second pass: check each line for second pass pattern
        failures = []
        for failure in first_pass_failures:
            # Check all lines after the first pass match for the second pattern
            has_second_pass_match = False
            for i, line in enumerate(lines[failure.line_number :], failure.line_number):
                if self._second_pass_regex.search(line):
                    has_second_pass_match = True
                    break

            if has_second_pass_match:
                failures.append(
                    TestFailure(
                        test_name=self.name,
                        filepath=filepath,
                        line_number=failure.line_number,
                        line_contents=failure.line_contents,
                    )
                )

        # Since we're frozen, we need to use object.__setattr__
        object.__setattr__(self, "_failures", tuple(failures))

    @classmethod
    def from_config(cls, config: "RatchetConfig") -> "TwoPassRatchetTest":
        """Create a TwoPassRatchetTest from a configuration.

        Args:
            config: Configuration to create test from

        Returns:
            TwoPassRatchetTest instance

        Raises:
            ConfigError: If configuration is invalid
        """
        if not config.second_pass_pattern:
            raise ConfigError(
                f"Second pass pattern is required for two-pass ratchet '{config.name}'"
            )

        # Create first pass test
        first_pass = RegexBasedRatchetTest(
            name=f"{config.name}_first_pass",
            pattern=config.pattern,
            match_examples=config.match_examples,
            non_match_examples=config.non_match_examples,
        )

        # Create two-pass test
        return cls(
            name=config.name,
            first_pass=first_pass,
            second_pass_pattern=config.second_pass_pattern,
            match_examples=config.second_pass_examples or tuple(),
            non_match_examples=config.second_pass_non_examples or tuple(),
        )


class PatternManager:
    """Manages regex patterns and their compilation."""

    def __init__(self):
        """Initialize the pattern manager."""
        self._pattern_cache = {}
        self._cache_generation = 0  # Add a generation counter

    def optimize_pattern(self, pattern: str) -> str:
        """Optimize a regex pattern.

        Args:
            pattern: The pattern to optimize

        Returns:
            The optimized pattern
        """
        # For now, just return the pattern as is
        # In the future, we can add pattern optimization logic here
        return pattern

    def get_pattern(self, pattern: str) -> Pattern:
        """Get a compiled pattern.

        Args:
            pattern: The pattern to compile

        Returns:
            The compiled pattern
        """
        # Create a cache key that includes the generation
        cache_key = (pattern, self._cache_generation)

        # Check if we have a cached pattern
        if cache_key not in self._pattern_cache:
            # Optimize and compile the pattern
            optimized = self.optimize_pattern(pattern)
            # Use re.ASCII flag to ensure we get a new pattern instance
            self._pattern_cache[cache_key] = re.compile(
                optimized, re.ASCII if self._cache_generation % 2 else 0
            )
        return self._pattern_cache[cache_key]

    def clear_cache(self) -> None:
        """Clear the pattern cache."""
        self._pattern_cache = {}
        self._cache_generation += 1  # Increment the generation counter


# Create a global pattern manager instance
pattern_manager = PatternManager()


def should_include_file(file_path: str, exclude_test_files: bool = True) -> bool:
    """Check if a file should be included in the analysis.

    Args:
        file_path: Path to the file
        exclude_test_files: Whether to exclude test files

    Returns:
        bool: True if the file should be included
    """
    # Convert Windows paths to Unix style for consistent matching
    file_path = file_path.replace("\\", "/")

    # Exclude test files if specified
    if exclude_test_files and ("test_" in file_path or "/tests/" in file_path):
        logger.debug(f"Excluding {file_path} due to test_ pattern")
        return False

    # Always include files that match the include pattern
    logger.debug(f"File {file_path} matches include pattern: True")
    return True


def collect_failures_from_file(
    filepath: Path, tests: List[RatchetTest]
) -> List[TestFailure]:
    """Collect failures from a file.

    Args:
        filepath: Path to the file
        tests: List of ratchet tests to run

    Returns:
        List of failures found in the file
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        failures = []
        for test in tests:
            # Only check files that should be included
            if not should_include_file(str(filepath), test.exclude_test_files):
                continue

            failures.extend(
                collect_failures_from_lines(str(filepath), content.splitlines(), test)
            )
        return failures
    except (IOError, UnicodeDecodeError) as e:
        logger.warning(f"Failed to read {filepath}: {e}")
        raise RatchetError(f"Failed to read {filepath}: {e}")


def collect_failures_from_lines(
    file_path: str, lines: List[str], test: RatchetTest
) -> List[TestFailure]:
    """Collect failures from a list of lines.

    Args:
        file_path: Path to the file being checked
        lines: List of lines to check
        test: Ratchet test to run

    Returns:
        List of test failures found
    """
    if not test.should_include_file(file_path):
        return []

    failures = []
    for i, line in enumerate(lines, start=1):
        if test.regex.search(line):
            failures.append(
                TestFailure(
                    test_name=test.name,
                    filepath=file_path,
                    line_number=i,
                    line_contents=line.rstrip(),
                )
            )
    return failures


def run_ratchets_on_file(
    filepath: Union[str, Path], tests: List[RatchetTest]
) -> List[TestFailure]:
    """Run ratchet tests on a single file.

    Args:
        filepath: Path to the file to check
        tests: List of ratchet tests to run

    Returns:
        List of test failures found
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise RatchetError(f"File not found: {filepath}")

    failures = []
    for test in tests:
        if test.should_include_file(filepath):
            try:
                test.collect_failures_from_file(filepath)
                failures.extend(test.failures)
            except RatchetError as e:
                logger.error(f"Error running test {test.name} on {filepath}: {e}")
                continue

    return failures
