# CodeRatchet Configuration Examples

This directory contains example configuration files for different use cases of CodeRatchet.

## Configuration Files

### basic.yaml
A basic configuration with default settings. Good for getting started with CodeRatchet.
- Enables basic and custom ratchets
- Standard line length and function length limits
- Basic git and CI settings

### strict.yaml
A strict configuration for enforcing high code quality standards.
- More aggressive limits on function length and line length
- Strict import order enforcement
- Fails CI on both violations and warnings
- Checks all files, not just changed ones

### relaxed.yaml
A more permissive configuration for development or legacy codebases.
- Allows print statements and TODO comments
- More lenient line length limits
- Ignores common magic numbers
- Doesn't fail CI on violations
- Only checks changed files

### custom.yaml
A configuration focused on custom ratchet tests.
- Disables basic ratchets
- Enables advanced custom checks:
  - Function length with docstring exclusion
  - Strict import order with custom stdlib list
  - Docstring style enforcement
  - Code complexity metrics
- JSON output format for CI integration

## Configuration Options

### Basic Options
- `ratchets.basic.enabled`: Enable/disable basic ratchets
- `ratchets.basic.config`: Configuration for basic ratchets
- `ratchets.custom.enabled`: Enable/disable custom ratchets
- `ratchets.custom.config`: Configuration for custom ratchets

### Git Options
- `git.base_branch`: Base branch for comparison
- `git.ignore_patterns`: Patterns to ignore in git operations

### CI Options
- `ci.fail_on_violations`: Whether to fail CI on violations
- `ci.report_format`: Output format (text/json)
- `ci.check_all_files`: Check all files or just changed ones
- `ci.exclude_patterns`: Additional patterns to exclude from checks

## Usage

To use a configuration file:

```python
from coderatchet.core.config import RatchetConfig

# Load configuration
config = RatchetConfig("path/to/config.yaml")

# Get configured ratchets
ratchets = config.get_ratchets()

# Run checks
results = run_ratchets_on_file("your_file.py", ratchets)
```

## Customizing

You can create your own configuration by:
1. Starting with one of these examples
2. Modifying the settings to match your needs
3. Adding or removing ratchets as required
4. Adjusting thresholds and limits

Remember to test your configuration with:
```python
python -m coderatchet --config your_config.yaml check
``` 