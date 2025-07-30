# Util Module

Common utility functions and helpers used across the Solstice project.

## Architecture Overview

The util module serves as a collection of lightweight, general-purpose utilities that are used throughout the Solstice system. It follows the principle of high cohesion within each utility and loose coupling between utilities, ensuring that each function can be used independently without complex dependencies.

### Design Philosophy

- **Zero Dependencies**: Uses only Python standard library
- **Pure Functions**: No side effects or state management
- **Single Purpose**: Each utility does one thing well
- **Cross-Module Usage**: Designed to be imported anywhere in the codebase
- **Performance First**: Optimized for use in hot paths

## Components

### nonce.py

Generates unique, URL-safe random identifiers:

```python
from src.util.nonce import new_nonce

# Generate a unique identifier
nonce = new_nonce()  # Returns: "a3f2c8b1d9e74562893047a5b6c1d2e3"
```

**Features:**
- 32 character hexadecimal strings
- URL-safe (no special characters)
- 122 bits of randomness (UUID4 based)
- Deterministic length and format

**Use Cases:**
- Cache-busting query parameters
- Request correlation IDs
- Temporary file naming
- Session identifiers

## Usage Examples

### Cache Busting
```python
from src.util.nonce import new_nonce

# Force fresh API call
url = f"https://api.example.com/data?nonce={new_nonce()}"
```

### Request Tracking
```python
from src.util.nonce import new_nonce

async def process_request(data):
    request_id = new_nonce()
    logger.info(f"Processing request {request_id}")
    
    try:
        result = await heavy_computation(data)
        logger.info(f"Request {request_id} completed")
        return result
    except Exception as e:
        logger.error(f"Request {request_id} failed: {e}")
        raise
```

### Temporary Resources
```python
from pathlib import Path
from src.util.nonce import new_nonce

def create_temp_file(extension=".tmp"):
    temp_name = f"temp_{new_nonce()}{extension}"
    return Path("/tmp") / temp_name
```

## Design Principles

1. **Simplicity**: Each utility serves one clear purpose
2. **No Dependencies**: Utilities use only Python stdlib
3. **Type Safety**: Full type hints for all functions
4. **Performance**: Lightweight operations suitable for hot paths
5. **Testability**: Pure functions with no side effects

## Adding New Utilities

When adding utilities, consider:

1. **Scope**: Is this truly general-purpose or domain-specific?
2. **Dependencies**: Avoid external dependencies when possible
3. **Naming**: Use clear, descriptive names
4. **Documentation**: Include docstrings with examples
5. **Testing**: Add unit tests for edge cases

Example structure for new utilities:
```python
"""Brief description of the utility."""

from __future__ import annotations
from typing import Optional

def my_utility(param: str, optional: Optional[int] = None) -> str:
    """One-line description.
    
    Longer description if needed.
    
    Args:
        param: Description of parameter
        optional: Description of optional parameter
        
    Returns:
        Description of return value
        
    Example:
        >>> my_utility("test", 42)
        "test-42"
    """
    # Implementation
    pass
```

## Architecture Integration

### Current Usage

1. **Gateway Module**: Uses nonce for cache-busting API requests
2. **Fact Check Module**: Request correlation and tracking
3. **Testing**: Unique identifiers for test isolation

### Import Pattern
```python
# Clean, direct imports from any module
from src.util.nonce import new_nonce

# No initialization or configuration needed
nonce = new_nonce()
```

## Performance Characteristics

### Nonce Generation
- **Speed**: ~2-3 microseconds per generation
- **Memory**: Minimal allocation (32-byte string)
- **Thread Safety**: UUID4 is thread-safe by design
- **Entropy**: 122 bits of randomness (cryptographically secure)

## Security Considerations

1. **Randomness**: Uses `uuid.uuid4()` which uses OS random source
2. **Uniqueness**: Collision probability negligible (2^122 space)
3. **No Secrets**: Nonces are not meant for authentication
4. **URL Safety**: Hex format avoids injection issues

## Testing Strategy

```python
import pytest
from src.util.nonce import new_nonce

def test_nonce_format():
    nonce = new_nonce()
    assert len(nonce) == 32
    assert all(c in '0123456789abcdef' for c in nonce)

def test_nonce_uniqueness():
    nonces = {new_nonce() for _ in range(10000)}
    assert len(nonces) == 10000  # All unique
```

## Future Utilities

Potential additions based on observed patterns:

### 1. Retry Decorator
```python
@retry(attempts=3, backoff=exponential)
def flaky_operation():
    # Automatic retry with backoff
    pass
```

### 2. Timer Context Manager
```python
with timer("database_query"):
    result = db.execute(query)
# Logs: "database_query took 0.123s"
```

### 3. Hash Utilities
```python
# Consistent hashing for cache keys
cache_key = stable_hash({"user": 123, "doc": "abc"})
```

### 4. Batch Processing
```python
# Process items in efficient batches
for batch in batched(items, size=100):
    process_batch(batch)
```

### 5. Path Sanitization
```python
# Safe filename generation
safe_name = sanitize_filename("../../etc/passwd")
# Returns: "etc_passwd"
```

## Best Practices

### When to Add to Util

✅ **Good Candidates**:
- General-purpose functions used by 2+ modules
- Pure functions with no side effects
- Standard library only implementations
- Performance-critical helpers

❌ **Poor Candidates**:
- Domain-specific logic (belongs in respective module)
- Functions requiring external dependencies
- Stateful utilities or singletons
- Configuration-dependent code

### Code Quality Standards

1. **Type Hints**: Full typing for all parameters and returns
2. **Docstrings**: Clear examples in docstring
3. **Tests**: 100% coverage with edge cases
4. **Performance**: Profile if used in hot paths
5. **Naming**: Descriptive but concise function names

## Module Evolution

The util module is intentionally kept minimal. As it grows:

1. **Subcategorization**: Group related utilities (e.g., `util.strings`, `util.async`)
2. **Extraction**: Move domain-specific utils to their modules
3. **Documentation**: Keep README updated with all utilities
4. **Deprecation**: Clear migration path for replaced utilities