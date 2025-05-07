"""Tests for configuration handling in CodeRatchet."""

import pytest
import yaml

from coderatchet.core.config import (
    DEFAULT_CONFIG,
    ConfigError,
    load_config,
    save_config,
)


def test_default_config():
    """Test that default configuration is valid."""
    config = DEFAULT_CONFIG
    assert isinstance(config, dict)
    assert "ratchets" in config
    assert "git" in config
    assert "ci" in config


def test_load_valid_config(tmp_path):
    """Test loading a valid configuration file."""
    config_file = tmp_path / "coderatchet.yaml"
    config_data = {
        "ratchets": {
            "basic": {
                "enabled": True,
                "config": {},
                "allowed_count": 0,
                "match_examples": [],
                "non_match_examples": [],
                "severity": "error",
            },
            "custom": {
                "enabled": True,
                "config": {"function_length": {"max_lines": 30}},
                "allowed_count": 0,
                "match_examples": [],
                "non_match_examples": [],
                "severity": "error",
            },
        },
        "git": {"base_branch": "main", "ignore_patterns": ["*.pyc"]},
        "ci": {"fail_on_violations": True, "report_format": "text"},
    }

    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    loaded_config = load_config(config_file)
    assert loaded_config == config_data


def test_load_missing_config(tmp_path):
    """Test loading when config file is missing."""
    config_file = tmp_path / "nonexistent.yaml"
    loaded_config = load_config(config_file)
    assert loaded_config == DEFAULT_CONFIG


def test_load_invalid_yaml(tmp_path):
    """Test loading an invalid YAML file."""
    config_file = tmp_path / "invalid.yaml"
    config_file.write_text(
        """
    ratchets:
        invalid: yaml
        - this is not valid
        - yaml syntax
    """
    )

    with pytest.raises(ConfigError):
        load_config(config_file)


def test_save_config(tmp_path):
    """Test saving configuration to file."""
    config_file = tmp_path / "coderatchet.yaml"
    config_data = {"ratchets": {"basic": {"enabled": True, "config": {}}}}

    save_config(config_data, config_file)
    assert config_file.exists()

    with open(config_file) as f:
        saved_config = yaml.safe_load(f)
    assert saved_config == config_data


def test_config_validation(tmp_path):
    """Test configuration validation."""
    config_file = tmp_path / "coderatchet.yaml"

    # Test invalid ratchet configuration
    invalid_config = {
        "ratchets": {
            "basic": {"enabled": "not a boolean", "config": {}}  # Should be boolean
        }
    }

    with open(config_file, "w") as f:
        yaml.dump(invalid_config, f)

    with pytest.raises(ConfigError):
        load_config(config_file)


def test_config_merging(tmp_path):
    """Test merging of configurations."""
    base_config = {"ratchets": {"basic": {"enabled": True, "config": {}}}}

    override_config = {"ratchets": {"basic": {"enabled": False}}}

    # Save base config
    base_file = tmp_path / "base.yaml"
    with open(base_file, "w") as f:
        yaml.dump(base_config, f)

    # Save override config
    override_file = tmp_path / "override.yaml"
    with open(override_file, "w") as f:
        yaml.dump(override_config, f)

    # Load and merge configs
    base = load_config(base_file)
    override = load_config(override_file)
    merged = {**base, **override}

    assert merged["ratchets"]["basic"]["enabled"] is False


def test_environment_variables(tmp_path):
    """Test configuration with environment variables."""
    import os

    config_file = tmp_path / "coderatchet.yaml"
    config_data = {
        "ratchets": {"basic": {"enabled": True, "config": {"api_key": "${API_KEY}"}}}
    }

    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    # Set environment variable
    os.environ["API_KEY"] = "test_key"

    loaded_config = load_config(config_file)
    assert loaded_config["ratchets"]["basic"]["config"]["api_key"] == "test_key"

    # Clean up
    del os.environ["API_KEY"]


def test_config_inheritance(tmp_path):
    """Test configuration inheritance."""
    # Create base config
    base_config = {
        "ratchets": {"basic": {"enabled": True, "config": {"common_setting": "value"}}}
    }

    # Create project-specific config
    project_config = {
        "extends": "base.yaml",
        "ratchets": {"basic": {"config": {"project_specific": "value"}}},
    }

    # Save configs
    base_file = tmp_path / "base.yaml"
    project_file = tmp_path / "project.yaml"

    with open(base_file, "w") as f:
        yaml.dump(base_config, f)

    with open(project_file, "w") as f:
        yaml.dump(project_config, f)

    # Load project config
    loaded_config = load_config(project_file)

    # Verify inheritance
    assert loaded_config["ratchets"]["basic"]["enabled"] is True
    assert loaded_config["ratchets"]["basic"]["config"]["common_setting"] == "value"
    assert loaded_config["ratchets"]["basic"]["config"]["project_specific"] == "value"
