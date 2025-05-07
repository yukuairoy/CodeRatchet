# Testing Guide

This document provides guidelines for testing CodeRatchet.

## Test Structure

### Directory Structure
```
tests/
├── __init__.py
├── conftest.py
├── test_core.py
├── test_cli.py
├── test_config.py
├── test_security.py
└── test_real_world_scenarios.py
```

### Test Categories
1. Unit Tests
2. Integration Tests
3. Security Tests
4. Performance Tests
5. Real-world Scenarios

## Writing Tests

### Basic Test Structure
```python
def test_functionality():
    """Test description."""
    # Setup
    test = RegexBasedRatchetTest(
        name="test",
        pattern="pattern",
        match_examples=["match"],
        non_match_examples=["no match"]
    )
    
    # Test
    result = test.match("test")
    
    # Assert
    assert result is True
```

### Using Fixtures
```python
@pytest.fixture
def ratchet_test():
    """Create ratchet test fixture."""
    return RegexBasedRatchetTest(
        name="test",
        pattern="pattern",
        match_examples=["match"],
        non_match_examples=["no match"]
    )

def test_with_fixture(ratchet_test):
    """Test using fixture."""
    assert ratchet_test.match("match")
```

### Mocking
```python
from unittest.mock import patch

def test_with_mock():
    """Test with mock."""
    with patch("subprocess.check_output") as mock:
        mock.return_value = b"test"
        result = get_git_history()
        assert result == "test"
```

## Test Types

### Unit Tests
Test individual components:
```python
def test_ratchet_test():
    """Test ratchet test functionality."""
    test = RegexBasedRatchetTest(
        name="no_print",
        pattern="print\\(",
        match_examples=["print('test')"],
        non_match_examples=["logger.info('test')"]
    )
    
    assert test.match("print('hello')")
    assert not test.match("logger.info('hello')")
```

### Integration Tests
Test component interactions:
```python
def test_git_integration(tmp_path):
    """Test git integration."""
    # Setup git repository
    subprocess.run(["git", "init"], cwd=tmp_path)
    
    # Create test file
    test_file = tmp_path / "test.py"
    test_file.write_text("print('test')")
    
    # Add and commit
    subprocess.run(["git", "add", "."], cwd=tmp_path)
    subprocess.run(["git", "commit", "-m", "test"], cwd=tmp_path)
    
    # Test
    failures = get_recently_broken_ratchets()
    assert len(failures) == 1
```

### Security Tests
Test security features:
```python
def test_command_injection():
    """Test command injection prevention."""
    with patch("subprocess.check_output") as mock:
        mock.return_value = b"test"
        result = _get_git_history("; rm -rf /")
        assert result == []
```

### Performance Tests
Test performance:
```python
def test_performance(benchmark):
    """Test performance."""
    @benchmark
    def test():
        return get_recently_broken_ratchets(limit=1000)
    
    assert test() is not None
```

### Real-world Scenarios
Test real-world usage:
```python
def test_complex_repository(tmp_path):
    """Test complex repository scenario."""
    # Setup complex repository
    setup_complex_repository(tmp_path)
    
    # Test various scenarios
    test_branch_merges(tmp_path)
    test_file_renames(tmp_path)
    test_multiple_commits(tmp_path)
```

## Test Best Practices

### 1. Test Organization
- Group related tests
- Use descriptive names
- Follow consistent structure
- Use appropriate fixtures

### 2. Test Coverage
- Test all code paths
- Test edge cases
- Test error conditions
- Test performance

### 3. Test Data
- Use realistic data
- Include edge cases
- Use appropriate size
- Clean up after tests

### 4. Test Maintenance
- Keep tests up to date
- Remove obsolete tests
- Fix failing tests
- Add new tests

## Running Tests

### Basic Commands
```bash
# Run all tests
pytest

# Run specific test
pytest tests/test_core.py

# Run with coverage
pytest --cov=coderatchet

# Run with debug
pytest --pdb
```

### Advanced Commands
```bash
# Run specific category
pytest -m "integration"

# Run with parallel
pytest -n auto

# Run with profiling
pytest --profile

# Run with verbose
pytest -v
```

## Test Configuration

### pytest.ini
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --cov=coderatchet
```

### conftest.py
```python
import pytest
from pathlib import Path

@pytest.fixture
def tmp_path(tmp_path):
    """Create temporary directory."""
    path = Path(tmp_path)
    yield path
    # Cleanup
```

## Test Examples

### Basic Test
```python
def test_basic_functionality():
    """Test basic functionality."""
    # Setup
    test = create_test()
    
    # Test
    result = test.function()
    
    # Assert
    assert result == expected
```

### Complex Test
```python
def test_complex_scenario(tmp_path):
    """Test complex scenario."""
    # Setup
    setup_repository(tmp_path)
    create_files(tmp_path)
    make_commits(tmp_path)
    
    # Test
    result = run_checks(tmp_path)
    
    # Assert
    assert_result(result)
    
    # Cleanup
    cleanup(tmp_path)
```

### Performance Test
```python
def test_performance(benchmark):
    """Test performance."""
    # Setup
    data = create_large_dataset()
    
    # Test
    @benchmark
    def test():
        return process_data(data)
    
    # Assert
    assert test() is not None
    assert benchmark.stats.stats.mean < 1.0
```

## Test Maintenance

### 1. Regular Updates
- Update tests with code changes
- Add tests for new features
- Remove obsolete tests
- Fix failing tests

### 2. Test Review
- Review test coverage
- Review test quality
- Review test performance
- Review test maintenance

### 3. Test Documentation
- Document test purpose
- Document test setup
- Document test cases
- Document test results

For more information, see the [Development Guide](../contributing/development.md). 