# CLI Command Reference

This document provides detailed information about CodeRatchet's command-line interface.

## Basic Commands

### check
Run ratchet checks on current code.

```bash
coderatchet check [options]
```

Options:
- `--limit N`: Maximum number of failures to show (default: 10)
- `--since COMMIT`: Check since specific commit
- `--include-commits`: Include commit information
- `--debug`: Enable debug mode
- `--config FILE`: Use specific configuration file

Example:
```bash
# Basic check
coderatchet check

# Check with limit
coderatchet check --limit 20

# Check since last commit
coderatchet check --since HEAD~1
```

### history
View violation history.

```bash
coderatchet history [options]
```

Options:
- `--limit N`: Maximum number of entries to show
- `--since COMMIT`: Show history since specific commit
- `--format FORMAT`: Output format (text, json)
- `--debug`: Enable debug mode

Example:
```bash
# Basic history
coderatchet history

# JSON format
coderatchet history --format json

# Limited history
coderatchet history --limit 5
```

### config
Show current configuration.

```bash
coderatchet config [options]
```

Options:
- `--format FORMAT`: Output format (text, json, yaml)
- `--debug`: Enable debug mode

Example:
```bash
# Basic config
coderatchet config

# YAML format
coderatchet config --format yaml
```

## Advanced Commands

### init
Initialize CodeRatchet in a repository.

```bash
coderatchet init [options]
```

Options:
- `--force`: Overwrite existing configuration
- `--template TEMPLATE`: Use specific template
- `--debug`: Enable debug mode

Example:
```bash
# Basic initialization
coderatchet init

# Force initialization
coderatchet init --force
```

### add
Add a new ratchet test.

```bash
coderatchet add [options]
```

Options:
- `--name NAME`: Test name
- `--pattern PATTERN`: Regex pattern
- `--match-examples EXAMPLES`: Match examples
- `--non-match-examples EXAMPLES`: Non-match examples
- `--debug`: Enable debug mode

Example:
```bash
# Add test interactively
coderatchet add

# Add test with options
coderatchet add --name no_print --pattern "print\\("
```

### remove
Remove a ratchet test.

```bash
coderatchet remove [options]
```

Options:
- `--name NAME`: Test name
- `--force`: Skip confirmation
- `--debug`: Enable debug mode

Example:
```bash
# Remove test interactively
coderatchet remove

# Remove specific test
coderatchet remove --name no_print
```

## Utility Commands

### version
Show version information.

```bash
coderatchet version
```

Example:
```bash
coderatchet version
```

### help
Show help information.

```bash
coderatchet help [command]
```

Example:
```bash
# General help
coderatchet help

# Command help
coderatchet help check
```

## Configuration Commands

### config-validate
Validate configuration file.

```bash
coderatchet config-validate [options]
```

Options:
- `--file FILE`: Configuration file to validate
- `--debug`: Enable debug mode

Example:
```bash
# Validate default config
coderatchet config-validate

# Validate specific file
coderatchet config-validate --file custom.yaml
```

### config-update
Update configuration.

```bash
coderatchet config-update [options]
```

Options:
- `--key KEY`: Configuration key
- `--value VALUE`: New value
- `--debug`: Enable debug mode

Example:
```bash
# Update cache size
coderatchet config-update --key cache.size --value 1000
```

## Examples

### Basic Workflow
```bash
# Initialize
coderatchet init

# Add test
coderatchet add --name no_print --pattern "print\\("

# Run check
coderatchet check

# View history
coderatchet history
```

### Advanced Workflow
```bash
# Initialize with template
coderatchet init --template security

# Add multiple tests
coderatchet add --name no_secrets --pattern "(password|secret|key)\\s*="
coderatchet add --name no_unsafe_eval --pattern "eval\\("

# Run check with limit
coderatchet check --limit 20 --include-commits

# View history in JSON
coderatchet history --format json
```

### Configuration Management
```bash
# Show current config
coderatchet config

# Validate config
coderatchet config-validate

# Update config
coderatchet config-update --key cache.enabled --value true

# Remove test
coderatchet remove --name no_print
```

## Exit Codes

| Code | Description |
|------|-------------|
| 0 | Success |
| 1 | General error |
| 2 | Configuration error |
| 3 | Git error |
| 4 | Pattern error |
| 5 | File error |

## Environment Variables

| Variable | Description |
|----------|-------------|
| CODERATCHET_CONFIG | Path to configuration file |
| CODERATCHET_DEBUG | Enable debug mode |
| CODERATCHET_CACHE_DIR | Cache directory path |

For more information, see the [Configuration Guide](../core_concepts/configuration.md). 