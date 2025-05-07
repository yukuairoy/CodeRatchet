"""Core functionality for CodeRatchet."""

from .comparison import compare_ratchets
from .config import RatchetConfig, create_ratchet_tests, load_ratchet_configs
from .errors import ConfigError
from .git_integration import GitError, GitIntegration
from .ratchet import RatchetTest, RegexBasedRatchetTest, TestFailure, TwoPassRatchetTest
from .ratchets import FunctionLengthRatchet
from .recent_failures import get_recently_broken_ratchets
from .utils import get_ratchet_test_files, load_ratchet_count

__all__ = [
    "RatchetTest",
    "RegexBasedRatchetTest",
    "TwoPassRatchetTest",
    "TestFailure",
    "FunctionLengthRatchet",
    "compare_ratchets",
    "ConfigError",
    "RatchetConfig",
    "load_ratchet_configs",
    "create_ratchet_tests",
    "GitIntegration",
    "GitError",
    "get_recently_broken_ratchets",
    "get_ratchet_test_files",
    "load_ratchet_count",
]
