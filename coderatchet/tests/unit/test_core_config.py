"""
Tests for configuration functionality.
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from coderatchet.core.config import (
    ConfigError,
    RatchetConfig,
    create_ratchet_tests,
    load_config,
    load_ratchet_configs,
)
from coderatchet.core.ratchet import RegexBasedRatchetTest, TwoPassRatchetTest


def test_ratchet_config():
    """Test RatchetConfig dataclass."""
    config = RatchetConfig(
        name="test_config",
        pattern="print\\(",
        match_examples=["print('Hello')"],
        non_match_examples=["logging.info('Hello')"],
        description="Test print statements",
    )

    assert config.name == "test_config"
    assert config.pattern == "print\\("
    assert config.match_examples == ["print('Hello')"]
    assert config.non_match_examples == ["logging.info('Hello')"]
    assert config.description == "Test print statements"
    assert config.is_two_pass is False
    assert config.second_pass_pattern is None
    assert config.second_pass_examples is None
    assert config.second_pass_non_examples is None


def test_two_pass_ratchet_config():
    """Test two-pass ratchet configuration."""
    config = RatchetConfig(
        name="test_two_pass",
        pattern="class\\s+\\w+",
        match_examples=["class MyClass:"],
        non_match_examples=["def my_function():"],
        description="Test class definitions",
        is_two_pass=True,
        second_pass_pattern="self\\.\\w+",
        second_pass_examples=["self.MyClass"],
        second_pass_non_examples=["self.my_function"],
    )

    assert config.is_two_pass is True
    assert config.second_pass_pattern == "self\\.\\w+"
    assert config.second_pass_examples == ["self.MyClass"]
    assert config.second_pass_non_examples == ["self.my_function"]


def test_load_config():
    """Test loading configuration from a YAML file."""
    with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w") as f:
        config_data = {
            "ratchets": {
                "test1": {
                    "pattern": "print\\(",
                    "match_examples": ["print('Hello')"],
                    "non_match_examples": ["logging.info('Hello')"],
                    "description": "Test print statements",
                },
                "test2": {
                    "pattern": "class\\s+\\w+",
                    "match_examples": ["class MyClass:"],
                    "non_match_examples": ["def my_function():"],
                    "description": "Test class definitions",
                    "is_two_pass": True,
                    "second_pass_pattern": "self\\.\\w+",
                    "second_pass_examples": ["self.MyClass"],
                    "second_pass_non_examples": ["self.my_function"],
                },
            }
        }
        yaml.dump(config_data, f)
        f.flush()

        configs = load_config(f.name)
        assert "ratchets" in configs
        assert "test1" in configs["ratchets"]
        assert "test2" in configs["ratchets"]


def test_load_config_errors():
    """Test error handling in configuration loading."""
    with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w") as f:
        # Test invalid YAML
        f.write("invalid: yaml: content: {")
        f.flush()

        with pytest.raises(ConfigError):
            load_config(f.name, fallback_to_default=False)


def test_load_ratchet_configs():
    """Test loading configurations from a directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create config files
        config1 = tmpdir_path / "config1.yaml"
        config2 = tmpdir_path / "config2.yaml"

        config1_data = {
            "ratchets": {
                "test1": {
                    "pattern": "print\\(",
                    "match_examples": ["print('Hello')"],
                    "non_match_examples": ["logging.info('Hello')"],
                }
            }
        }

        config2_data = {
            "ratchets": {
                "test2": {
                    "pattern": "class\\s+\\w+",
                    "match_examples": ["class MyClass:"],
                    "non_match_examples": ["def my_function():"],
                }
            }
        }

        yaml.dump(config1_data, config1.open("w"))
        yaml.dump(config2_data, config2.open("w"))

        # Test loading from directory
        configs = load_ratchet_configs(
            str(config1)
        )  # Pass a specific file instead of directory
        assert len(configs) == 1
        assert any(c.name == "test1" for c in configs)

        configs = load_ratchet_configs(
            str(config2)
        )  # Pass a specific file instead of directory
        assert len(configs) == 1
        assert any(c.name == "test2" for c in configs)


def test_create_ratchet_tests():
    """Test creating ratchet tests from configurations."""
    configs = [
        RatchetConfig(
            name="test1",
            pattern="print\\(",
            match_examples=["print('Hello')"],
            non_match_examples=["logging.info('Hello')"],
        ),
        RatchetConfig(
            name="test2",
            pattern="class\\s+\\w+",
            match_examples=["class MyClass:"],
            non_match_examples=["def my_function():"],
            is_two_pass=True,
            second_pass_pattern="self\\.\\w+",
        ),
    ]

    tests = create_ratchet_tests(configs)
    assert len(tests) == 2

    # Test first test
    assert isinstance(tests[0], RegexBasedRatchetTest)
    assert tests[0].name == "test1"
    assert tests[0].pattern == "print\\("

    # Test second test
    assert isinstance(tests[1], TwoPassRatchetTest)
    assert tests[1].name == "test2"
    assert tests[1].first_pass.pattern == "class\\s+\\w+"


def test_create_ratchet_tests_errors():
    """Test error handling in ratchet test creation."""
    # Test invalid two-pass configuration
    with pytest.raises(ConfigError):
        RatchetConfig(
            name="test",
            pattern="print\\(",
            match_examples=["print('Hello')"],
            non_match_examples=["logging.info('Hello')"],
            is_two_pass=True,
            # Missing second_pass_pattern
        )
