"""Examples of CodeRatchet configuration and usage patterns."""

from pathlib import Path
from typing import Any, Dict, List

import yaml

from coderatchet.core.ratchet import RatchetTest
from coderatchet.core.ratchets import FunctionLengthRatchet
from coderatchet.examples.basic_usage.basic_ratchets import get_basic_ratchets
from coderatchet.examples.basic_usage.custom_ratchets import get_custom_ratchets


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

        try:
            with open(self.config_path, "r") as f:
                config = yaml.safe_load(f)
            if not isinstance(config, dict):
                return self._get_default_config()
            return config
        except (yaml.YAMLError, IOError) as e:
            print(f"Error loading config file {self.config_path}: {e}")
            return self._get_default_config()

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
        ratchets = []

        # Add basic ratchets if enabled
        if self.config["ratchets"]["basic"]["enabled"]:
            # Get basic ratchets and create new instances to avoid modifying frozen ones
            for ratchet in get_basic_ratchets():
                ratchets.append(
                    RegexBasedRatchetTest(
                        name=ratchet.name,
                        pattern=ratchet.pattern,
                        description=ratchet.description,
                        match_examples=ratchet.match_examples,
                        non_match_examples=ratchet.non_match_examples,
                        allowed_count=ratchet.allowed_count,
                        exclude_test_files=ratchet.exclude_test_files,
                    )
                )

        # Add custom ratchets if enabled
        if self.config["ratchets"]["custom"]["enabled"]:
            custom_config = self.config["ratchets"]["custom"]["config"]

            # Get custom ratchets and create new instances with custom configuration
            for ratchet in get_custom_ratchets():
                if ratchet.name in custom_config:
                    config = custom_config[ratchet.name]
                    if isinstance(ratchet, FunctionLengthRatchet):
                        # Create a new FunctionLengthRatchet with custom configuration
                        ratchets.append(
                            FunctionLengthRatchet(
                                max_lines=config.get("max_lines", 50),
                                name=ratchet.name,
                                description=ratchet.description,
                                allowed_count=ratchet.allowed_count,
                                exclude_test_files=ratchet.exclude_test_files,
                                match_examples=ratchet.match_examples,
                                non_match_examples=ratchet.non_match_examples,
                            )
                        )
                else:
                    # Create a new instance of the ratchet without modification
                    if isinstance(ratchet, FunctionLengthRatchet):
                        ratchets.append(
                            FunctionLengthRatchet(
                                max_lines=ratchet.max_lines,
                                name=ratchet.name,
                                description=ratchet.description,
                                allowed_count=ratchet.allowed_count,
                                exclude_test_files=ratchet.exclude_test_files,
                                match_examples=ratchet.match_examples,
                                non_match_examples=ratchet.non_match_examples,
                            )
                        )
                    else:
                        ratchets.append(
                            RegexBasedRatchetTest(
                                name=ratchet.name,
                                pattern=ratchet.pattern,
                                description=ratchet.description,
                                match_examples=ratchet.match_examples,
                                non_match_examples=ratchet.non_match_examples,
                                allowed_count=ratchet.allowed_count,
                                exclude_test_files=ratchet.exclude_test_files,
                            )
                        )

        return ratchets

    def save_config(self):
        """Save current configuration to file."""
        with open(self.config_path, "w") as f:
            yaml.dump(self.config, f, default_flow_style=False)


def example_usage():
    """Example usage of the configuration system."""
    # Create a new configuration
    config = RatchetConfigManager()

    # Modify some settings
    config.config["ratchets"]["custom"]["config"]["function_length"]["max_lines"] = 30
    config.config["git"]["ignore_patterns"].append("tests/*")

    # Save the configuration
    config.save_config()

    # Get configured ratchets
    ratchets = config.get_ratchets()
    print(f"Loaded {len(ratchets)} ratchet tests")

    # Example: Run ratchets on a specific file
    from ..core.ratchet import run_ratchets_on_file

    results = run_ratchets_on_file(
        "example.py", ratchets, ignore_patterns=config.config["git"]["ignore_patterns"]
    )

    # Print results
    if results.failures:
        print("\nViolations found:")
        for failure in results.failures:
            print(f"{failure.file_path}:{failure.line_number} - {failure.message}")
    else:
        print("\nNo violations found")


def test_configuration(tmp_path):
    """Test configuration functionality."""
    # Create test config file
    config_path = tmp_path / "test_config.yaml"
    config = RatchetConfigManager(str(config_path))

    # Test default config
    assert config.config["ratchets"]["basic"]["enabled"]
    assert config.config["ratchets"]["custom"]["enabled"]
    assert config.config["git"]["base_branch"] == "main"

    # Test ratchet loading
    ratchets = config.get_ratchets()
    assert len(ratchets) > 0

    # Test config modification
    config.config["ratchets"]["custom"]["config"]["function_length"]["max_lines"] = 30
    config.save_config()

    # Reload config
    new_config = RatchetConfigManager(str(config_path))
    assert (
        new_config.config["ratchets"]["custom"]["config"]["function_length"][
            "max_lines"
        ]
        == 30
    )
