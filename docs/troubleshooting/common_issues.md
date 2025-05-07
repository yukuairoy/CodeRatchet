# Common Issues and Solutions

This guide covers common issues you might encounter when using CodeRatchet and how to resolve them.

## Configuration Issues

### Invalid Configuration File

**Symptoms:**
- Configuration loading fails
- Ratchet tests don't run as expected

**Solutions:**
1. Check your YAML syntax
2. Verify all required fields are present
3. Use the Python API to validate your configuration:
```python
from coderatchet.core.config import RatchetConfigManager

try:
    config = RatchetConfigManager("coderatchet.yaml")
    print("Configuration is valid")
except Exception as e:
    print(f"Configuration error: {e}")
```

### Missing Configuration

**Symptoms:**
- Default configuration is used instead of custom settings
- Ratchet tests don't match your requirements

**Solutions:**
1. Ensure your configuration file exists
2. Check the file path in your code:
```python
from coderatchet.core.config import RatchetConfigManager

# Use absolute path if needed
config = RatchetConfigManager("/absolute/path/to/coderatchet.yaml")
```

## Git Integration Issues

### Git Repository Not Found

**Symptoms:**
- Git-related operations fail
- History comparison doesn't work

**Solutions:**
1. Ensure you're in a git repository
2. Check git initialization:
```python
import subprocess

try:
    subprocess.check_call(["git", "rev-parse", "--git-dir"])
    print("Git repository found")
except subprocess.CalledProcessError:
    print("Not in a git repository")
```

### Commit History Issues

**Symptoms:**
- Can't compare with previous commits
- History view is empty

**Solutions:**
1. Check if you have commits:
```python
import subprocess

try:
    result = subprocess.check_output(["git", "log", "--oneline"])
    print("Commit history found")
except subprocess.CalledProcessError:
    print("No commit history")
```

2. Verify commit references:
```python
from coderatchet.core.comparison import compare_ratchets

try:
    results = compare_ratchets("HEAD~1", "HEAD")
    print("Comparison successful")
except Exception as e:
    print(f"Comparison failed: {e}")
```

## Pattern Matching Issues

### Invalid Regex Patterns

**Symptoms:**
- Pattern compilation fails
- Unexpected matches or non-matches

**Solutions:**
1. Test your patterns:
```python
import re

try:
    pattern = re.compile("your_pattern")
    print("Pattern is valid")
except re.error as e:
    print(f"Invalid pattern: {e}")
```

2. Use example validation:
```python
from coderatchet.core.ratchet import RegexBasedRatchetTest

ratchet = RegexBasedRatchetTest(
    name="test",
    pattern="your_pattern",
    match_examples=["should match"],
    non_match_examples=["should not match"]
)
```

### Performance Issues

**Symptoms:**
- Slow pattern matching
- High memory usage

**Solutions:**
1. Optimize your patterns
2. Use more specific patterns
3. Consider using two-pass ratchets for complex cases

## File Access Issues

### Permission Denied

**Symptoms:**
- Can't read files
- Operations fail with permission errors

**Solutions:**
1. Check file permissions
2. Use try-except blocks:
```python
from coderatchet.core.ratchet import run_ratchets_on_file

try:
    results = run_ratchets_on_file("your_file.py", ratchets)
except PermissionError:
    print("Permission denied")
```

### File Not Found

**Symptoms:**
- Files can't be found
- Operations fail with file not found errors

**Solutions:**
1. Verify file paths
2. Use absolute paths if needed
3. Check file existence:
```python
from pathlib import Path

file_path = Path("your_file.py")
if file_path.exists():
    print("File found")
else:
    print("File not found")
```

## Getting Help

If you encounter issues not covered here:

1. Check the [API Reference](../api/core.md)
2. Look at the [Examples](../examples/README.md)
3. Review the [Core Concepts](../core_concepts/ratchet_tests.md)
4. Open an issue on GitHub 