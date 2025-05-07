# Custom Ratchets

This guide explains how to create and use custom ratchet tests in CodeRatchet.

## Types of Custom Ratchets

### 1. RegexBasedRatchetTest

The simplest form of custom ratchet that uses regular expressions to match patterns:

```python
from coderatchet.core.ratchet import RegexBasedRatchetTest

ratchet = RegexBasedRatchetTest(
    name="no_hardcoded_secrets",
    pattern=r"(?i)(?:password|secret|key|token)\s*=\s*['\"][^'\"]+['\"]",
    match_examples=[
        "password = 'secret123'",
        "API_KEY = 'abc123xyz'",
    ],
    non_match_examples=[
        "password = get_password()",
        "API_KEY = os.environ['API_KEY']",
    ],
)
```

### 2. TwoPassRatchetTest

A more complex ratchet that performs two passes over the code:

```python
from coderatchet.core.ratchet import TwoPassRatchetTest, RegexBasedRatchetTest

ratchet = TwoPassRatchetTest(
    name="function_length",
    first_pass=RegexBasedRatchetTest(
        name="function_def",
        pattern=r"def\s+\w+\s*\([^)]*\)\s*:",
        match_examples=["def foo():", "def bar(x, y):"],
        non_match_examples=["class Foo:", "async def foo():"],
    ),
    first_pass_failure_to_second_pass_regex_part=lambda f: r"^(?!\s*$).+$",
    first_pass_failure_filepath_for_testing="test.py",
)
```

## Configuration

### YAML Configuration

```yaml
ratchets:
  custom:
    enabled: true
    config:
      no_hardcoded_secrets:
        enabled: true
        severity: high
      function_length:
        enabled: true
        max_lines: 50
```

### Python Configuration

```python
from coderatchet.core.config import RatchetConfig

config = RatchetConfig(
    name="custom_ratchets",
    pattern=r"your_pattern_here",
    match_examples=["example1", "example2"],
    non_match_examples=["non_example1", "non_example2"],
    description="Description of your custom ratchet",
)
```

## Best Practices

1. **Pattern Design**
   - Make patterns specific and targeted
   - Use non-capturing groups where possible
   - Test patterns thoroughly
   - Document edge cases

2. **Examples**
   - Include both positive and negative examples
   - Cover edge cases
   - Document why certain examples match/don't match
   - Keep examples up to date

3. **Testing**
   - Write unit tests for your ratchets
   - Test with real code samples
   - Verify performance impact
   - Document test cases

## Advanced Examples

### 1. Complex Pattern Matching

```python
from coderatchet.core.ratchet import RegexBasedRatchetTest

ratchet = RegexBasedRatchetTest(
    name="no_complex_conditions",
    pattern=r"if\s+[^:]+(?:and|or)[^:]+(?:and|or)[^:]+:",
    match_examples=[
        "if x > 0 and y < 10 and z == 5:",
        "if a or b or c:",
    ],
    non_match_examples=[
        "if x > 0 and y < 10:",
        "if condition:",
    ],
)
```

### 2. Multi-line Pattern Matching

```python
from coderatchet.core.ratchet import TwoPassRatchetTest

ratchet = TwoPassRatchetTest(
    name="class_too_many_methods",
    first_pass=RegexBasedRatchetTest(
        name="class_def",
        pattern=r"class\s+\w+[^:]*:",
        match_examples=["class MyClass:", "class Test(BaseClass):"],
        non_match_examples=["# class Comment:", "string_with_class = 'class'"],
    ),
    first_pass_failure_to_second_pass_regex_part=lambda f: r"def\s+\w+\s*\(",
)
```

## Integration with Git

Custom ratchets can be integrated with git hooks:

```python
from coderatchet.core.git import GitHook

hook = GitHook(
    name="pre-commit",
    ratchets=[your_custom_ratchet],
    on_failure="block",
)
```

## Troubleshooting

Common issues and solutions:

1. **Pattern Not Matching**
   - Check regex syntax
   - Verify pattern against examples
   - Use regex testing tools

2. **Performance Issues**
   - Optimize regex patterns
   - Use non-capturing groups
   - Consider using TwoPassRatchetTest

3. **False Positives**
   - Make patterns more specific
   - Add more non_match_examples
   - Document edge cases

## Next Steps

- Read the [API Reference](../api/core.md)
- Check out [Real-world Examples](../examples/real_world.md)
- Contribute to [Development](../contributing/development.md) 