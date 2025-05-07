"""Test failure class for CodeRatchet."""

from dataclasses import dataclass


@dataclass
class TestFailure:
    """A test failure."""

    test_name: str
    filepath: str
    line_number: int
    line_contents: str
    commit_hash: str | None = None
    commit_message: str | None = None
    commit_author: str | None = None
    commit_date: str | None = None

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
