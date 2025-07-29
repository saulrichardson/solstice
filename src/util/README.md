# Util Module

Common utility functions and helpers used across the Solstice project.

## Overview

The util module provides lightweight, reusable utilities that don't fit into other domain-specific modules. Currently focused on:
- **Nonce Generation**: Unique identifiers for cache-busting and request tracking

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

## Future Utilities

Potential additions based on common patterns:

- **retry**: Decorator for retrying operations
- **timer**: Context manager for timing operations
- **hash**: Consistent hashing utilities
- **sanitize**: String sanitization helpers
- **batch**: Batch processing utilities
- **async_utils**: Async/await helpers

## Integration

The util module is designed to be imported anywhere:

```python
# In any module
from src.util.nonce import new_nonce
from src.util.future_utility import helper_function
```

No circular dependencies or complex initialization required.