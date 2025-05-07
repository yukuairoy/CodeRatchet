# Configuration

CodeRatchet uses YAML configuration files to define ratchet tests and their settings.

## Basic Configuration

Create a `coderatchet.yaml` file in your project root:

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

### Ratchets Section

The `ratchets` section defines which ratchet tests to run:

```yaml
ratchets:
  basic:
    enabled: true  # Enable/disable basic ratchets
    config: {}     # Basic ratchet configuration
  custom:
    enabled: true  # Enable/disable custom ratchets
    config:        # Custom ratchet configuration
      function_length:
        max_lines: 50  # Maximum lines per function
```

### Git Options

```yaml
git:
  base_branch: main  # Base branch for comparison
  ignore_patterns:   # Files to ignore
    - "*.pyc"
    - "__pycache__/*"
    - "*.egg-info/*"
```

### CI Options

```yaml
ci:
  fail_on_violations: true  # Fail CI on violations
  report_format: text       # Report format (text, json)
```

## Ratchet Configuration

### Basic Ratchets

Basic ratchets are built-in tests that can be enabled/disabled:

```yaml
ratchets:
  basic:
    enabled: true
    config: {}
```

### Custom Ratchets

Custom ratchets can be configured with specific settings:

```yaml
ratchets:
  custom:
    enabled: true
    config:
      function_length:
        max_lines: 50
```

## File Exclusion

You can exclude files from ratchet checks using patterns:

```yaml
git:
  ignore_patterns:
    - "*.pyc"
    - "__pycache__/*"
    - "*.egg-info/*"
```

## Environment Variables

Configuration can be overridden using environment variables:

- `CODERATCHET_CONFIG`: Path to configuration file
- `CODERATCHET_DEBUG`: Enable debug mode

## Configuration Examples

### Strict Configuration

```yaml
ratchets:
  basic:
    enabled: true
    config: {}
  custom:
    enabled: true
    config:
      function_length:
        max_lines: 30
git:
  base_branch: main
  ignore_patterns:
    - "*.pyc"
    - "__pycache__/*"
ci:
  fail_on_violations: true
  report_format: text
```

### Relaxed Configuration

```yaml
ratchets:
  basic:
    enabled: true
    config: {}
  custom:
    enabled: true
    config:
      function_length:
        max_lines: 100
git:
  base_branch: develop
  ignore_patterns:
    - "*.pyc"
    - "__pycache__/*"
    - "*.egg-info/*"
    - "tests/*"
ci:
  fail_on_violations: false
  report_format: json
```

## Best Practices

1. Version control your configuration file
2. Keep configurations organized and documented
3. Use environment variables for sensitive settings
4. Regularly review and update configurations

## Advanced Topics

- Custom ratchets
- CI/CD integration
- Security considerations 