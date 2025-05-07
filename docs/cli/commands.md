# CLI Commands

> **Note**: CLI support is not yet implemented in CodeRatchet. This document describes the planned CLI interface. For now, please use the Python API as described in the [Quick Start Guide](../getting_started/quick_start.md).

## Current Usage

Until CLI support is implemented, please use the Python API:

```python
from coderatchet.core.config import RatchetConfigManager
from coderatchet.core.ratchet import run_ratchets_on_file

# Initialize configuration
config = RatchetConfigManager("coderatchet.yaml")

# Get configured ratchets
ratchets = config.get_ratchets()

# Run checks on a file
results = run_ratchets_on_file("your_file.py", ratchets)
```

For more information, see the [Quick Start Guide](../getting_started/quick_start.md) and [API Reference](../api/core.md).

## Planned CLI Interface

The following commands are planned for future implementation:

### check
Run ratchet tests on your codebase:

```bash
coderatchet check [options]
```

Options:
- `--config`: Path to config file (default: coderatchet.yaml)
- `--verbose`: Show detailed output
- `--quiet`: Show only errors
- `--format`: Output format (text, json, html)

### history
View violation history:

```bash
coderatchet history [options]
```

Options:
- `--limit`: Maximum number of violations to show
- `--since`: Show violations since date/commit
- `--by-file`: Group by file
- `--by-test`: Group by test

### config
Show or validate configuration:

```bash
coderatchet config [options]
```

Options:
- `--validate`: Validate configuration file
- `--show`: Show current configuration
- `--init`: Create default configuration

## Advanced Commands

### init

Initialize CodeRatchet in your project:

```bash
coderatchet init [options]
```

Options:
- `--basic`: Create basic configuration
- `--advanced`: Create advanced configuration
- `--git`: Initialize git hooks

### test

Test ratchet patterns:

```bash
coderatchet test [options]
```

Options:
- `--pattern`: Test a specific pattern
- `--file`: Test against a specific file
- `--examples`: Show pattern examples

### report

Generate violation reports:

```bash
coderatchet report [options]
```

Options:
- `--format`: Report format (html, json, text)
- `--output`: Output file path
- `--include-history`: Include historical data

## Git Integration

### pre-commit

Run as git pre-commit hook:

```bash
coderatchet pre-commit [options]
```

Options:
- `--strict`: Fail on any violation
- `--fix`: Auto-fix violations where possible
- `--staged`: Check only staged files

### status

Show current violation status:

```bash
coderatchet status [options]
```

Options:
- `--short`: Show summary only
- `--compare`: Compare with another branch/commit
- `--trend`: Show violation trend

## Configuration

### validate

Validate configuration file:

```bash
coderatchet validate [options]
```

Options:
- `--fix`: Fix common issues
- `--strict`: Enable strict validation
- `--suggest`: Suggest improvements

### update

Update ratchet values:

```bash
coderatchet update [options]
```

Options:
- `--auto`: Automatically update values
- `--dry-run`: Show what would be updated
- `--backup`: Create backup before updating

## Examples

1. Basic check with default config:
```bash
coderatchet check
```

2. Check with custom config:
```bash
coderatchet check --config custom.yaml
```

3. View recent violations:
```bash
coderatchet history --limit 10
```

4. Generate HTML report:
```bash
coderatchet report --format html --output report.html
```

5. Initialize in new project:
```bash
coderatchet init --basic
```

## Exit Codes

- 0: Success
- 1: Violations found
- 2: Configuration error
- 3: System error

## Environment Variables

- `CODERATCHET_CONFIG`: Default config file path
- `CODERATCHET_VERBOSE`: Enable verbose output
- `CODERATCHET_NO_COLOR`: Disable colored output
- `CODERATCHET_MAX_WORKERS`: Maximum worker processes

## See Also

- [Configuration Guide](../core_concepts/configuration.md)
- [Custom Ratchets](../advanced/custom_ratchets.md)
- [Git Integration](../advanced/git_integration.md) 