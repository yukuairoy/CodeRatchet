"""Examples of custom ratchet test implementations."""

from typing import List

from coderatchet.core.ratchet import RatchetTest
from coderatchet.core.ratchets import FunctionLengthRatchet


def get_custom_ratchets() -> List[RatchetTest]:
    """Get a list of custom ratchet tests."""
    return [
        FunctionLengthRatchet(
            max_lines=50,
            name="function_length",
            description="Functions should not exceed maximum length",
            allowed_count=0,
            exclude_test_files=True,
        ),
    ]


def get_custom_ratchet_names() -> List[str]:
    """Get a list of custom ratchet names."""
    return [ratchet.name for ratchet in get_custom_ratchets()]


def test_custom_ratchets():
    """Test custom ratchet implementations."""
    ratchets = get_custom_ratchets()
    assert len(ratchets) == 1

    # Test FunctionLengthRatchet
    func_length = next(r for r in ratchets if r.name == "function_length")
    assert isinstance(func_length, FunctionLengthRatchet)
    assert func_length.max_lines == 50
