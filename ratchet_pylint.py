from __future__ import annotations

from io import BufferedReader
from io import BytesIO
from typing import List
from typing import TYPE_CHECKING
from typing import Union

from astroid import nodes
from pylint.checkers import BaseRawFileChecker

from research.ratchets.ratchet_rules import ratchet_test_builders

if TYPE_CHECKING:
    from pylint.lint import PyLinter


class RatchetChecker(BaseRawFileChecker):
    name = "run_ratchet_tests"
    msgs = {
        "W9901": (
            "Ratchet test failure: %s",
            "ratchet_test_failure",
            "One of the Ratchet tests defined in research.ratchets.ratchet_rules is failing",
        )
    }
    options = ()

    def process_module(self, node: nodes.Module) -> None:
        lines = _astroid_stream_to_str_list(node.stream())

        for builder in ratchet_test_builders:
            ratchet_test = builder()
            ratchet_test.collect_failures_from_lines(lines)

            for failure in ratchet_test.failures:
                self.add_message("ratchet_test_failure", line=failure.line_number, args=(failure.test_name))


def _astroid_stream_to_str_list(stream: Union[BytesIO, BufferedReader, None]) -> List[str]:
    if stream is None:
        return []

    if hasattr(stream, "seek"):
        stream.seek(0)

    bytes_data = stream.read()
    string_data = bytes_data.decode("utf-8", errors="replace")

    return string_data.splitlines()


def register(linter: PyLinter) -> None:
    linter.register_checker(RatchetChecker(linter))
