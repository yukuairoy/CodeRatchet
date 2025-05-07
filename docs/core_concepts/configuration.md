# Configuration Guide

This guide explains how to configure CodeRatchet for your project.

## Configuration File

CodeRatchet uses a YAML configuration file (`coderatchet.yaml`) to define its behavior.

### Basic Structure

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

git:
  base_branch: main
  ignore_patterns:
    - "*.pyc"
    - "__pycache__/*"
    - "*.egg-info/*"

ci:
  fail_on_violations: true
  report_format: text
```

## Ratchet Configuration

### Basic Ratchets

```yaml
ratchets:
  basic:
    enabled: true
    config:
      no_print_statements:
        enabled: true
        severity: warning
      no_debug_comments:
        enabled: true
        severity: info
      no_bare_except:
        enabled: true
        severity: error
```

### Custom Ratchets

```yaml
ratchets:
  custom:
    enabled: true
    config:
      no_hardcoded_secrets:
        enabled: true
        severity: high
        pattern: "(?i)(?:password|secret|key|token)\\s*=\\s*['\"][^'\"]+['\"]"
      function_length:
        enabled: true
        max_lines: 50
        severity: medium
```

## Git Integration

```yaml
git:
  base_branch: main
  ignore_patterns:
    - "*.pyc"
    - "__pycache__/*"
    - "*.egg-info/*"
    - "venv/*"
    - "build/*"
    - "dist/*"
  hooks:
    pre_commit:
      enabled: true
      fail_on_violations: true
    pre_push:
      enabled: false
```

## CI/CD Integration

```yaml
ci:
  fail_on_violations: true
  report_format: text
  output_file: ratchet_report.txt
  thresholds:
    error: 0
    warning: 5
    info: 10
```

## Advanced Settings

### Pattern Groups

```yaml
pattern_groups:
  security:
    - no_hardcoded_secrets
    - no_unsafe_eval
    - no_sql_injection
  style:
    - no_print_statements
    - no_debug_comments
    - function_length
```

### Custom Rules

```yaml
custom_rules:
  - name: custom_pattern
    pattern: "your_pattern_here"
    match_examples:
      - "example1"
      - "example2"
    non_match_examples:
      - "non_example1"
      - "non_example2"
    severity: warning
```

## Environment Variables

CodeRatchet supports environment variables in the configuration:

```yaml
ratchets:
  custom:
    config:
      function_length:
        max_lines: ${MAX_FUNCTION_LINES:-50}
```

## File-specific Settings

```yaml
file_settings:
  "tests/*":
    ratchets:
      no_print_statements:
        enabled: false
  "scripts/*.py":
    ratchets:
      function_length:
        max_lines: 100
```

## Best Practices

1. **Organization**
   - Group related settings together
   - Use meaningful names
   - Document non-obvious settings
   - Keep the file clean and readable

2. **Version Control**
   - Commit configuration changes
   - Document major changes
   - Use environment variables for sensitive values
   - Keep a backup of working configurations

3. **Maintenance**
   - Review settings regularly
   - Update patterns as needed
   - Monitor false positives
   - Adjust thresholds based on team feedback

## Example Configurations

### Minimal Configuration

```yaml
ratchets:
  basic:
    enabled: true
```

### Full Configuration

```yaml
ratchets:
  basic:
    enabled: true
    config:
      no_print_statements:
        enabled: true
        severity: warning
      no_debug_comments:
        enabled: true
        severity: info
  custom:
    enabled: true
    config:
      function_length:
        enabled: true
        max_lines: 50
        severity: warning

git:
  base_branch: main
  ignore_patterns:
    - "*.pyc"
    - "__pycache__/*"

ci:
  fail_on_violations: true
  report_format: text

pattern_groups:
  style:
    - no_print_statements
    - function_length

file_settings:
  "tests/*":
    ratchets:
      no_print_statements:
        enabled: false
```

## Next Steps

- Learn about [Custom Ratchets](../advanced/custom_ratchets.md)
- See [Real-world Examples](../examples/real_world.md)
- Check out [Troubleshooting](../troubleshooting/common_issues.md) 