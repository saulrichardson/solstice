#!/usr/bin/env python3
"""Test the fact-checking agent specifically with gpt-4.1 model"""

import asyncio
import json
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fact_check.fact_checker import FactChecker
from fact_check.core.responses_client import ResponsesClient
from injestion.models.document import Document
from injestion.processing.fact_check_interface import FactCheckInterface


async def test_basic_llm_call():
    """Test basic LLM functionality with gpt-4.1"""
    print("=== Testing Basic LLM Call with gpt-4.1 ===\n")
    
    client = ResponsesClient()
    
    try:
        # Simple test prompt
        response = client.create_response(
            model="gpt-4.1",
            input="What is 2+2? Answer with just the number.",
            temperature=0
        )
        
        print(f"Response received: {response.get('model', 'Unknown model')}")
        
        # Extract the actual response text
        output = response.get('output', [])
        if output and isinstance(output, list):
            for msg in output:
                if isinstance(msg, dict) and 'content' in msg:
                    content = msg['content']
                    if isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict) and 'text' in item:
                                print(f"Response text: {item['text']}")
                                return True
                    elif isinstance(content, str):
                        print(f"Response text: {content}")
                        return True
        
        print("Could not extract response text")
        return False
        
    except Exception as e:
        print(f"Error in basic LLM call: {e}")
        return False


async def test_json_response():
    """Test that gpt-4.1 can return properly formatted JSON"""
    print("\n=== Testing JSON Response with gpt-4.1 ===\n")
    
    client = ResponsesClient()
    
    prompt = """Return a JSON object with the following structure:
{
    "name": "Test",
    "value": 42,
    "status": "success"
}

Return ONLY the JSON, no other text."""
    
    try:
        response = client.create_response(
            model="gpt-4.1",
            input=prompt,
            temperature=0
        )
        
        # Extract and parse the JSON
        output = response.get('output', [])
        if output and isinstance(output, list):
            for msg in output:
                if isinstance(msg, dict) and 'content' in msg:
                    content = msg['content']
                    if isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict) and 'text' in item:
                                text = item['text'].strip()
                                # Handle markdown-wrapped JSON
                                if text.startswith('```json') and text.endswith('```'):
                                    text = text[7:-3].strip()
                                elif text.startswith('```') and text.endswith('```'):
                                    text = text[3:-3].strip()
                                
                                data = json.loads(text)
                                print(f"Parsed JSON: {json.dumps(data, indent=2)}")
                                return True
        
        print("Could not extract JSON from response")
        return False
        
    except Exception as e:
        print(f"Error in JSON response test: {e}")
        return False


async def test_fact_checking():
    """Test the full fact-checking pipeline with gpt-4.1"""
    print("\n=== Testing Fact-Checking Pipeline with gpt-4.1 ===\n")
    
    # Create a simple test document
    test_document_text = """
    Flublok is a recombinant influenza vaccine. 
    Flublok is approved for use in persons 18 years of age and older.
    The most common side effects include injection site pain and headache.
    Clinical trials showed an efficacy rate of 50% against influenza.
    """
    
    # Test claims
    test_claims = [
        ("Flublok is approved for people 18 years and older.", "supports"),
        ("Flublok is approved for children under 12.", "does_not_support"),
        ("Flublok has an efficacy rate of 50%.", "supports"),
    ]
    
    client = ResponsesClient()
    fact_checker = FactChecker(client)
    
    results = []
    
    for claim, expected_verdict in test_claims:
        print(f"\nTesting claim: {claim}")
        print(f"Expected verdict: {expected_verdict}")
        
        try:
            result = await fact_checker.check_claim(claim, test_document_text)
            
            print(f"Actual verdict: {result.verdict}")
            print(f"Confidence: {result.confidence}")
            print(f"Success: {result.success}")
            
            # Check if verdict matches expected
            verdict_correct = result.verdict == expected_verdict
            results.append(verdict_correct)
            
            if verdict_correct:
                print("✅ Verdict matches expected!")
            else:
                print("❌ Verdict does not match expected")
                
            if result.steps:
                print(f"Found {len(result.steps)} reasoning steps")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append(False)
    
    return all(results)


async def test_retry_mechanism():
    """Test the quote retry mechanism"""
    print("\n=== Testing Quote Retry Mechanism ===\n")
    
    # Document with special characters
    test_document = """
    The vaccine effectiveness was measured at 45%.
    Side effects include pain at injection site.
    """
    
    client = ResponsesClient()
    fact_checker = FactChecker(client)
    
    # This claim should trigger a retry if the LLM quotes incorrectly
    claim = "The vaccine showed 45% effectiveness."
    
    try:
        result = await fact_checker.check_claim(claim, test_document)
        print(f"Result: {result.verdict}")
        print(f"Success after retry: {result.success}")
        return True
    except Exception as e:
        print(f"Error in retry test: {e}")
        return False


async def main():
    """Run all tests"""
    print("Testing gpt-4.1 Model Integration")
    print("="*50)
    
    # Check if gateway is accessible
    client = ResponsesClient()
    print(f"Using gateway at: {client.base_url}")
    print()
    
    # Run tests
    tests = [
        ("Basic LLM Call", test_basic_llm_call),
        ("JSON Response", test_json_response),
        ("Fact-Checking Pipeline", test_fact_checking),
        ("Retry Mechanism", test_retry_mechanism),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\nRunning: {test_name}")
        print("-" * 40)
        try:
            success = await test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"Test failed with error: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    total_passed = sum(1 for _, success in results if success)
    print(f"\nTotal: {total_passed}/{len(results)} tests passed")
    
    if total_passed == len(results):
        print("\n🎉 All tests passed! gpt-4.1 is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")


if __name__ == "__main__":
    asyncio.run(main())