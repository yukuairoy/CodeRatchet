# Quick Start Guide

This guide will help you get started with CodeRatchet quickly.

## Installation

```bash
pip install coderatchet
```

## Basic Usage

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

## Example: Preventing Print Statements

Here's a simple example to prevent print statements in your code:

```python
from coderatchet.core.ratchet import RegexBasedRatchetTest

# Create a ratchet test
ratchet = RegexBasedRatchetTest(
    name="no_print",
    pattern=r"print\(",
    match_examples=["print('Hello')"],
    non_match_examples=["logger.info('Hello')"],
)

# Run the test
results = ratchet.check_file("your_file.py")
```

## Example: Function Length Check

Check function length with a two-pass ratchet:

```python
from coderatchet.core.ratchet import TwoPassRatchetTest

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

# Run the test
results = ratchet.check_file("your_file.py")
```

## Example Ratchets

### Basic Ratchets

CodeRatchet comes with several built-in ratchets:

1. No Print Statements
```python
# Bad
print("Debug message")

# Good
logger.info("Debug message")
```

2. No Debug Comments
```python
# Bad
# TODO: Fix this later
# FIXME: Temporary hack

# Good
# Implementation note: Using dictionary for O(1) lookup
```

3. No Bare Except
```python
# Bad
try:
    do_something()
except:
    pass

# Good
try:
    do_something()
except ValueError:
    handle_error()
```

### Custom Ratchets

You can create custom ratchets for specific needs:

1. Function Length
```python
# Bad
def long_function():
    # ... more than 50 lines ...
    pass

# Good
def short_function():
    # ... less than 50 lines ...
    pass
```

2. Complex Conditions
```python
# Bad
if x > 0 and y < 10 and z == 5:
    pass

# Good
is_valid = x > 0 and y < 10
if is_valid and z == 5:
    pass
```

## Next Steps

- Read the [Basic Usage](basic_usage.md) guide for more details
- Check out [Core Concepts](core_concepts/ratchet_tests.md) to understand ratchet tests
- Explore [Configuration](core_concepts/configuration.md) options
- See [Examples](../examples/README.md) for more use cases

## Common Commands

| Command | Description |
|---------|-------------|
| `coderatchet check` | Run ratchet checks on current code |
| `coderatchet history` | View violation history |
| `coderatchet config` | Show current configuration |
| `coderatchet --help` | Show all available commands |

## Troubleshooting

If you encounter any issues:

1. Check your configuration file syntax
2. Verify git is properly initialized
3. Ensure all required files are committed

For more help, see the [Troubleshooting Guide](../troubleshooting/common_issues.md). 