# Configuration

CodeRatchet uses YAML configuration files to define ratchet tests and their settings.

## Basic Configuration

A basic configuration file (`coderatchet.yaml`):

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

## Configuration Structure

### Basic Options

```yaml
ratchets:
  basic:
    enabled: true  # Enable/disable basic ratchets
    config: {}     # Basic ratchet configuration
  custom:
    enabled: true  # Enable/disable custom ratchets
    config:        # Custom ratchet configuration
      function_length:
        max_lines: 50
```

### Git Options

```yaml
git:
  base_branch: main           # Base branch for comparison
  ignore_patterns:            # Patterns to ignore in git operations
    - "*.pyc"
    - "__pycache__/"
    - "venv/"
```

### CI Options

```yaml
ci:
  fail_on_violations: true    # Whether to fail CI on violations
  report_format: text         # Output format (text/json)
  check_all_files: false      # Check all files or just changed ones
  exclude_patterns:           # Additional patterns to exclude
    - "tests/"
    - "docs/"
```

## Ratchet Configuration

### Basic Ratchet

```yaml
ratchets:
  basic:
    enabled: true
    config:
      no_print:
        pattern: "print\\("
        match_examples:
          - "print('Hello')"
        non_match_examples:
          - "logger.info('Hello')"
```

### Two-Pass Ratchet

```yaml
ratchets:
  custom:
    enabled: true
    config:
      function_length:
        is_two_pass: true
        first_pass:
          pattern: "def\\s+\\w+\\s*\\([^)]*\\)\\s*:"
          match_examples:
            - "def foo():"
          non_match_examples:
            - "class Foo:"
        second_pass:
          pattern: "^(?!\\s*$).+$"
```

## File Exclusion

Configure file exclusions in `ratchet_excluded.txt`:

```
# Exclude patterns
*.pyc
__pycache__
venv/
!important.py
test2.py
```

## Environment Variables

CodeRatchet supports environment variables for sensitive configuration:

```yaml
git:
  api_key: ${GIT_API_KEY}
  base_url: ${GIT_BASE_URL}
```

## Configuration Examples

### Strict Configuration

```yaml
ratchets:
  basic:
    enabled: true
    config:
      function_length:
        max_lines: 30
      line_length:
        max_chars: 80
  custom:
    enabled: true
    config:
      import_order:
        strict: true
      docstring:
        required: true
```

### Relaxed Configuration

```yaml
ratchets:
  basic:
    enabled: true
    config:
      function_length:
        max_lines: 100
      line_length:
        max_chars: 120
  custom:
    enabled: true
    config:
      import_order:
        strict: false
      docstring:
        required: false
```

## Best Practices

1. **Version Control**
   - Keep configurations in version control
   - Document configuration changes
   - Use environment variables for secrets

2. **Organization**
   - Group related settings
   - Use clear, descriptive names
   - Comment complex settings
   - Maintain consistent structure

3. **Maintenance**
   - Review configurations regularly
   - Update as requirements change
   - Test configuration changes
   - Document non-obvious settings

## Advanced Topics

- [Custom Ratchets](../advanced/custom_ratchets.md)
- [CI/CD Integration](../advanced/ci_integration.md)
- [Security Considerations](../advanced/security.md) 