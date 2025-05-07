"""
Utility functions and classes for CodeRatchet.
"""

import json
import os
import os.path
import re
from fnmatch import fnmatch
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Union

import attr
from loguru import logger


class RatchetError(Exception):
    """Base exception for ratchet-related errors."""

    pass


class PatternManager:
    """Manages regex patterns for ratchet tests."""

    def __init__(self):
        """Initialize the pattern manager."""
        self._pattern_cache = {}
        self._cache_generation = 0

    def join_patterns(self, patterns: List[str], escape: bool = True) -> re.Pattern:
        """Join regex patterns with OR operator.

        Args:
            patterns: List of regex patterns to join
            escape: Whether to escape the patterns (default: True)

        Returns:
            Compiled regex pattern
        """
        if not patterns:
            return re.compile("(?!)")  # Never matches

        if len(patterns) == 1:
            pattern = patterns[0]
            return re.compile(f"(?:{pattern})")

        return re.compile("|".join(f"(?:{p})" for p in patterns))

    def get_pattern(self, pattern: str, escape: bool = True) -> re.Pattern:
        """Get a compiled pattern.

        Args:
            pattern: The pattern to compile
            escape: Whether to escape the pattern (default: True)

        Returns:
            The compiled pattern
        """
        cache_key = (pattern, escape, self._cache_generation)

        if cache_key not in self._pattern_cache:
            optimized = self.optimize_pattern(pattern)
            self._pattern_cache[cache_key] = re.compile(
                re.escape(optimized) if escape else optimized,
                re.ASCII if self._cache_generation % 2 else 0,
            )
        return self._pattern_cache[cache_key]

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

    def clear_cache(self) -> None:
        """Clear the pattern cache."""
        self._pattern_cache = {}
        self._cache_generation += 1


# Create a global pattern manager instance
pattern_manager = PatternManager()

# Default patterns to exclude from ratchet tests
DEFAULT_EXCLUDE_PATTERNS = [
    "*.pyc",
    "__pycache__/",
    "venv/",
    "*.egg-info/",
    "build/",
    "dist/",
    ".git/",
    ".tox/",
    ".pytest_cache/",
    ".mypy_cache/",
    ".coverage",
    "htmlcov/",
    "*.so",
    "*.pyd",
    "*.dll",
    "*.dylib",
]


def get_python_files(
    directory: Path, return_set: bool = False
) -> Union[List[Path], Set[Path]]:
    """Get all Python files in the given directory.

    Args:
        directory: The directory to search for Python files
        return_set: If True, return a set of paths. If False, return a sorted list.

    Returns:
        List or Set of absolute paths to Python files
    """
    directory = Path(directory)
    files = set()
    try:
        # Use rglob to find all Python files recursively
        for file_path in directory.rglob("*.py"):
            # Skip symlinks and non-files
            if not file_path.is_file() or file_path.is_symlink():
                continue
            # Convert to absolute path and normalize
            abs_path = file_path.absolute()
            # Add to set
            files.add(abs_path)
    except (PermissionError, OSError) as e:
        logger.warning(f"Error accessing {directory}: {e}")

    return files if return_set else sorted(list(files))


def _read_exclude_patterns(
    filepath: Union[str, Path], base_dir: Optional[Path] = None
) -> List[str]:
    """Read exclusion patterns from a file.

    Args:
        filepath: Path to the file containing exclusion patterns
        base_dir: Optional base directory to make patterns relative to

    Returns:
        List of exclusion patterns
    """
    filepath = Path(filepath)
    if not filepath.exists():
        return []

    patterns = []
    with open(filepath) as f:
        for line in f:
            # Remove leading and trailing whitespace
            line = line.strip()
            if line and not line.startswith("#"):
                # Remove leading and trailing quotes (both single and double)
                line = line.strip("\"'")
                # If base_dir is provided and pattern is not a glob pattern,
                # make it relative to base_dir
                if base_dir and not any(c in line for c in "*?["):
                    line = str(
                        Path(line).relative_to(base_dir)
                        if Path(line).is_absolute()
                        else line
                    )
                patterns.append(line)
    return patterns


def should_exclude_file(filepath: str, exclusion_patterns: List[str]) -> bool:
    """Check if a file should be excluded based on patterns.

    Args:
        filepath: The path to the file to check
        exclusion_patterns: List of glob patterns for files to exclude

    Returns:
        True if the file should be excluded, False otherwise
    """
    # Convert filepath to string and normalize it (convert Windows paths to Unix style)
    filepath = str(Path(filepath)).replace("\\", "/")
    filename = Path(filepath).name

    # First check directory patterns (they take precedence)
    for pattern in exclusion_patterns:
        if not pattern.startswith("!") and pattern.endswith("/"):
            dir_pattern = pattern.rstrip("/")
            # Check if any part of the path matches the directory pattern
            path_parts = filepath.split("/")
            for part in path_parts:
                if fnmatch(part, dir_pattern):
                    return True

    # Then check if the file matches any negation pattern
    for pattern in exclusion_patterns:
        if pattern.startswith("!"):
            pattern_without_negation = pattern[1:]
            # Only match filename against negation pattern if it's in the root directory
            # or if the pattern contains a path separator
            if "/" in pattern_without_negation:
                if fnmatch(filepath, pattern_without_negation):
                    return False
            elif fnmatch(filename, pattern_without_negation):
                return False

    # Finally check other exclusion patterns
    for pattern in exclusion_patterns:
        if not pattern.startswith("!") and not pattern.endswith(
            "/"
        ):  # Skip negation and directory patterns
            # Match against full path if pattern contains a path separator
            if "/" in pattern:
                if fnmatch(filepath, pattern):
                    return True
            # Match against filename only if pattern doesn't contain a path separator
            elif fnmatch(filename, pattern):
                return True

    return False


def get_ratchet_test_files(additional_dirs: Optional[List[Path]] = None) -> List[Path]:
    """Get all Python files that should be tested, applying exclusion patterns.

    Args:
        additional_dirs: Optional list of additional directories to search. If provided,
                       only these directories will be searched. Otherwise, the current
                       directory will be searched.

    Returns:
        List of Path objects for Python files to test
    """
    # Get exclusion patterns
    exclusion_patterns = _get_exclusion_patterns(additional_dirs)
    logger.debug(f"Exclusion patterns: {exclusion_patterns}")

    # Get files to check
    files = set()
    if additional_dirs:
        for directory in additional_dirs:
            logger.debug(f"Searching in additional directory: {directory}")
            try:
                files.update(get_python_files(directory, return_set=True))
            except Exception as e:
                logger.warning(f"Error searching directory {directory}: {e}")
    else:
        current_dir = Path.cwd()
        logger.debug(f"Searching in current directory: {current_dir}")
        try:
            files.update(get_python_files(current_dir, return_set=True))
        except Exception as e:
            logger.warning(f"Error searching current directory: {e}")

    logger.debug(f"Found files before filtering: {files}")

    # Filter out excluded files
    filtered_files = []
    for file_path in files:
        try:
            # Convert to relative path for pattern matching
            rel_path = (
                file_path.relative_to(Path.cwd()) if not additional_dirs else file_path
            )
            should_exclude = should_exclude_file(str(rel_path), exclusion_patterns)
            logger.debug(f"Checking {file_path}, should_exclude={should_exclude}")
            if not should_exclude:
                filtered_files.append(file_path)
        except ValueError:
            # If relative_to fails, use absolute path
            should_exclude = should_exclude_file(str(file_path), exclusion_patterns)
            logger.debug(f"Checking {file_path}, should_exclude={should_exclude}")
            if not should_exclude:
                filtered_files.append(file_path)

    logger.debug(f"Files after filtering: {filtered_files}")
    return sorted(filtered_files)


def _get_exclusion_patterns(additional_dirs: Optional[List[Path]] = None) -> List[str]:
    """Get exclusion patterns from default list and ratchet_excluded.txt.

    Args:
        additional_dirs: Optional list of additional directories to search

    Returns:
        List of exclusion patterns
    """
    # Start with an empty list
    exclusion_patterns = []

    # Try to read custom exclusion patterns from ratchet_excluded.txt
    try:
        # First try the current directory
        exclude_file = Path.cwd() / "ratchet_excluded.txt"
        if not exclude_file.exists() and additional_dirs:
            # If not found and additional_dirs is provided, try those directories
            for directory in additional_dirs:
                exclude_file = directory / "ratchet_excluded.txt"
                if exclude_file.exists():
                    break

        if exclude_file.exists():
            exclusion_patterns.extend(_read_exclude_patterns(exclude_file))
    except Exception as e:
        logger.warning(f"Failed to read ratchet_excluded.txt: {e}")

    # Add default patterns after custom patterns
    exclusion_patterns.extend(DEFAULT_EXCLUDE_PATTERNS)

    return exclusion_patterns


def ratchet_values_path() -> str:
    """Get the path to the ratchet values file.

    Returns:
        Absolute path to the ratchet values file
    """
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "ratchet_values.json"
    )


def get_ratchet_values() -> Dict[str, int]:
    """Get the current ratchet values.

    Returns:
        Dictionary mapping ratchet test names to their allowed violation counts
    """
    values_path = ratchet_values_path()
    if not os.path.exists(values_path):
        return {}
    try:
        with open(values_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def load_ratchet_count(test_name: str) -> int:
    """Load the allowed count for a ratchet test.

    Args:
        test_name: Name of the ratchet test

    Returns:
        The allowed violation count for the test
    """
    return get_ratchet_values().get(test_name, 0)


def write_ratchet_counts(counts_by_ratchet: Dict[str, int]) -> None:
    """Write the ratchet counts to the values file.

    Args:
        counts_by_ratchet: Dictionary mapping ratchet test names to their allowed violation counts
    """
    values_path = ratchet_values_path()
    os.makedirs(os.path.dirname(values_path), exist_ok=True)
    with open(values_path, "w") as f:
        json.dump(counts_by_ratchet, f, indent=2)


def file_path_to_module_path(filepath: str) -> str:
    """Convert a file path to a module path.

    Args:
        filepath: Path to convert

    Returns:
        Module path string
    """
    # Normalize path separators
    normalized = filepath.replace("\\", "/")

    # Remove leading slashes and drive letters
    if normalized.startswith("/"):
        normalized = normalized[1:]
    if normalized.startswith("C:/") or normalized.startswith("D:/"):
        normalized = normalized[3:]

    # Remove .py extension and convert to module path
    if normalized.endswith(".py"):
        normalized = normalized[:-3]
    elif normalized.endswith(".txt"):
        normalized = normalized[:-4]
    return normalized.replace("/", ".")


@attr.s(auto_attribs=True)
class TestFailure:
    """A test failure.

    Attributes:
        test_name: Name of the test that failed
        filepath: Path to the file where the failure occurred
        line_number: Line number where the failure occurred
        line_contents: Contents of the line that caused the failure
    """

    test_name: str
    filepath: str
    line_number: int
    line_contents: str

    # Make pytest not think this is a test
    __test__ = False

    def __str__(self) -> str:
        """Return a string representation of the test failure.

        Returns:
            String in the format "filepath:line_number: line_contents"
        """
        return f"{self.filepath}:{self.line_number}: {self.line_contents}"


def _regex_join_with_or(regex_parts: Iterable[str]) -> re.Pattern:
    """Join regex parts with OR operator.

    Args:
        regex_parts: Iterable of regex patterns to join

    Returns:
        Compiled regex pattern
    """
    if not regex_parts:
        return re.compile("(?!)")  # Never match anything
    return re.compile("|".join(f"({part})" for part in regex_parts))


def join_regex_patterns(patterns: List[str], escape: bool = True) -> re.Pattern:
    """Join regex patterns with OR operator.

    Args:
        patterns: List of regex patterns to join
        escape: Whether to escape the patterns (default: True)

    Returns:
        Compiled regex pattern
    """
    return pattern_manager.join_patterns(patterns, escape)
