"""Tests for configuration functionality."""

import os

import pytest
import yaml

from coderatchet.examples.advanced.configuration import RatchetConfigManager


def test_config_init_default():
    """Test RatchetConfig initialization with default settings."""
    config = RatchetConfigManager()

    assert config.config_path == "coderatchet.yaml"
    assert isinstance(config.config, dict)
    assert "ratchets" in config.config
    assert "git" in config.config
    assert "ci" in config.config


def test_config_init_custom_path():
    """Test RatchetConfig initialization with custom path."""
    config = RatchetConfigManager("custom.yaml")
    assert config.config_path == "custom.yaml"


def test_config_default_values():
    """Test default configuration values."""
    config = RatchetConfigManager()

    # Check ratchets section
    assert config.config["ratchets"]["basic"]["enabled"]
    assert config.config["ratchets"]["custom"]["enabled"]
    assert (
        config.config["ratchets"]["custom"]["config"]["function_length"]["max_lines"]
        == 50
    )

    # Check git section
    assert config.config["git"]["base_branch"] == "main"
    assert "*.pyc" in config.config["git"]["ignore_patterns"]
    assert "__pycache__/*" in config.config["git"]["ignore_patterns"]

    # Check CI section
    assert config.config["ci"]["fail_on_violations"]
    assert config.config["ci"]["report_format"] == "text"


def test_config_load_save(tmp_path):
    """Test loading and saving configuration."""
    config_path = tmp_path / "test_config.yaml"

    # Create initial config
    config = RatchetConfigManager(str(config_path))
    config.config["ratchets"]["custom"]["config"]["function_length"]["max_lines"] = 30
    config.save_config()

    # Load config and verify changes
    new_config = RatchetConfigManager(str(config_path))
    assert (
        new_config.config["ratchets"]["custom"]["config"]["function_length"][
            "max_lines"
        ]
        == 30
    )


def test_config_invalid_yaml(tmp_path):
    """Test handling of invalid YAML configuration."""
    config_path = tmp_path / "invalid_config.yaml"

    # Create invalid YAML file
    config_path.write_text("invalid: yaml: content: [")

    # Should fall back to default config
    config = RatchetConfigManager(str(config_path))
    assert isinstance(config.config, dict)
    assert "ratchets" in config.config


def test_config_get_ratchets(tmp_path):
    """Test getting configured ratchets."""
    config_path = tmp_path / "test_config.yaml"

    # Create config with basic ratchets disabled
    config_data = {
        "ratchets": {
            "basic": {"enabled": False, "config": {}},
            "custom": {
                "enabled": True,
                "config": {"function_length": {"max_lines": 30}},
            },
        },
        "git": {"base_branch": "main", "ignore_patterns": ["*.pyc"]},
        "ci": {"fail_on_violations": True, "report_format": "text"},
    }

    with open(config_path, "w") as f:
        yaml.dump(config_data, f)

    config = RatchetConfigManager(str(config_path))
    ratchets = config.get_ratchets()

    # Should only have custom ratchets since basic are disabled
    assert len(ratchets) > 0
    assert all(not r.name.startswith("basic_") for r in ratchets)


def test_config_custom_ratchet_config(tmp_path):
    """Test configuration of custom ratchets."""
    config_path = tmp_path / "test_config.yaml"

    # Create config with custom function length
    config_data = {
        "ratchets": {
            "basic": {"enabled": False, "config": {}},
            "custom": {
                "enabled": True,
                "config": {"function_length": {"max_lines": 25}},  # Custom value
            },
        },
        "git": {"base_branch": "main", "ignore_patterns": []},
        "ci": {"fail_on_violations": True, "report_format": "text"},
    }

    with open(config_path, "w") as f:
        yaml.dump(config_data, f)

    config = RatchetConfigManager(str(config_path))
    ratchets = config.get_ratchets()

    # Find function length ratchet
    func_length_ratchet = next(
        (r for r in ratchets if r.name == "function_length"), None
    )

    assert func_length_ratchet is not None
    assert func_length_ratchet.max_lines == 25


def test_config_file_permissions(tmp_path):
    """Test handling of file permission issues."""
    config_path = tmp_path / "test_config.yaml"

    # Create config file without write permissions
    config = RatchetConfigManager(str(config_path))
    config.save_config()
    os.chmod(config_path, 0o444)  # Read-only

    try:
        # Attempt to save config
        with pytest.raises(PermissionError):
            config.save_config()
    finally:
        os.chmod(config_path, 0o644)  # Restore permissions
