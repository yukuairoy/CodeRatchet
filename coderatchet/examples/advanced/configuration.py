"""Example of advanced configuration management."""

from coderatchet.core.config import RatchetConfigManager


def main():
    """Run the example."""
    # Create a config manager
    config_manager = RatchetConfigManager()

    # Add some patterns
    config_manager.add_pattern("TODO", ".*\\.py$")
    config_manager.add_pattern("FIXME", ".*\\.py$")

    # Add some exclusions
    config_manager.add_exclusion(".*\\.pyc$")
    config_manager.add_exclusion(".*/__pycache__/.*")

    # Save the config
    config_manager.save_config("my_config.json")

    # Load the config
    config_manager.load_config("my_config.json")

    # Print the config
    print(config_manager.get_config())


if __name__ == "__main__":
    main()
