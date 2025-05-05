import argparse
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import List
from typing import Optional
from typing import Sequence
from typing import Tuple
from typing import cast

from loguru import logger
from pygments import highlight
from pygments.formatters import TerminalFormatter
from pygments.lexers import PythonLexer

from imbue_core.git import get_git_repo_root
from research.ratchets.ratchet_rules import ratchet_test_builders
from research.ratchets.ratchet_utils import RatchetTest
from research.ratchets.ratchet_utils import TestFailure
from research.ratchets.ratchet_utils import get_ratchet_test_files
from research.ratchets.ratchet_utils import load_ratchet_count


def format_python_code_for_log(code: str) -> str:
    return cast(str, highlight(code, PythonLexer(), TerminalFormatter()))


def get_time_from_blame_output(output: str) -> int:
    commit_info = [entry.split(" ", maxsplit=1) for entry in output.split("\n") if entry != ""]
    for key, val in commit_info:
        if key == "committer-time":
            return int(val)
    # no committer time means it is uncommitted changes - set the time to now
    return int(time.time())


def log_matches(matches: Sequence[Tuple[int, TestFailure]], repo_root: Path) -> None:
    for git_time, failure in matches:
        # Note: This won't quite highlight correctly in pycharm due to a bug https://youtrack.jetbrains.com/issue/PY-46305
        logger.info(
            rf'{failure.test_name} matched File "{os.path.relpath(failure.filepath, repo_root)}:{failure.line_number}" as of {datetime.fromtimestamp(git_time)}'
        )
        logger.info(format_python_code_for_log(failure.line_contents))
        logger.info("")


def get_ratchet_test_failure_matches(
    files_to_test: Sequence[Path], ratchet_instances: Sequence[RatchetTest]
) -> List[TestFailure]:
    for ratchet in ratchet_instances:
        ratchet.get_total_count_from_files(list(files_to_test))
        ratchet_value = load_ratchet_count(ratchet.name)
        ratchet.set_allowed_count(ratchet_value)

    test_failure_match_lists = [test.failures for test in ratchet_instances if len(test.failures) > test.allowed_count]
    failing_test_matches = [match for match_list in test_failure_match_lists for match in match_list]
    return failing_test_matches


def date_failures(failures: Sequence[TestFailure]) -> Tuple[Tuple[int, TestFailure], ...]:
    dated_failures = []
    for failure in failures:
        # Tried using the git packages here and blame_iter but that doesn't have an option to limit lines and is slow
        # Now shelling out so that we can actually add the -L specifier and get the data for just the relevant line
        # for running on all existing failures, this takes 25s,
        # but is faster with the filtering for only too many failures done above.
        blame_line = subprocess.run(
            ["git", "blame", os.path.abspath(failure.filepath), "-L", rf"{failure.line_number},+1", "--incremental"],
            capture_output=True,
            text=True,
        )
        dated_failures.append((get_time_from_blame_output(blame_line.stdout), failure))
    return tuple(dated_failures)


def log_recently_broken_ratchets(
    specific_ratchet_types: Optional[Tuple[str, ...]] = None, num_matches_to_show: int = 10
) -> None:
    repo_root = get_git_repo_root()
    ratchet_instances = [builder() for builder in ratchet_test_builders]
    if specific_ratchet_types is not None:
        ratchet_instances = [ratchet for ratchet in ratchet_instances if ratchet.name in specific_ratchet_types]

    failing_test_matches = get_ratchet_test_failure_matches(get_ratchet_test_files(), ratchet_instances)
    # If there are some failing tests, we can accurately guess that the user wants to see the matches for just those
    # failing tests in order to fix them. If there are no failing tests, it doesn't make much sense to show no
    # results, so instead we'll put a note and then list all matches.
    if failing_test_matches:
        matches_to_blame = failing_test_matches
    else:
        logger.info(
            "There were no ratchet tests which had more matches than allowed. Running over all ratchet tests instead, which may be slower"
        )
        matches_to_blame = [failure for test in ratchet_instances for failure in test.failures]

    dated_matches = date_failures(matches_to_blame)
    sorted_dated_matches = sorted(dated_matches, reverse=True)
    log_matches(sorted_dated_matches[:num_matches_to_show], repo_root)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--specific_ratchet_types", nargs="*", help="If specified, only show matches for these ratchet types"
    )
    parser.add_argument(
        "--num_matches_to_show",
        type=int,
        default=10,
        help="The number of matches to show for each ratchet type. Default is 10.",
    )
    log_recently_broken_ratchets(**vars(parser.parse_args()))
