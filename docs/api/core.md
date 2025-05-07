# Core API Reference

## Ratchet Tests

### RegexBasedRatchetTest

```python
from coderatchet.core.ratchet import RegexBasedRatchetTest

class RegexBasedRatchetTest:
    """A ratchet test that uses regular expressions to match patterns."""
    
    def __init__(
        self,
        name: str,
        pattern: str,
        match_examples: List[str],
        non_match_examples: List[str],
        description: Optional[str] = None,
    ):
        """Initialize the ratchet test.
        
        Args:
            name: Name of the test
            pattern: Regex pattern to match
            match_examples: Examples that should match
            non_match_examples: Examples that should not match
            description: Optional description
        """
```

### TwoPassRatchetTest

```python
from coderatchet.core.ratchet import TwoPassRatchetTest

class TwoPassRatchetTest:
    """A ratchet test that performs two passes over the code."""
    
    def __init__(
        self,
        name: str,
        first_pass: RegexBasedRatchetTest,
        first_pass_failure_to_second_pass_regex_part: Callable[[str], str],
        first_pass_failure_filepath_for_testing: str,
    ):
        """Initialize the two-pass ratchet test.
        
        Args:
            name: Name of the test
            first_pass: First pass ratchet test
            first_pass_failure_to_second_pass_regex_part: Function to generate second pass pattern
            first_pass_failure_filepath_for_testing: Test file path
        """
```

## Configuration

### RatchetConfig

```python
from coderatchet.core.config import RatchetConfig

class RatchetConfig:
    """Configuration for a ratchet rule."""
    
    def __init__(
        self,
        name: str,
        pattern: str,
        match_examples: List[str],
        non_match_examples: List[str],
        description: Optional[str] = None,
        is_two_pass: bool = False,
        second_pass_pattern: Optional[str] = None,
        second_pass_examples: Optional[List[str]] = None,
        second_pass_non_examples: Optional[List[str]] = None,
    ):
        """Initialize the configuration.
        
        Args:
            name: Name of the ratchet rule
            pattern: Regex pattern to match
            match_examples: Examples that should match
            non_match_examples: Examples that should not match
            description: Optional description
            is_two_pass: Whether this is a two-pass ratchet
            second_pass_pattern: Pattern for second pass
            second_pass_examples: Examples for second pass
            second_pass_non_examples: Non-examples for second pass
        """
```

## Utilities

### Pattern Management

```python
from coderatchet.core.utils import join_regex_patterns

def join_regex_patterns(patterns: List[str], join_type: str = "or") -> str:
    """Join multiple regex patterns.
    
    Args:
        patterns: List of regex patterns
        join_type: How to join patterns ("or" or "and")
        
    Returns:
        Combined pattern string
    """
```

### File Operations

```python
from coderatchet.core.utils import get_python_files

def get_python_files(
    directory: Union[str, Path],
    exclude_patterns: Optional[List[str]] = None,
) -> List[Path]:
    """Get all Python files in a directory.
    
    Args:
        directory: Directory to search
        exclude_patterns: Patterns to exclude
        
    Returns:
        List of Python file paths
    """
```

## Git Integration

### Recent Failures

```python
from coderatchet.core.recent_failures import get_recently_broken_ratchets

def get_recently_broken_ratchets(
    ratchets: List[RatchetTest],
    base_commit: Optional[str] = None,
) -> Dict[str, List[TestFailure]]:
    """Get ratchets that were recently broken.
    
    Args:
        ratchets: List of ratchet tests
        base_commit: Base commit to compare against
        
    Returns:
        Dict mapping file paths to failures
    """
```

### Comparison

```python
from coderatchet.core.comparison import compare_ratchets

def compare_ratchets(
    ratchets: List[RatchetTest],
    base_commit: str,
    current_commit: Optional[str] = None,
) -> Dict[str, Dict[str, int]]:
    """Compare ratchet violations between commits.
    
    Args:
        ratchets: List of ratchet tests
        base_commit: Base commit
        current_commit: Current commit (default: HEAD)
        
    Returns:
        Dict with violation counts by file
    """
```

## Examples

### Basic Usage

```python
from coderatchet.core.ratchet import RegexBasedRatchetTest
from coderatchet.core.config import RatchetConfig

# Create a ratchet test
ratchet = RegexBasedRatchetTest(
    name="no_print",
    pattern=r"print\(",
    match_examples=["print('Hello')"],
    non_match_examples=["logger.info('Hello')"],
)

# Create configuration
config = RatchetConfig(
    name="no_print",
    pattern=r"print\(",
    match_examples=["print('Hello')"],
    non_match_examples=["logger.info('Hello')"],
)
```

### Advanced Usage

```python
from coderatchet.core.ratchet import TwoPassRatchetTest
from coderatchet.core.recent_failures import get_recently_broken_ratchets

# Create a two-pass ratchet
ratchet = TwoPassRatchetTest(
    name="function_length",
    first_pass=RegexBasedRatchetTest(
        name="function_def",
        pattern=r"def\s+\w+\s*\([^)]*\)\s*:",
        match_examples=["def foo():"],
        non_match_examples=["class Foo:"],
    ),
    first_pass_failure_to_second_pass_regex_part=lambda f: r"^(?!\s*$).+$",
    first_pass_failure_filepath_for_testing="test.py",
)

# Check for recent failures
failures = get_recently_broken_ratchets([ratchet])
```

## Error Handling

All functions may raise:
- `ValueError`: For invalid input
- `FileNotFoundError`: For missing files
- `ConfigError`: For configuration issues
- `GitError`: For git-related issues

## Best Practices

1. **Pattern Design**
   - Use non-capturing groups where possible
   - Test patterns thoroughly
   - Include edge cases in examples

2. **Configuration**
   - Keep configurations in version control
   - Use environment variables for sensitive values
   - Document non-obvious settings

3. **Error Handling**
   - Always catch and handle exceptions
   - Provide meaningful error messages
   - Log errors appropriately

4. **Performance**
   - Use specific patterns over general ones
   - Consider using TwoPassRatchetTest for complex cases
   - Profile and optimize as needed 

### Base Classes

#### RatchetTest

The base class for all ratchet tests.

```python
class RatchetTest:
    def collect_failures_from_lines(
        self,
        lines: List[str],
        file_path: str
    ) -> List[TestFailure]:
        """Collect failures from a list of lines."""
        pass

    def get_total_count_from_files(
        self,
        files: List[Path]
    ) -> Dict[str, List[TestFailure]]:
        """Get total count of failures from files."""
        pass
``` 