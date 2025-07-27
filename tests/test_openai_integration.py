"""Integration tests for microservices using OpenAI through the gateway."""
import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient

from src.gateway.app.providers.openai_provider import OpenAIProvider
from src.gateway.app.providers.base import ResponseRequest, ResponseObject


class TestOpenAIIntegration:
    """Test the integration between microservices and OpenAI via the gateway."""
    
    @pytest.fixture
    def openai_provider(self):
        """Create an OpenAI provider instance with mocked API key."""
        with patch('src.gateway.app.config.settings.openai_api_key', 'test-api-key'):
            return OpenAIProvider()
    
    @pytest.fixture
    def mock_openai_client(self):
        """Create a mock OpenAI client."""
        mock_client = AsyncMock()
        
        # Create a proper mock response object with model_dump method
        class MockResponse:
            def model_dump(self):
                return {
                    "id": "resp_test123",
                    "object": "response",
                    "created": 1234567890,
                    "model": "gpt-4.1",
                    "output": [{"type": "text", "text": "This is a test response from OpenAI"}],
                    "usage": {
                        "prompt_tokens": 15,
                        "completion_tokens": 25,
                        "reasoning_tokens": 5,
                        "total_tokens": 45
                    },
                    "tool_calls": None,
                    "status": "completed",
                    "incomplete_details": None,
                    "choices": None,
                    "data": None
                }
        
        mock_response = MockResponse()
        mock_client.responses.create.return_value = mock_response
        mock_client.responses.retrieve.return_value = mock_response
        mock_client.responses.delete.return_value = None
        return mock_client
    
    @pytest.mark.asyncio
    async def test_create_response_with_openai(self, openai_provider, mock_openai_client):
        """Test creating a response through OpenAI provider."""
        openai_provider.client = mock_openai_client
        
        request = ResponseRequest(
            model="gpt-4.1",
            input="What is the capital of France?",
            instructions="Provide a brief answer.",
            temperature=0.7
        )
        
        response = await openai_provider.create_response(request)
        
        # Verify the response
        assert response.id == "resp_test123"
        assert response.model == "gpt-4.1"
        assert response.output == [{"type": "text", "text": "This is a test response from OpenAI"}]
        assert response.usage["total_tokens"] == 45
        assert response.input_tokens == 15
        assert response.output_tokens == 25
        assert response.reasoning_tokens == 5
        
        # Verify the call to OpenAI
        mock_openai_client.responses.create.assert_called_once()
        call_args = mock_openai_client.responses.create.call_args[1]
        assert call_args["model"] == "gpt-4.1"
        assert call_args["input"] == "What is the capital of France?"
        assert call_args["instructions"] == "Provide a brief answer."
        assert call_args["temperature"] == 0.7
    
    @pytest.mark.asyncio
    async def test_streaming_response_with_openai(self, openai_provider, mock_openai_client):
        """Test streaming responses from OpenAI."""
        # Mock streaming response
        async def mock_stream():
            chunks = [
                {"type": "response.text.delta", "delta": {"text": "The capital"}},
                {"type": "response.text.delta", "delta": {"text": " of France"}},
                {"type": "response.text.delta", "delta": {"text": " is Paris."}},
                {"type": "response.done", "output": "The capital of France is Paris."}
            ]
            for chunk in chunks:
                class MockChunk:
                    def __init__(self, data):
                        self.data = data
                    def model_dump(self):
                        return self.data
                yield MockChunk(chunk)
        
        mock_openai_client.responses.create.return_value = mock_stream()
        openai_provider.client = mock_openai_client
        
        request = ResponseRequest(
            model="gpt-4.1",
            input="What is the capital of France?",
            stream=True
        )
        
        # Collect streamed chunks
        chunks = []
        async for chunk in openai_provider.stream_response(request):
            chunks.append(chunk)
        
        assert len(chunks) == 4
        assert '"type": "response.text.delta"' in chunks[0]
        assert '"text": "The capital"' in chunks[0]
        assert '"type": "response.done"' in chunks[3]
    
    @pytest.mark.asyncio
    async def test_tool_usage_with_openai(self, openai_provider, mock_openai_client):
        """Test using tools (functions) with OpenAI."""
        # Mock response with tool calls
        class MockToolResponse:
            def model_dump(self):
                return {
                    "id": "resp_tool123",
                    "object": "response",
                    "created": 1234567890,
                    "model": "gpt-4.1",
                    "output": None,
                    "tool_calls": [
                        {
                            "id": "call_123",
                            "type": "function",
                            "function": {
                                "name": "get_weather",
                                "arguments": '{"location": "Paris", "unit": "celsius"}'
                            }
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 30,
                        "completion_tokens": 15,
                        "reasoning_tokens": 10,
                        "total_tokens": 55
                    },
                    "status": "completed"
                }
        mock_openai_client.responses.create.return_value = MockToolResponse()
        openai_provider.client = mock_openai_client
        
        request = ResponseRequest(
            model="gpt-4.1",
            input="What's the weather in Paris?",
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get weather information for a location",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "location": {"type": "string"},
                                "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}
                            },
                            "required": ["location"]
                        }
                    }
                }
            ],
            tool_choice="auto"
        )
        
        response = await openai_provider.create_response(request)
        
        # Verify tool calls in response
        assert response.tool_calls is not None
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0]["function"]["name"] == "get_weather"
        assert "Paris" in response.tool_calls[0]["function"]["arguments"]
    
    @pytest.mark.asyncio
    async def test_conversation_with_previous_response(self, openai_provider, mock_openai_client):
        """Test continuing a conversation using previous_response_id."""
        openai_provider.client = mock_openai_client
        
        request = ResponseRequest(
            model="gpt-4.1",
            input="What else can you tell me about it?",
            previous_response_id="resp_previous123"
        )
        
        response = await openai_provider.create_response(request)
        
        # Verify previous_response_id was passed
        mock_openai_client.responses.create.assert_called_once()
        call_args = mock_openai_client.responses.create.call_args[1]
        assert call_args["previous_response_id"] == "resp_previous123"
    
    @pytest.mark.asyncio
    async def test_reasoning_models(self, openai_provider, mock_openai_client):
        """Test using reasoning models like o4-mini."""
        # Mock response with reasoning tokens
        class MockReasoningResponse:
            def model_dump(self):
                return {
                    "id": "resp_reasoning123",
                    "object": "response",
                    "created": 1234567890,
                    "model": "o4-mini",
                    "output": [{"type": "text", "text": "Based on careful analysis..."}],
                    "usage": {
                        "prompt_tokens": 20,
                        "completion_tokens": 30,
                        "reasoning_tokens": 100,  # High reasoning tokens for o4 models
                        "total_tokens": 150
                    },
                    "status": "completed"
                }
        mock_openai_client.responses.create.return_value = MockReasoningResponse()
        openai_provider.client = mock_openai_client
        
        request = ResponseRequest(
            model="o4-mini",
            input="Solve this complex problem step by step...",
            reasoning={"effort": "high"}
        )
        
        response = await openai_provider.create_response(request)
        
        # Verify reasoning model response
        assert response.model == "o4-mini"
        assert response.reasoning_tokens == 100
        assert response.usage["reasoning_tokens"] == 100
        
        # Verify reasoning parameter was normalized
        call_args = mock_openai_client.responses.create.call_args[1]
        assert call_args["reasoning"] == {"effort": "high"}
    
    @pytest.mark.asyncio
    async def test_builtin_tools(self, openai_provider, mock_openai_client):
        """Test using built-in tools like web-search-preview."""
        openai_provider.client = mock_openai_client
        
        request = ResponseRequest(
            model="gpt-4.1",
            input="Search for recent news about AI advancements",
            tools=[{"type": "web_search_preview"}, {"type": "code_interpreter"}]
        )
        
        await openai_provider.create_response(request)
        
        # Verify built-in tools were passed correctly (no normalization needed for dicts)
        call_args = mock_openai_client.responses.create.call_args[1]
        assert call_args["tools"] == [
            {"type": "web_search_preview"},
            {"type": "code_interpreter"}
        ]
    
    @pytest.mark.asyncio
    async def test_response_format_json_schema(self, openai_provider, mock_openai_client):
        """Test structured output with JSON schema."""
        openai_provider.client = mock_openai_client
        
        request = ResponseRequest(
            model="gpt-4.1",
            input="Generate a user profile",
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "user_profile",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "age": {"type": "integer"},
                            "email": {"type": "string"}
                        },
                        "required": ["name", "email"]
                    }
                }
            }
        )
        
        await openai_provider.create_response(request)
        
        # Verify response format was passed correctly
        call_args = mock_openai_client.responses.create.call_args[1]
        assert call_args["response_format"]["type"] == "json_schema"
        assert "user_profile" in call_args["response_format"]["json_schema"]["name"]
    
    @pytest.mark.asyncio
    async def test_error_handling(self, openai_provider, mock_openai_client):
        """Test error handling for OpenAI API errors."""
        # Mock an API error
        mock_error = Exception("OpenAI API Error")
        mock_error.status_code = 404
        mock_openai_client.responses.create = AsyncMock(side_effect=mock_error)
        openai_provider.client = mock_openai_client
        
        request = ResponseRequest(
            model="invalid-model",
            input="Test input"
        )
        
        with pytest.raises(ValueError, match="Model 'invalid-model' not found"):
            await openai_provider.create_response(request)
    
    @pytest.mark.asyncio
    async def test_retrieve_and_delete_responses(self, openai_provider, mock_openai_client):
        """Test retrieving and deleting stored responses."""
        openai_provider.client = mock_openai_client
        
        # Test retrieve
        response = await openai_provider.retrieve_response("resp_123")
        assert response.id == "resp_test123"
        mock_openai_client.responses.retrieve.assert_called_once_with("resp_123")
        
        # Test delete
        result = await openai_provider.delete_response("resp_123")
        assert result["id"] == "resp_123"
        assert result["deleted"] is True
        mock_openai_client.responses.delete.assert_called_once_with("resp_123")