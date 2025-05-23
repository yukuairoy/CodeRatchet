# CodeRatchet

A Python tool for enforcing code quality standards through ratchet tests. CodeRatchet helps teams maintain and improve code quality by preventing the introduction of specific patterns or practices that have been identified as problematic. It's particularly useful for gradually improving legacy codebases by enforcing stricter standards over time.

## Features

- **Regex-based Pattern Matching**: Define code patterns to detect and prevent
- **Two-Pass Analysis**: Complex pattern matching with context awareness
- **Git Integration**: Track violations across commits and branches
- **CI/CD Support**: Easy integration with continuous integration pipelines
- **Customizable Rules**: Create and share custom ratchet tests
- **Performance Optimized**: Fast analysis even on large codebases

## Installation

```bash
pip install coderatchet
```

## Quick Start

1. Create a configuration file (`coderatchet.yaml`):
```yaml
ratchets:
  basic:
    enabled: true
    config: {}
  custom:
    enabled: true
    config:
      function_length:
        max_lines: 50
```

2. Use CodeRatchet in your Python code:
```python
from coderatchet.core.config import RatchetConfigManager
from coderatchet.core.ratchet import run_ratchets_on_file

# Initialize configuration
config = RatchetConfigManager("coderatchet.yaml")

# Get configured ratchets
ratchets = config.get_ratchets()

# Run checks on a file
results = run_ratchets_on_file("your_file.py", ratchets)
```

## Documentation

- [Getting Started](docs/getting_started/quick_start.md)
- [Core Concepts](docs/core_concepts/ratchet_tests.md)
- [Configuration](docs/core_concepts/configuration.md)
- [Advanced Usage](docs/advanced/custom_ratchets.md)
- [API Reference](docs/api/core.md)

## Examples

Check out the [examples](coderatchet/examples) directory for:
- Basic usage examples
- Custom ratchet tests
- Advanced configurations
- Real-world scenarios

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- [Documentation](docs/)
- [Issue Tracker](https://github.com/yukuairoy/CodeRatchet/issues)
