# Code Style Guide

This document outlines the coding standards and style guidelines for CodeRatchet.

## Python Style

### General Guidelines
- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) for Python code style
- Use 4 spaces for indentation (no tabs)
- Maximum line length of 88 characters
- Use double quotes for strings consistently
- Use snake_case for variables and functions
- Use PascalCase for classes
- Use UPPER_CASE for constants

### Imports
```python
# Standard library imports
import os
import sys
from pathlib import Path
from typing import List, Optional

# Third-party imports
import pytest
from dataclasses import dataclass

# Local imports
from coderatchet.core import RatchetTest
from coderatchet.utils import validate_pattern
```

### Type Hints
Use type hints for all functions and variables:
```python
def process_file(
    file_path: str,
    config: Config
) -> List[TestFailure]:
    """Process a single file."""
    pass

def process_files(
    files: List[Path],
    config: Config
) -> List[TestFailure]:
    """Process multiple files."""
    pass
```

### Documentation
Follow Google style docstrings:
```python
def example_function(arg1: str, arg2: int) -> bool:
    """Short description.
    
    Long description with more details about the function's purpose
    and behavior.
    
    Args:
        arg1: Description of first argument
        arg2: Description of second argument
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When invalid input is provided
        RuntimeError: When operation fails
    """
    pass
```

## Git Integration

### Command Execution
Use subprocess safely:
```python
def run_git_command(args: List[str], cwd: Optional[str] = None) -> str:
    """Run git command safely.
    
    Args:
        args: Git command arguments
        cwd: Working directory
        
    Returns:
        Command output
        
    Raises:
        GitCommandError: When command fails
    """
    try:
        result = subprocess.run(
            ['git'] + args,
            capture_output=True,
            text=True,
            check=True,
            cwd=cwd
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise GitCommandError(f"Git command failed: {e.stderr}")
```

### Path Handling
Use pathlib for path operations:
```python
def resolve_path(path: Union[str, Path]) -> Path:
    """Resolve path safely.
    
    Args:
        path: Path to resolve
        
    Returns:
        Resolved Path object
    """
    return Path(path).resolve()
```

## Error Handling

### Custom Exceptions
Define clear exception hierarchy:
```python
class RatchetError(Exception):
    """Base class for ratchet-related errors."""
    pass

class GitCommandError(RatchetError):
    """Error raised when git commands fail."""
    pass

class PatternError(RatchetError):
    """Error raised for invalid patterns."""
    pass
```

### Error Messages
Provide clear error messages:
```python
def validate_pattern(pattern: str) -> None:
    """Validate regex pattern.
    
    Args:
        pattern: Pattern to validate
        
    Raises:
        PatternError: When pattern is invalid
    """
    try:
        re.compile(pattern)
    except re.error as e:
        raise PatternError(f"Invalid pattern: {e}")
```

## Configuration

### Default Configuration
```yaml
# Default configuration values
ratchets: []  # List of ratchet tests

cache:
  enabled: true
  size: 1000
  directory: .coderatchet/cache
  ttl: 3600  # 1 hour

processing:
  max_workers: 4
  max_file_size: 1000000  # 1MB
  timeout: 300  # 5 minutes
  retries: 3

logging:
  level: INFO
  file: coderatchet.log
  format: "%(asctime)s - %(levelname)s - %(message)s"
```

### Configuration Validation
```python
def validate_config(config: Dict) -> None:
    """Validate configuration structure and values.
    
    Args:
        config: Configuration dictionary
        
    Raises:
        ConfigError: When configuration is invalid
    """
    # Validate required sections
    required_sections = ['ratchets', 'cache', 'processing', 'logging']
    for section in required_sections:
        if section not in config:
            raise ConfigError(f"Missing required section: {section}")
    
    # Validate ratchets
    if not isinstance(config['ratchets'], list):
        raise ConfigError("ratchets must be a list")
    
    for ratchet in config['ratchets']:
        validate_ratchet_config(ratchet)
    
    # Validate cache
    validate_cache_config(config['cache'])
    
    # Validate processing
    validate_processing_config(config['processing'])
    
    # Validate logging
    validate_logging_config(config['logging'])

def validate_ratchet_config(ratchet: Dict) -> None:
    """Validate ratchet configuration.
    
    Args:
        ratchet: Ratchet configuration dictionary
        
    Raises:
        ConfigError: When ratchet configuration is invalid
    """
    required_fields = ['name', 'pattern', 'match_examples', 'non_match_examples']
    for field in required_fields:
        if field not in ratchet:
            raise ConfigError(f"Missing required field in ratchet: {field}")
    
    if not isinstance(ratchet['match_examples'], list):
        raise ConfigError("match_examples must be a list")
    
    if not isinstance(ratchet['non_match_examples'], list):
        raise ConfigError("non_match_examples must be a list")
    
    try:
        re.compile(ratchet['pattern'])
    except re.error as e:
        raise ConfigError(f"Invalid pattern: {e}")
```

### Configuration Examples

#### Basic Configuration
```yaml
# Basic configuration for print statement detection
ratchets:
  - name: no_print_statements
    pattern: print\(
    match_examples:
      - "print('Hello')"
      - "print(f'Hello {name}')"
    non_match_examples:
      - "logger.info('Hello')"
      - "print = 'test'"

cache:
  enabled: true
  size: 100

processing:
  max_workers: 2
  max_file_size: 500000
```

#### Security Configuration
```yaml
# Security-focused configuration
ratchets:
  - name: no_hardcoded_secrets
    pattern: (password|secret|key)\s*=\s*['\"][^'\"]+['\"]
    match_examples:
      - "password = 'secret123'"
      - "api_key = \"sk_test_123\""
    non_match_examples:
      - "password = None"
      - "key_length = 32"
  
  - name: no_unsafe_eval
    pattern: eval\(
    match_examples:
      - "eval(user_input)"
    non_match_examples:
      - "safe_eval('1 + 1')"

cache:
  enabled: true
  size: 1000
  ttl: 1800  # 30 minutes

processing:
  max_workers: 4
  max_file_size: 1000000
  timeout: 600  # 10 minutes
```

#### Performance Configuration
```yaml
# Performance-optimized configuration
ratchets:
  - name: no_nested_loops
    pattern: for\s+.*\s+in\s+.*:\s*\n\s*for\s+.*\s+in\s+.*:
    match_examples:
      - "for i in range(10):\n    for j in range(10):"
    non_match_examples:
      - "for i in range(10):\n    print(i)"
  
  - name: no_large_files
    pattern: ^.{10000,}$
    match_examples:
      - "very long line..."
    non_match_examples:
      - "normal line"

cache:
  enabled: true
  size: 5000
  directory: .coderatchet/cache
  ttl: 7200  # 2 hours

processing:
  max_workers: 8
  max_file_size: 2000000  # 2MB
  timeout: 900  # 15 minutes
  retries: 5
```

#### Development Configuration
```yaml
# Development environment configuration
ratchets:
  - name: no_debug_code
    pattern: (debugger|pdb\.set_trace|import\s+pdb)
    match_examples:
      - "import pdb; pdb.set_trace()"
      - "debugger;"
    non_match_examples:
      - "import logging"
  
  - name: no_todo_comments
    pattern: #\s*TODO
    match_examples:
      - "# TODO: Fix this"
    non_match_examples:
      - "# This is done"

cache:
  enabled: false  # Disable caching during development

processing:
  max_workers: 2
  max_file_size: 1000000
  timeout: 300
  retries: 1

logging:
  level: DEBUG
  file: coderatchet_dev.log
  format: "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
```

### Configuration Classes
```python
@dataclass
class Config:
    """Main configuration class."""
    ratchets: List[RatchetConfig]
    cache: CacheConfig
    processing: ProcessingConfig
    logging: LoggingConfig
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Config':
        """Create Config from dictionary.
        
        Args:
            data: Configuration dictionary
            
        Returns:
            Config object
            
        Raises:
            ConfigError: When configuration is invalid
        """
        validate_config(data)
        return cls(
            ratchets=[RatchetConfig(**r) for r in data['ratchets']],
            cache=CacheConfig(**data['cache']),
            processing=ProcessingConfig(**data['processing']),
            logging=LoggingConfig(**data['logging'])
        )
    
    def to_dict(self) -> Dict:
        """Convert Config to dictionary.
        
        Returns:
            Configuration dictionary
        """
        return {
            'ratchets': [asdict(r) for r in self.ratchets],
            'cache': asdict(self.cache),
            'processing': asdict(self.processing),
            'logging': asdict(self.logging)
        }
```

## Testing

### Test Structure
Follow consistent test structure:
```python
def test_functionality():
    """Test description."""
    # Setup
    test = create_test()
    
    # Test
    result = test.function()
    
    # Assert
    assert result == expected
```

### Test Naming
Use descriptive test names:
```python
def test_ratchet_test_matches_print_statement():
    """Test that ratchet test matches print statements."""
    pass

def test_git_command_handles_error():
    """Test that git command handles errors properly."""
    pass
```

## Performance

### Caching
Use caching appropriately:
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_git_history(since_commit: Optional[str] = None) -> List[CommitInfo]:
    """Get git commit history with caching."""
    pass
```

### Batch Processing
Process files in batches:
```python
def process_files(files: List[Path], config: Config) -> List[TestFailure]:
    """Process multiple files efficiently."""
    with ThreadPoolExecutor(max_workers=config.processing.max_workers) as executor:
        futures = [
            executor.submit(process_file, file, config)
            for file in files
        ]
        return [f.result() for f in futures]
```

## Security

### Input Validation
Validate all inputs:
```python
def validate_input(input_str: str) -> str:
    """Validate and sanitize input.
    
    Args:
        input_str: Input to validate
        
    Returns:
        Sanitized input
        
    Raises:
        ValueError: When input is invalid
    """
    if not input_str or not input_str.strip():
        raise ValueError("Input cannot be empty")
    return input_str.strip()
```

### Command Safety
Execute commands safely:
```python
def safe_command_execution(command: List[str]) -> str:
    """Execute command safely.
    
    Args:
        command: Command to execute
        
    Returns:
        Command output
        
    Raises:
        RuntimeError: When command fails
    """
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            shell=False
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Command failed: {e.stderr}")
```

## Best Practices

### 1. Code Organization
- Group related functionality
- Use appropriate abstractions
- Keep functions focused
- Follow single responsibility principle

### 2. Error Handling
- Use specific exceptions
- Provide clear error messages
- Handle errors gracefully
- Log errors appropriately

### 3. Performance
- Use caching when appropriate
- Process in batches
- Optimize critical paths
- Monitor resource usage

### 4. Security
- Validate all inputs
- Execute commands safely
- Handle sensitive data
- Follow security best practices

### 5. Testing
- Write comprehensive tests
- Test edge cases
- Use appropriate fixtures
- Mock external dependencies

For more information, see the [Development Guide](../contributing/development.md) and [Testing Guide](../contributing/testing.md). 