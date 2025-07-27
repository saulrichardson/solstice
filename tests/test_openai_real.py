"""Real integration tests for OpenAI API - these make actual API calls."""
import os
import pytest
import asyncio
from dotenv import load_dotenv

from src.gateway.app.providers.openai_provider import OpenAIProvider
from src.gateway.app.providers.base import ResponseRequest

# Load environment variables
load_dotenv()

# Skip all tests in this file if no API key is present
pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set - skipping real API tests"
)


class TestOpenAIRealAPI:
    """Test real OpenAI API integration."""
    
    @pytest.fixture
    def openai_provider(self):
        """Create a real OpenAI provider instance."""
        return OpenAIProvider()
    
    @pytest.mark.asyncio
    async def test_simple_response(self, openai_provider):
        """Test a simple response from OpenAI."""
        request = ResponseRequest(
            model="gpt-4o-mini",  # Using cheaper model for tests
            input="What is 2+2? Answer with just the number.",
            temperature=0  # For consistent responses
        )
        
        response = await openai_provider.create_response(request)
        
        # Verify response structure
        assert response.id.startswith("resp_")
        assert response.model == "gpt-4o-mini"
        assert response.output is not None
        assert len(response.output) > 0
        assert response.output[0]["type"] == "text"
        assert "4" in response.output[0]["text"]
        
        # Verify token usage
        assert response.input_tokens > 0
        assert response.output_tokens > 0
        assert response.usage["total_tokens"] > 0
        
        print(f"\nResponse: {response.output[0]['text']}")
        print(f"Tokens used: {response.usage['total_tokens']}")
    
    @pytest.mark.asyncio
    async def test_streaming_response(self, openai_provider):
        """Test streaming response from OpenAI."""
        request = ResponseRequest(
            model="gpt-4o-mini",
            input="Count from 1 to 5",
            stream=True,
            temperature=0
        )
        
        chunks = []
        async for chunk in openai_provider.stream_response(request):
            chunks.append(chunk)
            print(f"Chunk: {chunk[:100]}...")  # Print first 100 chars
        
        assert len(chunks) > 0
        # Should have multiple chunks for streaming
        assert len(chunks) > 1
        
        # Verify we got text deltas
        text_chunks = [c for c in chunks if '"type": "response.text.delta"' in c]
        assert len(text_chunks) > 0
    
    @pytest.mark.asyncio
    async def test_tool_usage(self, openai_provider):
        """Test using tools with OpenAI."""
        request = ResponseRequest(
            model="gpt-4o-mini",
            input="What's the weather in Paris, France?",
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get the weather for a location",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "location": {
                                    "type": "string",
                                    "description": "The city and country"
                                },
                                "unit": {
                                    "type": "string",
                                    "enum": ["celsius", "fahrenheit"]
                                }
                            },
                            "required": ["location"]
                        }
                    }
                }
            ],
            tool_choice="required"  # Force tool use
        )
        
        response = await openai_provider.create_response(request)
        
        # Should have tool calls
        assert response.tool_calls is not None
        assert len(response.tool_calls) > 0
        assert response.tool_calls[0]["type"] == "function"
        assert response.tool_calls[0]["function"]["name"] == "get_weather"
        
        # Parse arguments
        import json
        args = json.loads(response.tool_calls[0]["function"]["arguments"])
        assert "location" in args
        assert "Paris" in args["location"]
        
        print(f"\nTool call: {response.tool_calls[0]['function']['name']}")
        print(f"Arguments: {args}")
    
    @pytest.mark.asyncio
    async def test_conversation_continuation(self, openai_provider):
        """Test continuing a conversation."""
        # First message
        request1 = ResponseRequest(
            model="gpt-4o-mini",
            input="My name is Alice. Remember this.",
            temperature=0
        )
        
        response1 = await openai_provider.create_response(request1)
        assert response1.id
        
        # Continue conversation
        request2 = ResponseRequest(
            model="gpt-4o-mini",
            input="What is my name?",
            previous_response_id=response1.id,
            temperature=0
        )
        
        response2 = await openai_provider.create_response(request2)
        
        # Should remember the name
        assert "Alice" in response2.output[0]["text"]
        
        print(f"\nFirst response: {response1.output[0]['text']}")
        print(f"Second response: {response2.output[0]['text']}")
        
        # Clean up - delete the stored responses
        await openai_provider.delete_response(response1.id)
        await openai_provider.delete_response(response2.id)
    
    @pytest.mark.asyncio
    async def test_json_response_format(self, openai_provider):
        """Test structured JSON output."""
        request = ResponseRequest(
            model="gpt-4o-mini",
            input="Generate a person with name and age",
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "person",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "age": {"type": "integer"}
                        },
                        "required": ["name", "age"]
                    }
                }
            }
        )
        
        response = await openai_provider.create_response(request)
        
        # Response should be valid JSON matching the schema
        import json
        output_text = response.output[0]["text"]
        parsed = json.loads(output_text)
        
        assert "name" in parsed
        assert "age" in parsed
        assert isinstance(parsed["name"], str)
        assert isinstance(parsed["age"], int)
        
        print(f"\nJSON response: {parsed}")
    
    @pytest.mark.asyncio
    async def test_error_handling_invalid_model(self, openai_provider):
        """Test error handling with invalid model."""
        request = ResponseRequest(
            model="invalid-model-xyz",
            input="Hello"
        )
        
        with pytest.raises(ValueError, match="Model.*not found"):
            await openai_provider.create_response(request)
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="o1 models are expensive - uncomment to test")
    async def test_reasoning_model(self, openai_provider):
        """Test o1 reasoning model (expensive - skipped by default)."""
        request = ResponseRequest(
            model="o1-mini",
            input="Explain why the sky is blue using physics principles",
            reasoning={"effort": "high"}
        )
        
        response = await openai_provider.create_response(request)
        
        # o1 models use reasoning tokens
        assert response.reasoning_tokens > 0
        assert response.usage["reasoning_tokens"] > 0
        
        print(f"\nReasoning tokens used: {response.reasoning_tokens}")
        print(f"Response: {response.output[0]['text'][:200]}...")


@pytest.mark.asyncio
async def test_gateway_with_real_api():
    """Test the full gateway with real API calls."""
    from fastapi.testclient import TestClient
    from src.gateway.app.main import app
    
    client = TestClient(app)
    
    response = client.post("/v1/responses", json={
        "model": "gpt-4o-mini",
        "input": "Say hello!",
        "temperature": 0
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"]
    assert data["output"]
    assert data["usage"]["total_tokens"] > 0
    
    print(f"\nGateway response: {data['output'][0]['text']}")
    print(f"Total tokens: {data['usage']['total_tokens']}")


if __name__ == "__main__":
    # Run just the basic test when called directly
    async def run_basic_test():
        provider = OpenAIProvider()
        request = ResponseRequest(
            model="gpt-4o-mini",
            input="Say 'Hello, tests are working!'",
            temperature=0
        )
        response = await provider.create_response(request)
        print(f"Response: {response.output[0]['text']}")
        print(f"Tokens used: {response.usage['total_tokens']}")
    
    asyncio.run(run_basic_test())