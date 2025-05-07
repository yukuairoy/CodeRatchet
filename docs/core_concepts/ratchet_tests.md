# Ratchet Tests

Ratchet tests are the core concept in CodeRatchet. They allow you to enforce code quality standards by detecting and preventing specific patterns in your code.

## Types of Ratchet Tests

### RegexBasedRatchetTest

The most basic type of ratchet test that uses regular expressions to match patterns:

```python
from coderatchet.core.ratchet import RegexBasedRatchetTest

ratchet = RegexBasedRatchetTest(
    name="no_print",
    pattern=r"print\(",
    match_examples=["print('Hello')"],
    non_match_examples=["logger.info('Hello')"],
)
```

### TwoPassRatchetTest

A more advanced ratchet test that performs two passes over the code:

```python
from coderatchet.core.ratchet import TwoPassRatchetTest

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
```

## Creating Ratchet Tests

### Basic Requirements

Every ratchet test requires:
- A unique name
- A pattern to match
- Examples that should match
- Examples that should not match

### Pattern Design

When designing patterns:
- Use non-capturing groups where possible
- Test patterns thoroughly
- Include edge cases in examples
- Consider performance implications

### Example Patterns

Common patterns include:
- Function definitions: `r"def\s+\w+\s*\([^)]*\)\s*:"`
- Print statements: `r"print\("`
- TODO comments: `r"#\s*TODO"`
- Magic numbers: `r"\b\d{4,}\b"`

## Running Tests

### Basic Usage

```python
# Run on a single file
results = ratchet.check_file("your_file.py")

# Run on multiple files
results = ratchet.check_files(["file1.py", "file2.py"])

# Run on a directory
results = ratchet.check_directory("src/")
```

### Configuration Options

Tests can be configured with:
- `exclude_test_files`: Skip test files
- `include_file_regex`: Only check matching files
- `description`: Add a description
- `allowed_count`: Set violation threshold

## Best Practices

1. **Pattern Design**
   - Keep patterns simple and focused
   - Use clear, descriptive names
   - Document complex patterns
   - Test edge cases

2. **Configuration**
   - Set appropriate thresholds
   - Use file exclusions wisely
   - Document configuration choices
   - Version control configurations

3. **Maintenance**
   - Review patterns regularly
   - Update examples as needed
   - Monitor performance
   - Document changes

## Common Use Cases

1. **Code Style**
   - Enforce naming conventions
   - Prevent specific patterns
   - Ensure consistent formatting

2. **Code Quality**
   - Limit function length
   - Prevent magic numbers
   - Enforce documentation

3. **Security**
   - Prevent sensitive data
   - Block dangerous patterns
   - Enforce best practices

## Advanced Topics

- [Custom Ratchets](../advanced/custom_ratchets.md)
- [CI/CD Integration](../advanced/ci_integration.md)
- [Performance Tuning](../troubleshooting/performance.md) 