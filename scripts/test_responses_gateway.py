#!/usr/bin/env python3
"""
Test script for the Responses API gateway.
"""
import os
import sys
import json

# Add parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.fact_check.core.responses_client import ResponsesClient


def test_basic_completion():
    """Test basic text completion."""
    print("=== Testing Basic Completion ===")
    client = ResponsesClient()
    
    try:
        response = client.complete(
            "What is 2+2? Answer in one word.",
            model="gpt-4.1-mini"
        )
        print(f"Response: {response}")
        print("✓ Basic completion working\n")
        return True
    except Exception as e:
        print(f"✗ Basic completion failed: {e}\n")
        return False


def test_stateful_conversation():
    """Test stateful conversation handling."""
    print("=== Testing Stateful Conversation ===")
    client = ResponsesClient()
    
    try:
        # Start conversation
        response1 = client.create_stateful_conversation(
            "My favorite color is blue and I work as a software engineer.",
            model="gpt-4.1-mini",
            instructions="Remember details about the user"
        )
        print(f"First response: {response1['output_text']}")
        print(f"Response ID: {response1['id']}")
        
        # Continue conversation
        response2 = client.continue_conversation(
            "What did I tell you about my job?",
            previous_response_id=response1['id'],
            model="gpt-4.1-mini"
        )
        print(f"Second response: {response2['output_text']}")
        print("✓ Stateful conversation working\n")
        return True
    except Exception as e:
        print(f"✗ Stateful conversation failed: {e}\n")
        return False


def test_tool_use():
    """Test tool calling functionality."""
    print("=== Testing Tool Use ===")
    client = ResponsesClient()
    
    try:
        # Test with custom tool
        tools = [{
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get current weather for a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "City name"
                        },
                        "unit": {
                            "type": "string",
                            "enum": ["celsius", "fahrenheit"],
                            "description": "Temperature unit"
                        }
                    },
                    "required": ["location"]
                }
            }
        }]
        
        response = client.complete_with_tools(
            "What's the weather like in Paris?",
            tools=tools,
            model="gpt-4.1-mini"
        )
        
        print(f"Response: {response.get('output_text', '')}")
        if response.get('tool_calls'):
            print("Tool calls made:")
            for tool_call in response['tool_calls']:
                print(f"  - {tool_call['function']['name']}: {tool_call['function']['arguments']}")
        print("✓ Tool use working\n")
        return True
    except Exception as e:
        print(f"✗ Tool use failed: {e}\n")
        return False


def test_built_in_tools():
    """Test built-in tools like web search."""
    print("=== Testing Built-in Tools ===")
    client = ResponsesClient()
    
    try:
        response = client.complete_with_tools(
            "Search for information about the Eiffel Tower height",
            tools=["web-search-preview"],
            model="gpt-4.1"
        )
        
        print(f"Response: {response.get('output_text', '')[:200]}...")
        if response.get('tool_calls'):
            print(f"Used built-in tools: {[tc['function']['name'] for tc in response['tool_calls']]}")
        print("✓ Built-in tools working\n")
        return True
    except Exception as e:
        print(f"✗ Built-in tools failed: {e}\n")
        return False


def test_reasoning_model():
    """Test o4-mini reasoning model."""
    print("=== Testing Reasoning Model ===")
    client = ResponsesClient()
    
    try:
        response = client.complete_with_reasoning(
            "Solve this step by step: If 3 cats catch 3 mice in 3 minutes, how many cats are needed to catch 100 mice in 100 minutes?",
            model="o4-mini",
            reasoning_level="high"
        )
        
        print(f"Response: {response[:200]}...")
        print("✓ Reasoning model working\n")
        return True
    except Exception as e:
        print(f"✗ Reasoning model failed: {e}\n")
        return False


def test_streaming():
    """Test streaming responses."""
    print("=== Testing Streaming ===")
    client = ResponsesClient()
    
    try:
        print("Streaming response: ", end="", flush=True)
        for chunk in client.stream_response(
            "Count from 1 to 3",
            model="gpt-4.1-mini"
        ):
            if chunk.get("output_text"):
                print(chunk["output_text"], end="", flush=True)
        print("\n✓ Streaming working\n")
        return True
    except Exception as e:
        print(f"\n✗ Streaming failed: {e}\n")
        return False


def test_retrieve_delete():
    """Test response retrieval and deletion."""
    print("=== Testing Retrieve/Delete ===")
    client = ResponsesClient()
    
    try:
        # Create a stored response
        response = client.create_response(
            input="Test message for storage",
            model="gpt-4.1-mini",
            store=True
        )
        response_id = response['id']
        print(f"Created response: {response_id}")
        
        # Retrieve it
        retrieved = client.retrieve_response(response_id)
        print(f"Retrieved response: {retrieved['id']}")
        
        # Delete it
        deleted = client.delete_response(response_id)
        print(f"Deleted response: {deleted}")
        
        print("✓ Retrieve/Delete working\n")
        return True
    except Exception as e:
        print(f"✗ Retrieve/Delete failed: {e}\n")
        return False


def main():
    """Run all tests."""
    print("Testing Responses API Gateway\n")
    
    # Check environment
    gateway_url = os.getenv("SOLSTICE_GATEWAY_URL", f"http://localhost:{os.getenv('SOLSTICE_GATEWAY_PORT', '4000')}")
    print(f"Gateway URL: {gateway_url}")
    print(f"API Key: {'Set' if os.getenv('OPENAI_API_KEY') else 'Not set'}")
    print()
    
    # Run tests
    tests = [
        test_basic_completion,
        test_stateful_conversation,
        test_tool_use,
        test_built_in_tools,
        test_reasoning_model,
        test_streaming,
        test_retrieve_delete
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"Test {test.__name__} crashed: {e}")
            results.append(False)
    
    # Summary
    passed = sum(results)
    total = len(results)
    print(f"\n{'='*50}")
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed")
        return 1


if __name__ == "__main__":
    exit(main())