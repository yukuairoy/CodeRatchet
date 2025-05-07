# CodeRatchet Examples

This directory contains examples of how to use CodeRatchet in different scenarios.

## Directory Structure

```
examples/
├── basic_usage/         # Basic usage examples
│   ├── basic_ratchets.py
│   └── custom_ratchets.py
├── advanced/            # Advanced usage examples
│   ├── ci_integration.py
│   └── configuration.py
└── configs/             # Configuration examples
    ├── base.yaml        # Base configuration
    ├── strict.yaml      # Strict settings
    ├── relaxed.yaml     # Relaxed settings
    └── custom.yaml      # Custom ratchet settings
```

## Basic Usage

The `basic_usage` directory contains simple examples showing how to:
- Use basic ratchet tests
- Create and use custom ratchet tests
- Run checks on individual files

Example:
```python
from coderatchet.core.ratchet import run_ratchets_on_file
from coderatchet.examples.basic_ratchets import get_basic_ratchets

# Get ratchets
ratchets = get_basic_ratchets()

# Run checks
results = run_ratchets_on_file("your_file.py", ratchets)
```

## Advanced Usage

The `advanced` directory contains examples of more complex scenarios:
- CI/CD integration
- Configuration management
- Custom ratchet implementations

Example:
```python
from coderatchet.core.config import RatchetConfig

# Load configuration
config = RatchetConfig("coderatchet.yaml")

# Get configured ratchets
ratchets = config.get_ratchets()
```

## Configuration Examples

The `configs` directory contains example configuration files:
- `base.yaml`: Default settings
- `strict.yaml`: Strict code quality settings
- `relaxed.yaml`: More permissive settings
- `custom.yaml`: Custom ratchet configurations

To use a configuration:
```bash
python -m coderatchet --config examples/configs/strict.yaml check
```

## Running Examples

To run an example:
```bash
# Basic usage
python examples/basic_usage/basic_ratchets.py

# Advanced usage
python examples/advanced/ci_integration.py
```

## Contributing Examples

When adding new examples:
1. Place them in the appropriate directory
2. Include clear documentation
3. Add example files or data if needed
4. Update this README if necessary 