"""Robust JSON parsing utilities for handling LLM responses."""

import json
import re
import logging
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)


def parse_json_response(text: str) -> Dict[str, Any]:
    """
    Parse JSON from LLM response text, handling common formatting issues.
    
    This function handles:
    - Markdown code blocks (```json ... ``` or ``` ... ```)
    - Extra whitespace
    - Common JSON syntax issues
    - Nested JSON strings
    
    Args:
        text: Raw text response from LLM
        
    Returns:
        Parsed JSON as dictionary
        
    Raises:
        json.JSONDecodeError: If JSON cannot be parsed after all attempts
    """
    if not text:
        raise json.JSONDecodeError("Empty response", "", 0)
    
    # Step 1: Clean markdown code blocks
    cleaned = clean_json_text(text)
    
    # Step 2: Try standard parsing
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.debug(f"Initial JSON parse failed: {e}")
    
    # Step 3: Try to extract JSON from mixed content
    extracted = extract_json_object(cleaned)
    if extracted:
        try:
            return json.loads(extracted)
        except json.JSONDecodeError as e:
            logger.debug(f"Extracted JSON parse failed: {e}")
    
    # Step 4: Try to fix common JSON issues
    fixed = fix_json_syntax(cleaned)
    if fixed != cleaned:
        try:
            return json.loads(fixed)
        except json.JSONDecodeError as e:
            logger.debug(f"Fixed JSON parse failed: {e}")
    
    # Step 5: Try to handle truncated JSON
    if cleaned.startswith('{') and not cleaned.endswith('}'):
        repaired = repair_truncated_json(cleaned)
        if repaired:
            try:
                return json.loads(repaired)
            except json.JSONDecodeError as e:
                logger.debug(f"Repaired JSON parse failed: {e}")
    
    # Step 6: Final attempt with the original after basic cleaning
    # Sometimes the LLM includes explanation before/after JSON
    json_match = re.search(r'\{[^{}]*\{[^{}]*\}[^{}]*\}|\{[^{}]*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    
    # If all else fails, raise the original error
    raise json.JSONDecodeError(
        f"Could not parse JSON from response: {text[:200]}...",
        text, 0
    )


def clean_json_text(text: str) -> str:
    """
    Clean common formatting issues from JSON text.
    
    Args:
        text: Raw text that may contain JSON
        
    Returns:
        Cleaned text
    """
    # Remove leading/trailing whitespace
    text = text.strip()
    
    # Remove markdown code blocks
    # Handles: ```json ... ```, ``` ... ```, ```JSON ... ```
    patterns = [
        r'^```(?:json|JSON)?\s*\n(.*?)\n```$',  # Multiline code block
        r'^```(?:json|JSON)?\s*(.*?)```$',       # Single line code block
        r'^`(.*?)`$',                             # Single backticks
    ]
    
    for pattern in patterns:
        match = re.match(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            text = match.group(1).strip()
            break
    
    # Remove any remaining leading/trailing backticks
    text = text.strip('`')
    
    # Remove potential JSON prefix/suffix text
    # Some LLMs add "Here is the JSON:" or similar
    prefixes = [
        r'^(?:Here is|This is|The|Output|Result|JSON|Response)[^{]*',
        r'^[^{]*(?:json|JSON|Json)[:\s]*',
    ]
    
    for prefix in prefixes:
        text = re.sub(prefix, '', text, flags=re.IGNORECASE)
    
    # Remove trailing explanations after the JSON
    # Look for complete JSON object and remove anything after
    json_match = re.match(r'(\{.*\})', text, re.DOTALL)
    if json_match:
        # Verify it's likely complete by checking bracket balance
        candidate = json_match.group(1)
        if is_balanced_json(candidate):
            text = candidate
    
    return text.strip()


def extract_json_object(text: str) -> Optional[str]:
    """
    Extract a JSON object from mixed content.
    
    Args:
        text: Text that may contain JSON mixed with other content
        
    Returns:
        Extracted JSON string or None
    """
    # Try to find JSON object boundaries
    start_idx = text.find('{')
    if start_idx == -1:
        return None
    
    # Find matching closing brace
    brace_count = 0
    in_string = False
    escape_next = False
    
    for i in range(start_idx, len(text)):
        char = text[i]
        
        if escape_next:
            escape_next = False
            continue
            
        if char == '\\':
            escape_next = True
            continue
            
        if char == '"' and not escape_next:
            in_string = not in_string
            continue
            
        if not in_string:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    return text[start_idx:i+1]
    
    return None


def fix_json_syntax(text: str) -> str:
    """
    Fix common JSON syntax issues.
    
    Args:
        text: JSON text with potential syntax issues
        
    Returns:
        Fixed JSON text
    """
    # Fix Python-style booleans and None
    text = re.sub(r'\bTrue\b', 'true', text)
    text = re.sub(r'\bFalse\b', 'false', text)
    text = re.sub(r'\bNone\b', 'null', text)
    
    # Fix single quotes (careful not to break contractions in strings)
    # This is tricky and error-prone, so we only do it if double quotes are rare
    if text.count('"') < text.count("'") / 2:
        # Likely using single quotes for JSON
        # Simple approach: replace ' with " when not inside a word
        text = re.sub(r"(?<![a-zA-Z])'([^']*)'(?![a-zA-Z])", r'"\1"', text)
    
    # Fix trailing commas (common error)
    text = re.sub(r',(\s*[}\]])', r'\1', text)
    
    # Fix missing quotes on keys (basic case)
    # This is risky and only for simple cases
    text = re.sub(r'(\{|\,)\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1 "\2":', text)
    
    return text


def is_balanced_json(text: str) -> bool:
    """
    Check if JSON brackets are balanced.
    
    Args:
        text: JSON text to check
        
    Returns:
        True if brackets are balanced
    """
    count = 0
    in_string = False
    escape_next = False
    
    for char in text:
        if escape_next:
            escape_next = False
            continue
            
        if char == '\\':
            escape_next = True
            continue
            
        if char == '"' and not escape_next:
            in_string = not in_string
            continue
            
        if not in_string:
            if char == '{':
                count += 1
            elif char == '}':
                count -= 1
                if count < 0:
                    return False
    
    return count == 0


def repair_truncated_json(text: str) -> Optional[str]:
    """
    Attempt to repair truncated JSON by closing open structures.
    
    Args:
        text: Potentially truncated JSON text
        
    Returns:
        Repaired JSON string or None if repair isn't possible
    """
    # Count open structures
    brace_count = 0
    bracket_count = 0
    in_string = False
    escape_next = False
    last_quote_pos = -1
    
    for i, char in enumerate(text):
        if escape_next:
            escape_next = False
            continue
            
        if char == '\\':
            escape_next = True
            continue
            
        if char == '"' and not escape_next:
            if in_string:
                in_string = False
            else:
                in_string = True
                last_quote_pos = i
            continue
            
        if not in_string:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
            elif char == '[':
                bracket_count += 1
            elif char == ']':
                bracket_count -= 1
    
    # If we're still in a string, close it
    repaired = text
    if in_string:
        # Check if we're in the middle of a value
        # Look for the last colon before the unclosed quote
        before_quote = text[:last_quote_pos]
        last_colon = before_quote.rfind(':')
        if last_colon > 0:
            # We're likely in a value, add closing quote
            repaired += '"'
        
    # Add null for incomplete values
    if repaired.rstrip().endswith(':'):
        repaired += 'null'
    elif repaired.rstrip().endswith(','):
        # Remove trailing comma
        repaired = repaired.rstrip()[:-1]
    
    # Close arrays and objects
    repaired += ']' * bracket_count
    repaired += '}' * brace_count
    
    return repaired


def parse_json_with_pydantic(
    text: str,
    model_class: type,
    strict: bool = True
) -> Union[Dict[str, Any], Any]:
    """
    Parse JSON and validate with a Pydantic model.
    
    Args:
        text: Raw text response from LLM
        model_class: Pydantic model class for validation
        strict: If False, returns raw dict on validation failure
        
    Returns:
        Validated model instance (as dict) or raw dict if strict=False
        
    Raises:
        json.JSONDecodeError: If JSON cannot be parsed
        pydantic.ValidationError: If validation fails and strict=True
    """
    # First parse the JSON
    raw_dict = parse_json_response(text)
    
    # Then validate with Pydantic
    try:
        instance = model_class(**raw_dict)
        return instance.dict()
    except Exception as e:
        if strict:
            raise
        else:
            logger.warning(f"Pydantic validation failed: {e}")
            return raw_dict