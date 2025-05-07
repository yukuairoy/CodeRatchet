# Contributing to CodeRatchet

We love your input! We want to make contributing to CodeRatchet as easy and transparent as possible.

## Development Process

1. Fork the repo and create your branch from `main`.
2. Set up your development environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   pip install -e ".[dev]"
   ```
3. Make your changes.
4. Run tests and ensure they pass:
   ```bash
   pytest
   ```
5. Run code quality checks:
   ```bash
   black .
   isort .
   mypy .
   pylint coderatchet
   ```
6. Submit a pull request.

## Pull Request Process

1. Update documentation for any new features.
2. Add tests for new functionality.
3. Update the README.md if needed.
4. The PR will be merged once you have the sign-off of a maintainer.

## Code Style

We use several tools to maintain code quality:

- **Black**: Code formatting
- **isort**: Import sorting
- **mypy**: Type checking
- **pylint**: Code analysis

Configuration for these tools is in `pyproject.toml`.

## Testing

- Write unit tests for new features
- Maintain test coverage above 80%
- Use meaningful test names and docstrings
- Group related tests in test classes

## Documentation

- Keep docstrings up to date
- Follow Google docstring format
- Update relevant documentation files
- Add examples for new features

## Creating Custom Ratchets

When creating new ratchet tests:

1. Follow the pattern in `examples/custom_ratchets.py`
2. Include both match and non-match examples
3. Write thorough tests
4. Document usage and edge cases

## Reporting Bugs

Report bugs by [opening an issue](https://github.com/yukuairoy/CodeRatchet/issues):

1. Describe the bug
2. Include steps to reproduce
3. Show expected vs actual behavior
4. Include relevant code snippets
5. Specify your environment

## Feature Requests

Feature requests are welcome:

1. Check it hasn't been requested before
2. Open an issue describing the feature
3. Explain why it would be useful
4. Provide example usage if possible

## Code of Conduct

Please note that this project is released with a [Code of Conduct](CODE_OF_CONDUCT.md). By participating in this project you agree to abide by its terms.

## License

By contributing, you agree that your contributions will be licensed under the MIT License. 