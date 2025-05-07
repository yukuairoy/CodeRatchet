# Configuration API Reference

This document provides detailed information about CodeRatchet's configuration API.

## Configuration Structure

### Basic Structure
```yaml
# coderatchet.yaml
ratchets:
  - name: test_name
    pattern: regex_pattern
    match_examples:
      - "example1"
    non_match_examples:
      - "example2"

cache:
  enabled: true
  size: 1000

processing:
  max_workers: 4
  max_file_size: 1000000
```

### Advanced Structure
```yaml
# coderatchet.yaml
ratchets:
  - name: security_checks
    patterns:
      - no_hardcoded_secrets
      - no_unsafe_eval
    file_pattern: "*.py"
    condition: "not file.endswith('_test.py')"

  - name: style_checks
    patterns:
      - no_tabs
      - no_trailing_whitespace
    file_pattern: "*.{py,js}"

cache:
  enabled: true
  size: 1000
  directory: .coderatchet/cache
  ttl: 3600

processing:
  max_workers: 4
  max_file_size: 1000000
  timeout: 300
  retries: 3

logging:
  level: INFO
  file: coderatchet.log
  format: "%(asctime)s - %(levelname)s - %(message)s"
```

## Configuration Classes

### Config
Main configuration class.

```python
@dataclass
class Config:
    ratchets: List[RatchetConfig]
    cache: CacheConfig
    processing: ProcessingConfig
    logging: LoggingConfig
    
    @classmethod
    def from_file(cls, path: str) -> 'Config':
        """
        Load configuration from file.
        
        Args:
            path: Path to configuration file
            
        Returns:
            Config: Loaded configuration
        """
        pass
    
    def validate(self) -> bool:
        """
        Validate configuration.
        
        Returns:
            bool: True if configuration is valid
        """
        pass
```

### RatchetConfig
Ratchet test configuration.

```python
@dataclass
class RatchetConfig:
    name: str
    pattern: str
    match_examples: List[str]
    non_match_examples: List[str]
    file_pattern: Optional[str] = None
    condition: Optional[str] = None
    
    def validate(self) -> bool:
        """
        Validate ratchet configuration.
        
        Returns:
            bool: True if configuration is valid
        """
        pass
```

### CacheConfig
Cache configuration.

```python
@dataclass
class CacheConfig:
    enabled: bool
    size: int
    directory: Optional[str] = None
    ttl: Optional[int] = None
    
    def validate(self) -> bool:
        """
        Validate cache configuration.
        
        Returns:
            bool: True if configuration is valid
        """
        pass
```

### ProcessingConfig
Processing configuration.

```python
@dataclass
class ProcessingConfig:
    max_workers: int
    max_file_size: int
    timeout: Optional[int] = None
    retries: Optional[int] = None
    
    def validate(self) -> bool:
        """
        Validate processing configuration.
        
        Returns:
            bool: True if configuration is valid
        """
        pass
```

### LoggingConfig
Logging configuration.

```python
@dataclass
class LoggingConfig:
    level: str
    file: Optional[str] = None
    format: Optional[str] = None
    
    def validate(self) -> bool:
        """
        Validate logging configuration.
        
        Returns:
            bool: True if configuration is valid
        """
        pass
```

## Configuration Functions

### load_config
Load configuration from file.

```python
def load_config(path: str) -> Config:
    """
    Load configuration from file.
    
    Args:
        path: Path to configuration file
        
    Returns:
        Config: Loaded configuration
    """
    pass
```

### save_config
Save configuration to file.

```python
def save_config(config: Config, path: str) -> None:
    """
    Save configuration to file.
    
    Args:
        config: Configuration to save
        path: Path to save configuration
    """
    pass
```

### validate_config
Validate configuration.

```python
def validate_config(config: Config) -> bool:
    """
    Validate configuration.
    
    Args:
        config: Configuration to validate
        
    Returns:
        bool: True if configuration is valid
    """
    pass
```

## Configuration Examples

### Basic Configuration
```python
from coderatchet.config import Config, RatchetConfig

# Create basic configuration
config = Config(
    ratchets=[
        RatchetConfig(
            name="no_print",
            pattern="print\\(",
            match_examples=["print('test')"],
            non_match_examples=["logger.info('test')"]
        )
    ],
    cache=CacheConfig(enabled=True, size=1000),
    processing=ProcessingConfig(max_workers=4, max_file_size=1000000),
    logging=LoggingConfig(level="INFO")
)

# Save configuration
save_config(config, "coderatchet.yaml")
```

### Advanced Configuration
```python
from coderatchet.config import Config, RatchetConfig

# Create advanced configuration
config = Config(
    ratchets=[
        RatchetConfig(
            name="security_checks",
            pattern="(password|secret|key)\\s*=",
            match_examples=["password = 'secret'"],
            non_match_examples=["password = None"],
            file_pattern="*.py",
            condition="not file.endswith('_test.py')"
        )
    ],
    cache=CacheConfig(
        enabled=True,
        size=1000,
        directory=".coderatchet/cache",
        ttl=3600
    ),
    processing=ProcessingConfig(
        max_workers=4,
        max_file_size=1000000,
        timeout=300,
        retries=3
    ),
    logging=LoggingConfig(
        level="INFO",
        file="coderatchet.log",
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
)

# Validate configuration
if validate_config(config):
    save_config(config, "coderatchet.yaml")
```

## Configuration Validation

### Schema Validation
```python
from coderatchet.config import validate_schema

def validate_config(config: Config) -> bool:
    """
    Validate configuration using schema.
    
    Args:
        config: Configuration to validate
        
    Returns:
        bool: True if configuration is valid
    """
    schema = {
        "type": "object",
        "properties": {
            "ratchets": {"type": "array"},
            "cache": {"type": "object"},
            "processing": {"type": "object"},
            "logging": {"type": "object"}
        }
    }
    return validate_schema(config, schema)
```

### Pattern Validation
```python
from coderatchet.config import validate_pattern

def validate_ratchet(config: RatchetConfig) -> bool:
    """
    Validate ratchet configuration.
    
    Args:
        config: Ratchet configuration to validate
        
    Returns:
        bool: True if configuration is valid
    """
    try:
        validate_pattern(config.pattern)
        return True
    except PatternError:
        return False
```

For more information, see the [Configuration Guide](../core_concepts/configuration.md). 