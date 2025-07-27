#!/usr/bin/env python3
"""Test JSON response handling for layout refinement."""

import asyncio
import json
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from src.injestion.agent.llm_client import call_llm


def test_json_response():
    """Test that we can get proper JSON responses."""
    print("Testing JSON response handling...")
    
    system_prompt = "You are a document layout expert. Respond ONLY with valid JSON matching the provided schema, no prose."
    
    user_content = """
Please analyze these boxes and return JSON:
{
  "boxes": [{"id": "1", "bbox": [100, 100, 200, 150], "label": "Text", "score": 0.9}],
  "reading_order": ["1"]
}

Return JSON exactly matching this schema:
{
  "boxes": [{"id": "string", "bbox": [x1, y1, x2, y2], "label": "string", "score": 0-1}],
  "reading_order": ["id", ...]
}
"""
    
    try:
        response = call_llm(
            system_prompt=system_prompt,
            user_content=user_content,
            model="gpt-4o-mini",
            temperature=0.1,
        )
        
        print(f"Raw response:\n{response}")
        
        # Try to extract JSON from the response
        # The response might be wrapped in markdown code blocks
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            json_str = response.split("```")[1].split("```")[0].strip()
        else:
            json_str = response.strip()
            
        print(f"\nExtracted JSON string:\n{json_str}")
        
        # Parse the JSON
        parsed = json.loads(json_str)
        print(f"\nParsed JSON:\n{json.dumps(parsed, indent=2)}")
        
        # Validate structure
        assert "boxes" in parsed, "Missing 'boxes' key"
        assert "reading_order" in parsed, "Missing 'reading_order' key"
        assert isinstance(parsed["boxes"], list), "'boxes' should be a list"
        assert isinstance(parsed["reading_order"], list), "'reading_order' should be a list"
        
        print("\n✓ JSON response is valid and properly structured!")
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {type(e).__name__}: {e}")
        return False


if __name__ == "__main__":
    # Unset shell API key to use .env
    import os
    if "OPENAI_API_KEY" in os.environ:
        del os.environ["OPENAI_API_KEY"]
    
    success = test_json_response()
    print(f"\nTest {'PASSED' if success else 'FAILED'}")