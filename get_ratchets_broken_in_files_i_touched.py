import argparse
from pathlib import Path
from typing import List
from typing import Sequence

from loguru import logger

from computronium.common.log_utils import configure_stdout_logger
from imbue_core.git import get_git_repo_root
from research.ratchets.get_most_recently_broken_ratchets import date_failures
from research.ratchets.get_most_recently_broken_ratchets import log_matches
from research.ratchets.ratchet_rules import ratchet_test_builders
from research.ratchets.ratchet_utils import RatchetTest
from research.ratchets.ratchet_utils import TestFailure
from research.ratchets.ratchet_utils import get_ratchet_test_files
from science.common.git_utils import generate_changed_files


def get_broken_ratchet_matches(
    files_to_test: Sequence[Path], ratchet_instances: Sequence[RatchetTest]
) -> List[TestFailure]:
    for ratchet in ratchet_instances:
        ratchet.get_total_count_from_files(list(files_to_test))
    return sum([test.failures for test in ratchet_instances], [])


def log_ratchets_broken_in_files_i_touched(
    compared_against: str = "origin/main", displayed_match_count_per_type: int = 10
) -> None:
    changed_files = tuple(Path(filename) for filename in generate_changed_files(compared_against, ("py",), False))
    changed_files = tuple(path.absolute() for path in changed_files if path.exists())
    ratchet_test_files = get_ratchet_test_files(changed_files)

    repo_root = get_git_repo_root()
    for ratchet_builder in ratchet_test_builders:
        ratchet_instance = ratchet_builder()
        failing_test_matches = get_broken_ratchet_matches(ratchet_test_files, [ratchet_instance])
        dated_matches = date_failures(failing_test_matches)
        sorted_dated_matches = sorted(dated_matches, reverse=True)
        total_matches_for_type = len(failing_test_matches)

        if total_matches_for_type == 0:
            logger.info(f"{ratchet_instance.name}: no broken instances in files affected by your changes")
            continue

        log_message = (
            f"\n{ratchet_instance.name}: {total_matches_for_type} broken instances in files affected by your changes"
        )
        if displayed_match_count_per_type < total_matches_for_type:
            log_message += f" (showing {displayed_match_count_per_type} most recent)"
        logger.info(log_message)
        log_matches(sorted_dated_matches[:displayed_match_count_per_type], repo_root)


if __name__ == "__main__":
    repo_root = get_git_repo_root()
    assert Path.cwd() == repo_root, f"You must run this script from the root of the git repo"

    configure_stdout_logger()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--compared_against",
        default="origin/main",
        help="The branch or commit to compare against. Default is origin/main",
    )
    parser.add_argument(
        "--displayed_match_count_per_type",
        type=int,
        default=10,
        help="The number of matches to show for each ratchet type. Default is 10.",
    )
    log_ratchets_broken_in_files_i_touched(**vars(parser.parse_args()))
