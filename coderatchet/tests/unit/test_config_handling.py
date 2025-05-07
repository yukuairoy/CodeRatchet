"""Tests for improved configuration handling."""

import os

import pytest
import yaml

from coderatchet.core.config import (
    ConfigError,
    EnvValue,
    RatchetConfig,
    create_ratchet_tests,
    load_config,
    merge_configs,
    substitute_env_vars,
)


def test_env_value():
    """Test environment variable handling."""
    # Test with no environment variable
    value = EnvValue(default=42, env_var="TEST_VALUE")
    assert value.get() == 42

    # Test with environment variable
    os.environ["TEST_VALUE"] = "84"
    value = EnvValue(default=42, env_var="TEST_VALUE", transform=int)
    assert value.get() == 84

    # Test with invalid environment variable
    os.environ["TEST_VALUE"] = "not_a_number"
    value = EnvValue(default=42, env_var="TEST_VALUE", transform=int)
    assert value.get() == 42  # Should return default on error


def test_ratchet_config_validation():
    """Test RatchetConfig validation."""
    # Test valid configuration
    config = RatchetConfig(
        name="test",
        pattern=r"print\(",
        match_examples=["print('hello')"],
        non_match_examples=["log('hello')"],
        severity="error",
    )
    assert config.name == "test"
    assert config.pattern == r"print\("

    # Test invalid pattern
    with pytest.raises(ConfigError, match="Invalid pattern"):
        RatchetConfig(
            name="test",
            pattern="[",  # Invalid regex
            match_examples=[],
            non_match_examples=[],
        )

    # Test invalid severity
    with pytest.raises(ConfigError, match="Invalid severity"):
        RatchetConfig(
            name="test",
            pattern=r"print\(",
            severity="invalid",
        )

    # Test two-pass validation
    with pytest.raises(ConfigError, match="Second pass pattern is required"):
        RatchetConfig(
            name="test",
            pattern=r"print\(",
            is_two_pass=True,
        )


def test_config_inheritance(tmp_path):
    """Test configuration inheritance."""
    # Create base config
    base_config = {
        "ratchets": {
            "test1": {
                "enabled": True,
                "pattern": r"print\(",
                "severity": "error",
            }
        }
    }
    base_path = tmp_path / "base.yaml"
    with open(base_path, "w") as f:
        yaml.dump(base_config, f)

    # Create extending config
    extend_config = {
        "extends": "base.yaml",
        "ratchets": {
            "test1": {
                "severity": "warning",  # Override base
            },
            "test2": {  # New ratchet
                "enabled": True,
                "pattern": r"debug\(",
            },
        },
    }
    extend_path = tmp_path / "extend.yaml"
    with open(extend_path, "w") as f:
        yaml.dump(extend_config, f)

    # Load and verify
    config = load_config(extend_path)
    assert config["ratchets"]["test1"]["severity"] == "warning"
    assert config["ratchets"]["test1"]["enabled"] is True
    assert config["ratchets"]["test2"]["pattern"] == r"debug\("


def test_env_var_substitution():
    """Test environment variable substitution."""
    os.environ["TEST_PATTERN"] = r"print\("
    os.environ["TEST_SEVERITY"] = "warning"

    config = {
        "ratchets": {
            "test1": {
                "pattern": "${TEST_PATTERN}",
                "severity": "$TEST_SEVERITY",
            }
        }
    }

    result = substitute_env_vars(config)
    assert result["ratchets"]["test1"]["pattern"] == r"print\("
    assert result["ratchets"]["test1"]["severity"] == "warning"


def test_create_ratchet_tests():
    """Test creation of ratchet tests."""
    configs = [
        RatchetConfig(
            name="test1",
            pattern=r"print\(",
            match_examples=["print('hello')"],
            non_match_examples=["log('hello')"],
            file_pattern=r"\.py$",
        ),
        RatchetConfig(
            name="test2",
            pattern=r"class\s+\w+",
            is_two_pass=True,
            second_pass_pattern=r"self\.\w+",
            match_examples=["class Test"],
            second_pass_examples=["self.value"],
            non_match_examples=["def test():", "value"],
        ),
        RatchetConfig(
            name="disabled_test",
            pattern=r"debug\(",
            enabled=False,
        ),
    ]

    tests = create_ratchet_tests(configs)
    assert len(tests) == 2  # disabled_test should be excluded
    assert tests[0].name == "test1"
    assert tests[0].include_file_regex.pattern == r"\.py$"
    assert tests[1].name == "test2"
    assert tests[1].first_pass.pattern == r"class\s+\w+"


def test_config_error_handling(tmp_path):
    """Test configuration error handling."""
    # Test invalid YAML
    invalid_yaml = tmp_path / "invalid.yaml"
    invalid_yaml.write_text("invalid: yaml: :")
    with pytest.raises(ConfigError, match="Failed to load configuration file"):
        load_config(invalid_yaml)

    # Test invalid ratchet config
    invalid_config = {
        "ratchets": {
            "test": {
                "enabled": "not_a_boolean",  # Should be boolean
            }
        }
    }
    invalid_path = tmp_path / "invalid_config.yaml"
    with open(invalid_path, "w") as f:
        yaml.dump(invalid_config, f)

    with pytest.raises(ConfigError, match="must be a boolean"):
        load_config(invalid_path)


def test_merge_configs():
    """Test configuration merging."""
    base = {
        "ratchets": {
            "test1": {
                "enabled": True,
                "config": {
                    "max_lines": 50,
                },
            },
        },
        "git": {
            "ignore": ["*.pyc"],
        },
    }

    override = {
        "ratchets": {
            "test1": {
                "config": {
                    "max_lines": 100,
                },
            },
            "test2": {
                "enabled": True,
            },
        },
        "git": {
            "ignore": ["*.pyc", "*.pyo"],
        },
    }

    result = merge_configs(base, override)
    assert result["ratchets"]["test1"]["enabled"] is True
    assert result["ratchets"]["test1"]["config"]["max_lines"] == 100
    assert result["ratchets"]["test2"]["enabled"] is True
    assert result["git"]["ignore"] == ["*.pyc", "*.pyo"]
