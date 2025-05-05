import functools
import json
import os.path
import re
import sys
from abc import ABC
from abc import abstractmethod
from pathlib import Path
from typing import Callable
from typing import Final
from typing import Iterable
from typing import List
from typing import Optional
from typing import Self
from typing import Tuple

import attr
import attrs
from loguru import logger

from imbue_core.common import filter_excluded_files
from imbue_core.git import get_git_repo_root

_NEVER_MATCHING_REGEX: Final = re.compile("(?!)")


def get_python_files(directory: Path) -> List[Path]:
    directory = Path(directory)
    python_files = set([path.absolute() for path in directory.rglob("*.py") if not path.is_symlink()])
    return list(python_files)


@functools.lru_cache(maxsize=1)
def get_ratchet_test_files(source_files: Optional[Tuple[Path]] = None) -> List[Path]:
    repo_root = get_git_repo_root()
    if source_files is None:
        files = get_python_files(repo_root)
    else:
        files = list(source_files)
    files = filter_excluded_files(files, repo_root, ".gitignore")
    files = filter_excluded_files(files, repo_root, "ratchet_excluded.txt")
    # ignore files that come from other repositories, since it's a little silly for us to modify their styles
    files = [x for x in files if "/contrib/" not in str(x.absolute())]
    return files


def ratchet_values_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "ratchet_values.json")


@functools.lru_cache(maxsize=1)
def get_ratchet_values() -> dict[str, int]:
    with open(ratchet_values_path()) as f:
        ratchet_values = dict(json.load(f))
    return ratchet_values


def load_ratchet_count(test_name: str) -> int:
    ratchet_values = get_ratchet_values()
    return ratchet_values.get(test_name, 0)


def write_ratchet_counts(counts_by_ratchet: dict) -> None:
    with open(ratchet_values_path(), "w") as f:
        json.dump(counts_by_ratchet, f, indent=4)
        f.write("\n")
    get_ratchet_values.cache_clear()


def file_path_to_module_path(file_path: str) -> str:
    prefix = max([x for x in sys.path if file_path.startswith(x)], default="", key=len)
    if prefix == "" and file_path.startswith("/") and "/standalone/" in file_path:
        # HACK: correctly resolve paths in standalone projects even if they're not in sys.path.
        # (As is the case in core_fast_tests.)
        expected_path = file_path.split("/standalone/", 1)[1].split("/", 1)[1]
        prefix = file_path.removesuffix(expected_path)

    return file_path.removeprefix(prefix).replace("/", ".").removeprefix(".").removesuffix(".py")


@attr.s(auto_attribs=True)
class TestFailure:
    test_name: str
    filepath: str
    line_number: int
    line_contents: str

    # Make pytest not think this is a test
    __test__ = False

    def __str__(self) -> str:
        return f"{self.filepath}:{self.line_number}: {self.line_contents}"


@attr.s(auto_attribs=True)
class RatchetTest(ABC):
    """A ratchet test ensures that we don't add any new occurrences of some matched pattern to our codebase,
    but doesn't require us to migrate all existing cases"""

    name: str
    allowed_count: int = 0
    exclude_test_files: bool = False
    match_examples: List[str] = attr.Factory(list)
    non_match_examples: List[str] = attr.Factory(list)
    failures: List[TestFailure] = attr.Factory(list)
    include_file_regex: Optional[re.Pattern] = attrs.field(kw_only=True, default=None)

    def set_allowed_count(self, count: int) -> None:
        self.allowed_count = count

    def compare_with(self, other: "RatchetTest") -> "RatchetTest":
        """For troubleshooting/validating ratchet rule changes. To see differences just:
        1. append `.compare_with=RatchetTest('updated', re.compile(...))`
        2. run `python -m research.ratchets.test_all_ratchets update`

        The resulting `_TempComparisonRatchetTest` will report any lines that are unique to either ratchet without effecting other behavior.
        """
        return _TempComparisonRatchetTest.build_from(self, other)

    @abstractmethod
    def collect_failures_from_lines(self, lines: List[str], filepath: str = "") -> None:
        """Appends to failures based on any matched patterns within the lines."""

    def collect_failures_from_file(self, filepath: Path) -> None:
        with open(filepath, "r") as file:
            code = file.read()
            lines = code.split("\n")
            self.collect_failures_from_lines(lines, str(filepath))

    def get_total_count_from_files(self, files_to_evaluate: List[Path]) -> int:
        self.failures = []
        if self.exclude_test_files:
            # https://docs.pytest.org/en/7.1.x/explanation/goodpractices.html#test-discovery
            # We're not catching files under `tests/` here (without an _test_ pre/suffix), which exist a few places.
            # This is intentional - refactor those to match the test discovery conventions documented at the above link.
            test_file_re = re.compile(r"(test_[^\\/]*\.py)|(.*_test.py)")
            files_to_evaluate = [file for file in files_to_evaluate if test_file_re.search(str(file)) is None]

        if self.include_file_regex is not None:
            files_to_evaluate = [
                file for file in files_to_evaluate if self.include_file_regex.search(str(file)) is not None
            ]

        for file in files_to_evaluate:
            self.collect_failures_from_file(file)
        return len(self.failures)

    def test(self) -> None:
        files = get_ratchet_test_files()
        actual_offenses = self.get_total_count_from_files(files)

        msg = f"{self.name} offenses: {actual_offenses}"
        if actual_offenses < self.allowed_count:
            logger.success(msg)
        elif actual_offenses == self.allowed_count:
            logger.info(msg)
        else:
            logger.error(msg)

        assert (
            actual_offenses <= self.allowed_count
        ), f"The number of actual offenses for {self.name} was {actual_offenses}, greater than the allowed offenses {self.allowed_count}"

    def test_examples(self) -> List[TestFailure]:
        # Although we don't use multiline examples for base ratchets, we do for subclasses so it's worth splitting
        match_failures = []
        for case in self.match_examples:
            self.collect_failures_from_lines(case.split("\n"))
            assert len(self.failures) == 1, (self.name, case, self.failures)
            match_failures.append(self.failures[0])
            self.failures = []

        for case in self.non_match_examples:
            self.collect_failures_from_lines(case.split("\n"))
            assert len(self.failures) == 0, (self.name, case, self.failures)

        return match_failures


@attr.s(auto_attribs=True)
class RegexBasedRatchetTest(RatchetTest):
    """A ratchet test that uses defines match patterns via regexes."""

    regex: re.Pattern = attrs.field(kw_only=True)

    def collect_failures_from_lines(self, lines: List[str], filepath: str = "") -> None:
        for i, line in enumerate(lines):
            if self.regex.search(line):
                self.failures.append(
                    TestFailure(test_name=self.name, filepath=filepath, line_number=i + 1, line_contents=line)
                )

    def __str__(self) -> str:
        return f"{self.name} ({self.regex})"


@attr.s(auto_attribs=True)
class TwoLineRatchetTest(RegexBasedRatchetTest):
    """A Ratchet test that has to match the specified regex and not match the previous line to mark an offence"""

    last_line_regex: Optional[re.Pattern] = None

    def collect_failures_from_lines(self, lines: List[str], filepath: str = "") -> None:
        for i, line in enumerate(lines):
            if self.regex.search(line):
                if self.last_line_regex is not None:
                    first_line = i == 0
                    if first_line or self.last_line_regex.search(lines[i - 1]) is None:
                        self.failures.append(
                            TestFailure(test_name=self.name, filepath=filepath, line_number=i + 1, line_contents=line)
                        )


@attr.s(auto_attribs=True)
class FullFileRatchetTest(RegexBasedRatchetTest):
    """A ratchet test that operates on the whole file at once and then back-calculates what line each breakage is coming
    from. If possible, prefer line-by-line ratchets for simpler regexes."""

    def collect_failures_from_lines(self, lines: List[str], filepath: str = "") -> None:
        file = "\n".join(lines)
        for match in self.regex.finditer(file):
            line_number = file.count("\n", 0, match.start())
            self.failures.append(
                TestFailure(
                    test_name=self.name,
                    filepath=filepath,
                    line_number=line_number + 1,
                    line_contents=lines[line_number],
                )
            )


def make_regex_part_matching_import_from_failure(failure: TestFailure) -> str:
    module_path = file_path_to_module_path(failure.filepath)
    parts = [f"import {module_path}", f"from {module_path} import"]
    as_modname_import = module_path.rsplit(".", maxsplit=1)
    if len(as_modname_import) == 2:
        from_parent, modname = as_modname_import
        parts.append(f"from {from_parent} import {modname}")
    return f"^({'|'.join(parts)})"


def _regex_join_with_or(regex_parts: Iterable[str]) -> re.Pattern:
    expression = "|".join(f"({p})" for p in regex_parts)
    if expression == "":
        return _NEVER_MATCHING_REGEX
    return re.compile(expression)


@attr.s(auto_attribs=True)
class TwoPassRatchetTest(RegexBasedRatchetTest):
    """
    A ratchet test that runs in two passes.

        - In the first pass, we assemble the actual regex to run against the individual files.
        - In the second pass, we use the regex to run the test as a normal ratchet test.

    In this way, we can reflect on code relationships that span multiple files.

    """

    first_pass: RegexBasedRatchetTest = attrs.field(kw_only=True)
    first_pass_failure_to_second_pass_regex_part: Callable[[TestFailure], str] = attrs.field(kw_only=True)
    first_pass_failure_filepath_for_testing: str = attrs.field(kw_only=True)
    regex: re.Pattern = _NEVER_MATCHING_REGEX

    def _collect_first_pass_failures(self, files_to_evaluate: List[Path]) -> List[TestFailure]:
        self.first_pass.get_total_count_from_files(files_to_evaluate)
        return self.first_pass.failures

    def build_second_pass_regex(self, failures: List[TestFailure]) -> re.Pattern:
        return _regex_join_with_or(self.first_pass_failure_to_second_pass_regex_part(failure) for failure in failures)

    def get_total_count_from_files(self, files_to_evaluate: List[Path]) -> int:
        self.regex = self.build_second_pass_regex(self._collect_first_pass_failures(files_to_evaluate))
        if self.regex == _NEVER_MATCHING_REGEX:
            return 0
        return super().get_total_count_from_files(files_to_evaluate)

    def test_examples(self) -> List[TestFailure]:
        if len(self.match_examples) + len(self.non_match_examples) == 0:
            return []
        first_pass_sample_match_failures = self.first_pass.test_examples()
        assert (
            len(first_pass_sample_match_failures) > 0
        ), f"must have a first_pass failure example for {self.name} to test the second pass"
        for failure in first_pass_sample_match_failures:
            failure.filepath = self.first_pass_failure_filepath_for_testing
        self.regex = self.build_second_pass_regex(first_pass_sample_match_failures)
        return super().test_examples()


@attr.s(auto_attribs=True)
class _TempComparisonRatchetTest(RatchetTest):
    """For troubleshooting/validating ratchet rule changes. See RatchetTest.compare_with"""

    # Behaves according to the base_ratchet
    base_ratchet: RatchetTest = attrs.field(kw_only=True)
    compare_with_ratchet: RatchetTest = attrs.field(kw_only=True)

    @classmethod
    def build_from(cls, base: RatchetTest, compare_with: RatchetTest) -> Self:
        return cls(
            name=base.name,
            allowed_count=base.allowed_count,
            exclude_test_files=base.exclude_test_files,
            match_examples=base.match_examples,
            non_match_examples=base.non_match_examples,
            failures=base.failures,
            base_ratchet=base,
            compare_with_ratchet=compare_with,
        )

    @staticmethod
    def _report_comparison(current_ratchet: RatchetTest, compare_with_ratchet: RatchetTest) -> None:
        current_failures = set(str(f) for f in current_ratchet.failures)
        compare_with_failures = set(str(f) for f in compare_with_ratchet.failures)

        logger.info(f"Failures unique to {str(current_ratchet)}:")
        for unique_to_current in current_failures - compare_with_failures:
            logger.info(unique_to_current)

        logger.info(f"Failures unique to {str(compare_with_ratchet)}:")
        for unique_to_other in compare_with_failures - current_failures:
            logger.info(unique_to_other)

    def collect_failures_from_lines(self, lines: List[str], filepath: str = "") -> None:
        self.base_ratchet.collect_failures_from_lines(lines, filepath)
        self.compare_with_ratchet.collect_failures_from_lines(lines, filepath)
        # Even though build_from uses the same list at construction time, need
        # to grab the failures over, in case we get deepcopy'ed.
        self.failures = self.base_ratchet.failures

    def get_total_count_from_files(self, files_to_evaluate: List[Path]) -> int:
        failure_count = super().get_total_count_from_files(files_to_evaluate)
        self._report_comparison(self.base_ratchet, self.compare_with_ratchet)
        return failure_count
