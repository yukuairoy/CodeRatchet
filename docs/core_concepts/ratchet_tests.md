# Ratchet Tests

Ratchet tests are the core concept of CodeRatchet. They define patterns that should not be present in your codebase and help maintain code quality standards.

## Basic Structure

A ratchet test consists of:

- `name`: A descriptive identifier for the test
- `pattern`: A regular expression pattern to match
- `match_examples`: Examples that should match the pattern
- `non_match_examples`: Examples that should not match the pattern

Example:
```yaml
ratchets:
  - name: no_print_statements
    pattern: print\(
    match_examples:
      - "print('Hello')"
      - "print(f'Hello {name}')"
    non_match_examples:
      - "logger.info('Hello')"
      - "print = 'test'"
```

## Pattern Types

### 1. Simple Patterns
Basic regular expressions for simple matches:
```yaml
- name: no_tabs
  pattern: \t
  match_examples:
    - "\tindented line"
  non_match_examples:
    - "    indented line"
```

### 2. Complex Patterns
Advanced regular expressions with groups and lookarounds:
```yaml
- name: no_hardcoded_credentials
  pattern: (password|secret|key)\s*=\s*['\"][^'\"]+['\"]
  match_examples:
    - "password = 'secret123'"
    - "api_key = \"sk_test_123\""
  non_match_examples:
    - "password = None"
    - "key_length = 32"
```

### 3. File-specific Patterns
Patterns that only apply to certain file types:
```yaml
- name: no_console_log
  pattern: console\.log\(
  file_pattern: "*.js"
  match_examples:
    - "console.log('test')"
  non_match_examples:
    - "logger.info('test')"
```

## Best Practices

### 1. Pattern Design
- Keep patterns as specific as possible
- Use non-capturing groups when possible
- Consider edge cases in your examples
- Test patterns thoroughly before deployment

### 2. Example Selection
- Include both obvious and edge cases
- Cover different variations of the same pattern
- Include false positives to ensure accuracy
- Update examples as patterns evolve

### 3. Naming Conventions
- Use descriptive, action-oriented names
- Follow a consistent naming scheme
- Include the type of check in the name
- Avoid ambiguous terms

## Common Patterns

### Code Style
```yaml
- name: no_trailing_whitespace
  pattern: \s+$
  match_examples:
    - "line with spaces    "
  non_match_examples:
    - "clean line"
```

### Security
```yaml
- name: no_hardcoded_secrets
  pattern: (api_key|secret|password)\s*=\s*['\"][^'\"]{8,}['\"]
  match_examples:
    - "api_key = 'sk_test_1234567890'"
  non_match_examples:
    - "api_key = os.getenv('API_KEY')"
```

### Performance
```yaml
- name: no_nested_loops
  pattern: for\s+.*\s+in\s+.*:\s*\n\s*for\s+.*\s+in\s+.*:
  match_examples:
    - "for i in range(10):\n    for j in range(10):"
  non_match_examples:
    - "for i in range(10):\n    print(i)"
```

## Advanced Features

### 1. Custom Validators
You can create custom validator functions for complex checks:
```python
def validate_import_order(imports):
    stdlib = []
    third_party = []
    local = []
    
    for imp in imports:
        if imp.startswith('.'):
            local.append(imp)
        elif '.' in imp:
            third_party.append(imp)
        else:
            stdlib.append(imp)
    
    return stdlib + third_party + local == imports
```

### 2. Conditional Patterns
Patterns that only apply under certain conditions:
```yaml
- name: no_direct_db_access
  pattern: "cursor\\.execute\\("
  condition: "not file.endswith('_test.py')"
  match_examples:
    - "cursor.execute('SELECT * FROM users')"
  non_match_examples:
    - "test_cursor.execute('SELECT 1')"
```

### 3. Pattern Groups
Group related patterns together:
```yaml
- name: security_checks
  patterns:
    - no_hardcoded_secrets
    - no_unsafe_eval
    - no_sql_injection
  match_examples:
    - "password = 'secret123'"
    - "eval(user_input)"
    - "f'SELECT * FROM {table}'"
  non_match_examples:
    - "password = None"
    - "safe_eval('1 + 1')"
    - "query = 'SELECT * FROM users'"
```

## Testing Your Patterns

Always test your patterns before deploying them:

1. Create test cases
2. Run against sample code
3. Verify matches and non-matches
4. Check performance impact

For more information, see the [Testing Guide](../contributing/testing.md). 