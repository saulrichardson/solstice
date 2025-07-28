#!/usr/bin/env python3
"""Debug o4-mini issue"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from fact_check.core.responses_client import ResponsesClient

client = ResponsesClient()

# Test with progressively longer prompts
prompts = [
    "Hi",
    "What is 2+2?",
    "Explain quantum physics in one sentence.",
    "Write a haiku about coding.",
    """Analyze this text and return JSON:
{"verdict": "test", "confidence": 0.5}""",
    """Given a claim and document, analyze.
CLAIM: Test
DOCUMENT: Test document.
Return JSON: {"verdict": "supports", "confidence": 1.0}"""
]

print("Testing o4-mini with different prompt lengths")
print("="*50)

for i, prompt in enumerate(prompts, 1):
    print(f"\nTest {i} (length: {len(prompt)} chars)")
    print(f"Prompt preview: {prompt[:50]}...")
    
    try:
        response = client.create_response(
            model="o4-mini",
            input=prompt,
            temperature=0
        )
        print(f"✅ Success! Model: {response.get('model')}")
        
        # Check token usage
        usage = response.get('usage', {})
        print(f"Tokens - Input: {usage.get('input_tokens')}, Output: {usage.get('output_tokens')}, Reasoning: {usage.get('reasoning_tokens')}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        # Try to get more error details
        if hasattr(e, 'response'):
            print(f"Response status: {e.response.status_code}")
            print(f"Response body: {e.response.text[:200]}")

print("\n" + "="*50)
print("Findings:")
print("- o4-mini may have different prompt length limits")
print("- Or it may require different formatting for complex prompts")
print("- Check gateway logs for more details about the 500 errors")