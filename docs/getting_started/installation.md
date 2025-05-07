# Installation Guide

## Prerequisites

- Python 3.8 or higher
- Git 2.0 or higher
- pip (Python package installer)

## Installation Methods

### Using pip

The recommended way to install CodeRatchet is using pip:

```bash
pip install coderatchet
```

### From Source

1. Clone the repository:
```bash
git clone https://github.com/yourusername/coderatchet.git
cd coderatchet
```

2. Install in development mode:
```bash
pip install -e .
```

### Verifying Installation

After installation, verify that CodeRatchet is properly installed:

```bash
coderatchet --version
```

## Configuration

### Basic Configuration

Create a `coderatchet.yaml` file in your project root:

```yaml
# Example configuration
ratchets:
  - name: no_print_statements
    pattern: print\(
    match_examples:
      - "print('Hello')"
    non_match_examples:
      - "logger.info('Hello')"
```

### Advanced Configuration

For more complex configurations, see the [Configuration Guide](../core_concepts/configuration.md).

## Post-Installation Steps

1. Initialize git repository (if not already done):
```bash
git init
```

2. Create a `.gitignore` file to exclude unnecessary files:
```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class

# Distribution / packaging
dist/
build/
*.egg-info/

# Virtual environments
venv/
env/
```

3. Create an initial commit:
```bash
git add .
git commit -m "Initial commit"
```

## Troubleshooting

If you encounter any issues during installation:

1. Check Python version:
```bash
python --version
```

2. Verify pip is up to date:
```bash
pip install --upgrade pip
```

3. Check git installation:
```bash
git --version
```

For more detailed troubleshooting, see the [Troubleshooting Guide](../troubleshooting/common_issues.md).

## Next Steps

- [Quick Start Guide](../getting_started/quick_start.md)
- [Basic Usage](../getting_started/basic_usage.md) 