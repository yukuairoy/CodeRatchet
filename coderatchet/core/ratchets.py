"""Built-in ratchet implementations."""

import ast
from typing import List, Optional

import attr

from .ratchet import RatchetTest, TestFailure


@attr.s(frozen=True, auto_attribs=True)
class FunctionLengthRatchet(RatchetTest):
    """Ratchet that enforces a maximum function length."""

    max_lines: int = attr.ib(default=50)

    def __init__(
        self,
        max_lines: int = 50,
        name: str = "function_length",
        description: str = "Functions should not exceed maximum length",
        allowed_count: int = 0,
        exclude_test_files: bool = True,
        match_examples: Optional[List[str]] = None,
        non_match_examples: Optional[List[str]] = None,
    ):
        """Initialize the ratchet.

        Args:
            max_lines: Maximum number of lines allowed in a function
            name: Name of the ratchet
            description: Description of what the ratchet checks for
            allowed_count: Number of violations allowed
            exclude_test_files: Whether to exclude test files
            match_examples: Example functions that should match
            non_match_examples: Example functions that should not match
        """
        example_short = "def short_function():\n    pass"
        example_medium = (
            "def medium_function():\n" "    x = 1\n" "    y = 2\n" "    return x + y"
        )
        example_long = (
            "def long_function():\n"
            "    x = 1\n    y = 2\n    z = 3\n"
            "    a = 4\n    b = 5\n    c = 6\n"
            "    d = 7\n    e = 8\n    f = 9\n"
            "    g = 10\n"
            "    return x + y + z + a + b + c + d + e + f + g"
        )

        super().__init__(
            name=name,
            description=description,
            allowed_count=allowed_count,
            exclude_test_files=exclude_test_files,
            match_examples=match_examples or [example_short, example_medium],
            non_match_examples=non_match_examples or [example_long],
        )
        object.__setattr__(self, "max_lines", max_lines)

    def collect_failures_from_lines(
        self, lines: List[str], filepath: str = ""
    ) -> List[TestFailure]:
        """Collect failures from lines of code.

        Args:
            lines: Lines of code to check
            filepath: Path to the file being checked

        Returns:
            List of test failures
        """
        failures = []
        try:
            tree = ast.parse("\n".join(lines))
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Get the line range of the function
                    start_line = node.lineno
                    end_line = node.end_lineno or start_line
                    function_length = end_line - start_line + 1

                    if function_length > self.max_lines:
                        msg = (
                            f"Function '{node.name}' is {function_length} lines long, "
                            f"exceeding the maximum of {self.max_lines} lines"
                        )
                        failures.append(
                            TestFailure(
                                test_name=self.name,
                                filepath=filepath,
                                line_number=start_line,
                                line_contents=msg,
                            )
                        )
        except SyntaxError:
            # If there's a syntax error, we can't parse the file
            # This is not a ratchet failure, so we return an empty list
            pass

        return failures
