"""Robust parser for LLM JSON responses with retry logic."""

import json
import re
import logging
from typing import TypeVar, Type, Optional, Dict, Any
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class LLMResponseParser:
    """Robust parser for LLM JSON responses with automatic retry logic."""
    
    @staticmethod
    def clean_json_string(content: str) -> str:
        """Clean common JSON formatting issues from LLM output."""
        # Remove markdown code blocks
        if content.startswith('```json') and content.endswith('```'):
            content = content[7:-3].strip()
        elif content.startswith('```') and content.endswith('```'):
            content = content[3:-3].strip()
            
        # Remove trailing commas (common LLM error)
        content = re.sub(r',\s*}', '}', content)
        content = re.sub(r',\s*]', ']', content)
        
        # Fix common quote issues
        # Convert smart quotes to regular quotes
        content = content.replace('"', '"').replace('"', '"')
        content = content.replace(''', "'").replace(''', "'")
        
        # Extract just the JSON if there's extra text
        # Find first { and last matching }
        if '{' in content:
            start = content.index('{')
            # Count braces to find matching close
            brace_count = 0
            end = -1
            for i in range(start, len(content)):
                if content[i] == '{':
                    brace_count += 1
                elif content[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end = i + 1
                        break
            
            if end > start:
                content = content[start:end]
        
        # Escape control characters in JSON strings
        # This handles newlines, tabs, etc. that break JSON parsing
        def escape_json_string(match):
            s = match.group(1)
            # Replace common control characters
            s = s.replace('\n', '\\n')
            s = s.replace('\r', '\\r')
            s = s.replace('\t', '\\t')
            s = s.replace('\b', '\\b')
            s = s.replace('\f', '\\f')
            # Replace any other control characters
            s = re.sub(r'[\x00-\x1f]', lambda m: f'\\u{ord(m.group(0)):04x}', s)
            return f'"{s}"'
        
        # Find strings and escape control characters inside them
        # This regex matches strings while handling escaped quotes
        content = re.sub(r'"((?:[^"\\]|\\.)*)\"', escape_json_string, content)
                
        return content
    
    @classmethod
    def get_schema_example(cls, model: Type[BaseModel]) -> str:
        """Get a simple example of the expected JSON structure."""
        schema = model.schema()
        example = {}
        
        for field_name, field_info in schema['properties'].items():
            if field_info['type'] == 'string':
                example[field_name] = field_info.get('description', 'string value')
            elif field_info['type'] == 'boolean':
                example[field_name] = True
            elif field_info['type'] == 'array':
                example[field_name] = [{"example": "item"}]
            else:
                example[field_name] = field_info['type']
                
        return json.dumps(example, indent=2)
    
    @classmethod
    async def parse_with_retry(
        cls,
        llm_client,
        prompt: str,
        output_model: Type[T],
        max_retries: int = 2,
        include_format_hint: bool = True,
        temperature: float = 0.0,
        max_output_tokens: int = 2000
    ) -> T:
        """
        Parse LLM response with automatic retry on validation errors.
        
        Args:
            llm_client: The LLM client to use
            prompt: The prompt to send to the LLM
            output_model: The Pydantic model to validate against
            max_retries: Maximum number of retry attempts
            include_format_hint: Whether to add JSON format hint to prompt
            temperature: LLM temperature setting
            max_output_tokens: Maximum tokens for response
            
        Returns:
            Validated Pydantic model instance
            
        Raises:
            ValueError: If all retry attempts fail
        """
        
        # Add format hint to prompt if requested
        original_prompt = prompt
        if include_format_hint:
            example = cls.get_schema_example(output_model)
            prompt += f"\n\nReturn ONLY valid JSON matching this structure:\n{example}"
        
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                # Get LLM response
                response = await llm_client.create_response(
                    input=prompt,
                    model=getattr(llm_client, 'model', 'gpt-4.1'),
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                    disable_request_deduplication=True
                )
                
                # Extract text content
                if hasattr(llm_client, 'extract_text'):
                    content = llm_client.extract_text(response)
                else:
                    # Fallback for different response formats
                    content = str(response)
                
                # Clean the JSON
                cleaned = cls.clean_json_string(content)
                
                # Try to parse
                data = json.loads(cleaned)
                
                # Validate with Pydantic
                return output_model(**data)
                
            except json.JSONDecodeError as e:
                last_error = f"Invalid JSON: {str(e)}"
                logger.warning(f"Attempt {attempt + 1} failed with JSON error: {last_error}")
                
                if attempt < max_retries:
                    # Add error feedback to prompt
                    prompt = f"{original_prompt}\n\nPREVIOUS ATTEMPT FAILED: {last_error}\nPlease return valid JSON only, with no additional text."
                    
            except ValidationError as e:
                last_error = f"Validation error: {e.json()}"
                logger.warning(f"Attempt {attempt + 1} failed with validation error: {last_error}")
                
                if attempt < max_retries:
                    # Add specific validation feedback
                    error_details = []
                    for error in e.errors():
                        field = '.'.join(str(x) for x in error['loc'])
                        error_details.append(f"- {field}: {error['msg']}")
                    
                    prompt = f"{original_prompt}\n\nPREVIOUS ATTEMPT FAILED with these validation errors:\n" + \
                            "\n".join(error_details) + \
                            "\nPlease fix these issues and return valid JSON."
                    
            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
                logger.error(f"Unexpected error parsing LLM response: {e}", exc_info=True)
                
        # All retries failed
        raise ValueError(f"Failed to get valid response after {max_retries + 1} attempts. Last error: {last_error}")