"""Tests ratchet values across the whole repository.

If this test fails, you might find this command useful:
```
python standalone/research/research/ratchets/get_ratchets_broken_in_files_i_touched.py
```

"""
import fire
import pytest

from research.ratchets.ratchet_rules import path_exclude_check
from research.ratchets.ratchet_rules import ratchet_test_builders
from research.ratchets.ratchet_utils import RatchetTest
from research.ratchets.ratchet_utils import get_ratchet_test_files
from research.ratchets.ratchet_utils import load_ratchet_count
from research.ratchets.ratchet_utils import ratchet_values_path
from research.ratchets.ratchet_utils import write_ratchet_counts


@pytest.mark.parametrize(
    "ratchet",
    [pytest.param(instance, id=instance.name) for instance in [builder() for builder in ratchet_test_builders]],
)
def test_all_ratchet_examples(ratchet: RatchetTest) -> None:
    ratchet.test_examples()


def update() -> None:
    """Update the permitted numbers of violations to those in the current codebase."""
    ratchet_counts = dict()
    test_instances = [maker() for maker in ratchet_test_builders]
    for test in test_instances:
        ratchet_counts[test.name] = test.get_total_count_from_files(get_ratchet_test_files())

    # Write to json file, which determines
    write_ratchet_counts(ratchet_counts)
    print(f"Updated ratchet values at: {ratchet_values_path()}")


@pytest.mark.parametrize(
    "ratchet",
    [pytest.param(instance, id=instance.name) for instance in [builder() for builder in ratchet_test_builders]],
)
def test_ratchet(ratchet: RatchetTest) -> None:
    """Run ratchet test against the current codebase."""
    ratchet_value = load_ratchet_count(ratchet.name)
    ratchet.set_allowed_count(ratchet_value)
    ratchet.test()
    # We had a bug where all ratchet tests were sharing a failure list. This assertion prevents such a bug
    assert len(set(failure.test_name for failure in ratchet.failures)) <= 1


def test_ratchet_file_exclude_rules() -> None:
    path_exclude_check.set_allowed_count(0)
    path_exclude_check.test()


def _run_all_ratchet_examples() -> None:
    """Run all ratchet examples, to validate that the ratchet is written correctly."""
    for ratchet in [builder() for builder in ratchet_test_builders]:
        test_all_ratchet_examples(ratchet)


def _run_all_ratchet_tests() -> None:
    """Run all ratchet tests against the current codebase."""
    for ratchet in [builder() for builder in ratchet_test_builders]:
        test_ratchet(ratchet)


if __name__ == "__main__":
    fire.Fire(
        {
            "update": update,
            "test": _run_all_ratchet_tests,
            "check_examples": _run_all_ratchet_examples,
        }
    )
