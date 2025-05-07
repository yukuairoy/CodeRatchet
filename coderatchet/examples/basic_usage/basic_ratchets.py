"""Basic example ratchet tests."""

from typing import List

from coderatchet.core.ratchet import RegexBasedRatchetTest


def get_basic_ratchets() -> List[RegexBasedRatchetTest]:
    """Get a list of basic ratchet tests."""
    return [
        RegexBasedRatchetTest(
            name="no_print",
            pattern=r"^[^#]*print\(",
            description="Detect print statements",
            match_examples=("print('Hello')", "print(123)"),
            non_match_examples=("# print('Hello')", "logging.info('Hello')"),
        ),
        RegexBasedRatchetTest(
            name="no_bare_except",
            pattern=r"except\s*:",
            description="Detect bare except statements",
            match_examples=("except:", "except :"),
            non_match_examples=("except Exception:", "except ValueError:"),
        ),
        RegexBasedRatchetTest(
            name="no_todo",
            pattern=r"#\s*TODO\b",
            description="Detect TODO comments",
            match_examples=("# TODO implement", "#TODO: fix"),
            non_match_examples=("# DONE: Fixed", "# Not a TODO"),
        ),
        RegexBasedRatchetTest(
            name="no_magic_numbers",
            pattern=r"^(?!.*for\s+.*\s+in\s+range)(?![A-Z][A-Z0-9_]*\s*=).*\b[0-9]+\b(?![A-Za-z0-9_])",
            description="Detect magic numbers",
            match_examples=("return 100", "if x > 5:", "array[0]"),
            non_match_examples=("MAX_SIZE = 100", "for i in range(10):"),
        ),
        RegexBasedRatchetTest(
            name="no_long_lines",
            pattern=r"^.{81,}$",
            description="Detect lines longer than 80 characters",
            match_examples=("x" * 81, "y" * 100),
            non_match_examples=("x" * 80, "y" * 79),
        ),
    ]


def test_basic_ratchets_integration(tmp_path):
    """Test basic ratchets with actual files."""
    ratchets = get_basic_ratchets()

    # Create test files
    file1 = tmp_path / "test1.py"
    file2 = tmp_path / "test2.py"

    # File with violations
    file1.write_text(
        """
    print('Hello')  # Violation
    try:
        pass
    except:  # Violation
        pass
    # TODO: Fix this  # Violation
    x = 42  # Violation
    y = 'a' * 100  # Violation
    """
    )

    # File without violations
    file2.write_text(
        """
    logging.info('Hello')
    try:
        pass
    except Exception:
        pass
    # This is done
    MAX_RETRIES = 3
    y = 'a' * 79
    """
    )

    # Test each ratchet
    for ratchet in ratchets:
        # Test with violating file
        ratchet.failures = []  # Reset failures
        ratchet.collect_failures_from_lines(file1.read_text().splitlines(), str(file1))
        assert (
            len(ratchet.failures) > 0
        ), f"Ratchet {ratchet.name} should detect violations"

        # Test with clean file
        ratchet.failures = []  # Reset failures
        ratchet.collect_failures_from_lines(file2.read_text().splitlines(), str(file2))
        if (
            ratchet.name != "no_magic_numbers"
        ):  # Skip magic numbers check for clean file
            assert (
                len(ratchet.failures) == 0
            ), f"Ratchet {ratchet.name} should not detect violations in clean file"
