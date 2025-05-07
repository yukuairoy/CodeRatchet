# Development Guide

This document provides guidelines for contributing to CodeRatchet.

## Development Environment

### Prerequisites
- Python 3.8 or higher
- Git
- Virtual environment (recommended)

### Setup
1. Clone the repository:
```bash
git clone https://github.com/yukuairoy/coderatchet.git
cd coderatchet
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Install development dependencies:
```bash
pip install -e ".[dev]"
```

4. Install pre-commit hooks:
```bash
pre-commit install
```

## Code Style

### Python Style
Follow PEP 8 guidelines:
- Use 4 spaces for indentation
- Maximum line length of 88 characters
- Use double quotes for strings
- Use snake_case for variables and functions
- Use PascalCase for classes

### Type Hints
Use type hints for all functions and variables:
```python
def process_file(file_path: str, config: Config) -> List[TestFailure]:
    """
    Process a file for ratchet violations.
    
    Args:
        file_path: Path to file
        config: Configuration
        
    Returns:
        List of ratchet failures
    """
    pass
```

### Documentation
Follow Google style docstrings:
```python
def example_function(arg1: str, arg2: int) -> bool:
    """Short description.
    
    Long description.
    
    Args:
        arg1: Description of arg1
        arg2: Description of arg2
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: Description of when raised
    """
    pass
```

## Testing

### Running Tests
```bash
# Run all tests
pytest

# Run specific test
pytest tests/test_core.py

# Run with coverage
pytest --cov=coderatchet
```

### Writing Tests
1. Use descriptive test names
2. Test edge cases
3. Use fixtures for common setup
4. Mock external dependencies

Example:
```python
def test_ratchet_test():
    """Test basic ratchet test functionality."""
    test = RegexBasedRatchetTest(
        name="no_print",
        pattern="print\\(",
        match_examples=["print('test')"],
        non_match_examples=["logger.info('test')"]
    )
    
    assert test.match("print('hello')")
    assert not test.match("logger.info('hello')")
```

## Git Workflow

### Branching
- Use feature branches
- Follow naming convention: `feature/description`
- Keep branches up to date
- Delete merged branches

### Commits
- Write clear commit messages
- Use present tense
- Reference issues
- Keep commits focused

Example:
```
feat: add support for custom patterns

- Add pattern configuration
- Add pattern validation
- Add pattern tests

Closes #123
```

### Pull Requests
1. Create feature branch
2. Make changes
3. Run tests
4. Update documentation
5. Create pull request
6. Address feedback
7. Merge when approved

## Documentation

### Updating Documentation
1. Update docstrings
2. Update README
3. Update API docs
4. Add examples

### Building Documentation
```bash
# Install docs dependencies
pip install -e ".[docs]"

# Build docs
cd docs
make html
```

## Release Process

### Versioning
Follow semantic versioning:
- MAJOR: Breaking changes
- MINOR: New features
- PATCH: Bug fixes

### Release Steps
1. Update version
2. Update changelog
3. Create release branch
4. Run tests
5. Build package
6. Create tag
7. Push to PyPI

## Common Tasks

### Adding New Feature
1. Create feature branch
2. Implement feature
3. Add tests
4. Update docs
5. Create pull request

### Fixing Bug
1. Create bug branch
2. Write failing test
3. Fix bug
4. Verify test
5. Create pull request

### Updating Dependencies
1. Check updates
2. Update requirements
3. Run tests
4. Update docs
5. Create pull request

## Code Review

### Review Checklist
- [ ] Code style
- [ ] Type hints
- [ ] Documentation
- [ ] Tests
- [ ] Performance
- [ ] Security

### Review Process
1. Create pull request
2. Request review
3. Address feedback
4. Update code
5. Get approval
6. Merge

## Getting Help

### Questions
- Check documentation
- Search issues
- Ask in chat
- Create issue

### Reporting Issues
1. Check existing issues
2. Create new issue
3. Provide details
4. Add reproduction steps

## Best Practices

### Code Quality
- Write clean code
- Use type hints
- Add documentation
- Write tests
- Handle errors

### Performance
- Profile code
- Optimize bottlenecks
- Use caching
- Handle large files

### Security
- Validate input
- Handle errors
- Use safe defaults
- Follow best practices

For more information, see the [Testing Guide](../contributing/testing.md).

## Project Structure

The project is organized into the following directories:

- `coderatchet/core/`: Core functionality and base classes
- `coderatchet/examples/`: Example ratchet tests and usage
- `coderatchet/tests/`: Test suite
- `docs/`: Documentation

## Core Components

### Ratchet Tests

The main components are:

```python
def process_file(file_path: str, config: Config) -> List[TestFailure]:
    """Process a single file with the given configuration."""
    pass

def process_files(files: List[Path], config: Config) -> List[TestFailure]:
    """Process multiple files with the given configuration."""
    pass
``` 