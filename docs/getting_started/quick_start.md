# Quick Start Guide

## Basic Usage

1. Install CodeRatchet:
```bash
pip install coderatchet
```

2. Create a configuration file (`coderatchet.yaml`):
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

3. Run CodeRatchet:
```bash
coderatchet check
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

- Read the [Configuration Guide](../core_concepts/configuration.md) for detailed settings
- Check out [Advanced Usage](../advanced/custom_ratchets.md) for custom ratchets
- See [Real-world Examples](../examples/real_world.md) for practical applications

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