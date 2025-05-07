# CodeRatchet

A Python tool for enforcing code quality standards through ratchet tests.

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

2. Run CodeRatchet:
```bash
coderatchet check
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
- [Discussions](https://github.com/yukuairoy/CodeRatchet/discussions)

## Acknowledgments

Thanks to all contributors who have helped shape CodeRatchet! 