"""
Configuration management for ratchet rules.
"""

import copy
import os
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Generic, List, Optional, Set, TypeVar, Union

import yaml
from loguru import logger

from .errors import ConfigError
from .ratchet import RatchetTest, RegexBasedRatchetTest, TwoPassRatchetTest
from .ratchets import FunctionLengthRatchet
from .utils import RatchetError

T = TypeVar("T")


@dataclass
class EnvValue(Generic[T]):
    """A configuration value that can be overridden by environment variables."""

    default: T
    env_var: str
    transform: callable = lambda x: x

    def get(self) -> T:
        """Get the value, checking environment variables first."""
        if self.env_var in os.environ:
            try:
                return self.transform(os.environ[self.env_var])
            except (ValueError, TypeError) as e:
                logger.warning(
                    f"Failed to parse environment variable {self.env_var}: {e}"
                )
                return self.default
        return self.default


@dataclass
class RatchetConfig:
    """Configuration for a ratchet rule.

    Attributes:
        name: Name of the ratchet rule
        pattern: Regex pattern to match against
        match_examples: List of example strings that should match the pattern
        non_match_examples: List of example strings that should not match the pattern
        description: Optional description of what the ratchet rule checks for
        is_two_pass: Whether this is a two-pass ratchet rule
        second_pass_pattern: Optional pattern for the second pass
        second_pass_examples: Optional examples for the second pass
        second_pass_non_examples: Optional non-examples for the second pass
        enabled: Whether this ratchet is enabled
        severity: Severity level of violations
        file_pattern: Optional pattern to match file paths
        exclude_pattern: Optional pattern to exclude file paths
    """

    name: str
    pattern: str
    match_examples: List[str] = field(default_factory=list)
    non_match_examples: List[str] = field(default_factory=list)
    description: Optional[str] = None
    is_two_pass: bool = False
    second_pass_pattern: Optional[str] = None
    second_pass_examples: Optional[List[str]] = None
    second_pass_non_examples: Optional[List[str]] = None
    enabled: bool = True
    severity: str = "error"
    file_pattern: Optional[str] = None
    exclude_pattern: Optional[str] = None

    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate()

    def _validate(self):
        """Validate the configuration."""
        if not self.name:
            raise ConfigError("Ratchet name is required")
        if not self.pattern:
            raise ConfigError(f"Pattern is required for ratchet '{self.name}'")
        try:
            re.compile(self.pattern)
        except re.error as e:
            raise ConfigError(f"Invalid pattern for ratchet '{self.name}': {e}")

        if self.is_two_pass:
            if not self.second_pass_pattern:
                msg = (
                    f"Second pass pattern is required for two-pass "
                    f"ratchet '{self.name}'"
                )
                raise ConfigError(msg)
            try:
                re.compile(self.second_pass_pattern)
            except re.error as e:
                raise ConfigError(
                    f"Invalid second pass pattern for ratchet '{self.name}': {e}"
                )

        if self.file_pattern:
            try:
                re.compile(self.file_pattern)
            except re.error as e:
                raise ConfigError(
                    f"Invalid file pattern for ratchet '{self.name}': {e}"
                )

        if self.exclude_pattern:
            try:
                re.compile(self.exclude_pattern)
            except re.error as e:
                raise ConfigError(
                    f"Invalid exclude pattern for ratchet '{self.name}': {e}"
                )

        if self.severity not in {"error", "warning", "info"}:
            raise ConfigError(
                f"Invalid severity '{self.severity}' for ratchet '{self.name}'"
            )


@lru_cache(maxsize=None)
def load_config(
    config_file: Union[str, Path], _visited: Optional[frozenset] = None, _depth: int = 0
) -> Dict[str, Any]:
    """Load configuration from a YAML file with environment variable substitution.

    Args:
        config_file: Path to configuration file
        _visited: Frozenset of visited file paths (internal use)
        _depth: Current recursion depth (internal use)

    Returns:
        Configuration dictionary

    Raises:
        ConfigError: If configuration is invalid
    """
    MAX_DEPTH = 10  # Maximum recursion depth for config inheritance

    if _depth > MAX_DEPTH:
        raise ConfigError("Maximum config inheritance depth exceeded")

    visited_paths = set() if _visited is None else set(_visited)

    try:
        config_path = Path(config_file)
        if not config_path.exists():
            return DEFAULT_CONFIG

        abs_path = config_path.resolve()
        if abs_path in visited_paths:
            raise ConfigError(
                f"Circular dependency detected in config inheritance: {abs_path}"
            )

        visited_paths.add(abs_path)

        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        if not isinstance(config, dict):
            raise ConfigError("Configuration must be a dictionary")

        # Handle inheritance first
        if "extends" in config:
            base_config_path = config_path.parent / config["extends"]
            try:
                base_config = load_config(
                    base_config_path, frozenset(visited_paths), _depth + 1
                )
                config = merge_configs(base_config, config)
            except (OSError, ConfigError) as e:
                raise ConfigError(
                    f"Failed to load base configuration from {base_config_path}: {e}"
                )

        # Substitute environment variables
        config = substitute_env_vars(config)

        # Validate and set defaults for ratchets
        if "ratchets" not in config:
            config["ratchets"] = {}

        for name, ratchet_config in config["ratchets"].items():
            if not isinstance(ratchet_config, dict):
                ratchet_config = {}
                config["ratchets"][name] = ratchet_config

            # Set default values
            ratchet_config.setdefault("enabled", True)
            ratchet_config.setdefault("config", {})
            ratchet_config.setdefault("allowed_count", 0)
            ratchet_config.setdefault("match_examples", [])
            ratchet_config.setdefault("non_match_examples", [])
            ratchet_config.setdefault("severity", "error")

            # Validate types
            if not isinstance(ratchet_config["enabled"], bool):
                raise ConfigError(
                    f"'enabled' field for ratchet '{name}' must be a boolean"
                )
            if not isinstance(ratchet_config["config"], dict):
                raise ConfigError(
                    f"'config' field for ratchet '{name}' must be a dictionary"
                )
            if not isinstance(ratchet_config["allowed_count"], int):
                raise ConfigError(
                    f"'allowed_count' field for ratchet '{name}' must be an integer"
                )
            if not isinstance(ratchet_config["match_examples"], list):
                raise ConfigError(
                    f"'match_examples' field for ratchet '{name}' must be a list"
                )
            if not isinstance(ratchet_config["non_match_examples"], list):
                raise ConfigError(
                    f"'non_match_examples' field for ratchet '{name}' must be a list"
                )
            if ratchet_config["severity"] not in {"error", "warning", "info"}:
                raise ConfigError(
                    "'severity' field for ratchet '" + name + "' "
                    "must be one of: error, warning, info"
                )

        return config

    except yaml.YAMLError as e:
        raise ConfigError(f"Failed to load configuration file: {e}")


def merge_configs(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two configurations, with override taking precedence.

    Args:
        base: Base configuration
        override: Configuration to override with

    Returns:
        Merged configuration
    """
    result = copy.deepcopy(base)

    def deep_merge(d1: Dict[str, Any], d2: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge two dictionaries."""
        for k, v in d2.items():
            if k in d1 and isinstance(d1[k], dict) and isinstance(v, dict):
                deep_merge(d1[k], v)
            else:
                d1[k] = copy.deepcopy(v)
        return d1

    return deep_merge(result, override)


def substitute_env_vars(config: Dict[str, Any]) -> Dict[str, Any]:
    """Substitute environment variables in configuration values.

    Args:
        config: Configuration dictionary

    Returns:
        Configuration with environment variables substituted
    """

    def substitute_value(value: Any) -> Any:
        """Substitute environment variables in a value."""
        if isinstance(value, str):
            # Match ${VAR} or $VAR format
            pattern = r"\$\{([^}]+)\}|\$([a-zA-Z_][a-zA-Z0-9_]*)"

            def replace(match):
                var_name = match.group(1) or match.group(2)
                return os.environ.get(var_name, match.group(0))

            return re.sub(pattern, replace, value)
        elif isinstance(value, dict):
            return {k: substitute_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [substitute_value(item) for item in value]
        return value

    return substitute_value(config)


def create_ratchet_tests(
    configs: List[RatchetConfig],
) -> List[Union[RegexBasedRatchetTest, TwoPassRatchetTest]]:
    """Create ratchet tests from configurations.

    Args:
        configs: List of ratchet configurations

    Returns:
        List of ratchet tests

    Raises:
        ConfigError: If a configuration is invalid
    """
    tests = []
    for config in configs:
        try:
            if not config.enabled:
                continue

            # Create test instance with basic attributes
            test_args = {
                "description": config.description or "",
                "allowed_count": 0,
                "exclude_test_files": False,
            }

            # Add file pattern if specified
            if config.file_pattern:
                try:
                    test_args["include_file_regex"] = re.compile(config.file_pattern)
                except re.error as e:
                    raise ConfigError(
                        f"Invalid file pattern for ratchet '{config.name}': {e}"
                    )

            # Create appropriate test type
            if config.is_two_pass:
                test = TwoPassRatchetTest.from_config(config)
            else:
                test = RegexBasedRatchetTest(
                    name=config.name,
                    pattern=config.pattern,
                    match_examples=config.match_examples,
                    non_match_examples=config.non_match_examples,
                    **test_args,
                )

            tests.append(test)
        except (re.error, RatchetError) as e:
            raise ConfigError(f"Invalid configuration for ratchet '{config.name}': {e}")

    return tests


class RatchetConfigManager:
    """Configuration manager for CodeRatchet."""

    def __init__(self, config_path: str = "coderatchet.yaml"):
        """Initialize the configuration.

        Args:
            config_path: Path to the configuration file
        """
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if not Path(self.config_path).exists():
            return self._get_default_config()

        with open(self.config_path, "r") as f:
            return yaml.safe_load(f)

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "ratchets": {
                "basic": {"enabled": True, "config": {}},
                "custom": {
                    "enabled": True,
                    "config": {"function_length": {"max_lines": 50}},
                },
            },
            "git": {
                "base_branch": "main",
                "ignore_patterns": ["*.pyc", "__pycache__/*", "*.egg-info/*"],
            },
            "ci": {"fail_on_violations": True, "report_format": "text"},
        }

    def get_ratchets(self) -> List[RatchetTest]:
        """Get configured ratchet tests."""
        from ..examples.basic_usage.basic_ratchets import get_basic_ratchets
        from ..examples.basic_usage.custom_ratchets import get_custom_ratchets

        ratchets = []

        # Add basic ratchets if enabled
        if self.config["ratchets"]["basic"]["enabled"]:
            ratchets.extend(get_basic_ratchets())

        # Add custom ratchets if enabled
        if self.config["ratchets"]["custom"]["enabled"]:
            custom_ratchets = get_custom_ratchets()
            for ratchet in custom_ratchets:
                # Apply custom configuration
                if ratchet.name in self.config["ratchets"]["custom"]["config"]:
                    config = self.config["ratchets"]["custom"]["config"][ratchet.name]
                    if isinstance(ratchet, FunctionLengthRatchet):
                        ratchet.max_lines = config.get("max_lines", 50)
                ratchets.append(ratchet)

        return ratchets

    def save_config(self):
        """Save current configuration to file."""
        with open(self.config_path, "w") as f:
            yaml.dump(self.config, f, default_flow_style=False)


def save_config(config: Dict[str, Any], config_path: Path) -> None:
    """Save configuration to file.

    Args:
        config: Configuration dictionary to save
        config_path: Path to save configuration to
    """
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)


DEFAULT_CONFIG = {
    "ratchets": {
        "basic": {
            "enabled": True,
            "config": {},
            "allowed_count": 0,
            "match_examples": [],
            "non_match_examples": [],
        },
        "custom": {
            "enabled": True,
            "config": {
                "function_length": {
                    "max_lines": 50,
                },
            },
            "allowed_count": 0,
            "match_examples": [],
            "non_match_examples": [],
        },
    },
    "git": {
        "base_branch": "main",
        "ignore_patterns": ["*.pyc", "__pycache__/*", "*.egg-info/*"],
    },
    "ci": {
        "fail_on_violations": True,
        "report_format": "text",
    },
}


def load_ratchet_configs(
    config_file: Optional[Union[str, Path]] = None
) -> List[RatchetConfig]:
    """Load ratchet configurations from a YAML file.

    Args:
        config_file: Optional path to configuration file. If None, uses default config.

    Returns:
        List of RatchetConfig objects

    Raises:
        ConfigError: If configuration is invalid
    """
    # Load raw config
    raw_config = load_config(config_file) if config_file else DEFAULT_CONFIG

    # Extract ratchet configurations
    ratchet_configs = []
    for name, config in raw_config.get("ratchets", {}).items():
        if not isinstance(config, dict):
            continue

        if not config.get("enabled", True):
            continue

        # Skip the "basic" and "custom" ratchets since they are handled separately
        if name in ["basic", "custom"]:
            continue

        ratchet_config = RatchetConfig(
            name=name,
            pattern=config.get("pattern", ""),
            match_examples=config.get("match_examples", []),
            non_match_examples=config.get("non_match_examples", []),
            description=config.get("description"),
            is_two_pass=config.get("is_two_pass", False),
            second_pass_pattern=config.get("second_pass_pattern"),
            second_pass_examples=config.get("second_pass_examples"),
            second_pass_non_examples=config.get("second_pass_non_examples"),
            enabled=config.get("enabled", True),
            severity=config.get("severity", "error"),
            file_pattern=config.get("file_pattern"),
            exclude_pattern=config.get("exclude_pattern"),
        )
        ratchet_configs.append(ratchet_config)

    return ratchet_configs


def get_ratchet_tests(
    return_set: bool = False,
) -> Union[List[RatchetTest], Set[RatchetTest]]:
    """Get all ratchet tests to check.

    Args:
        return_set: If True, returns a set of tests instead of a list

    Returns:
        List or Set of ratchet tests created from loaded configurations.
    """
    configs = load_ratchet_configs()
    tests = create_ratchet_tests(configs)
    return set(tests) if return_set else tests
