"""Test suite for the Solstice gateway functionality."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from src.gateway.app.main import app, providers
from src.gateway.app.providers import ResponseRequest, ResponseObject


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_openai_provider():
    """Create a mock OpenAI provider."""
    provider = MagicMock()
    provider.create_response = AsyncMock()
    provider.stream_response = AsyncMock()
    provider.retrieve_response = AsyncMock()
    provider.delete_response = AsyncMock()
    return provider


class TestGatewayHealth:
    """Test the gateway health and status endpoints."""
    
    def test_health_endpoint(self, client):
        """Test that the health endpoint returns correct status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "providers" in data
        assert data["api_version"] == "responses"
        assert "cache_enabled" in data
    
    def test_api_info_endpoint(self, client):
        """Test the API info endpoint returns capability details."""
        response = client.get("/api-info")
        assert response.status_code == 200
        data = response.json()
        assert data["api_version"] == "responses/v1"
        assert "features" in data
        assert "roles" in data["features"]
        assert "conversation_storage" in data["features"]
        assert "streaming" in data["features"]
        assert "tools" in data["features"]
    
    def test_models_endpoint(self, client):
        """Test that the models endpoint lists available models."""
        response = client.get("/models")
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        models = data["models"]
        assert len(models) >= 2
        model_ids = [m["id"] for m in models]
        assert "gpt-4.1" in model_ids
        assert "o4-mini" in model_ids
    
    def test_pricing_endpoint(self, client):
        """Test the pricing information endpoint."""
        response = client.get("/pricing")
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert "gpt-4.1" in data["models"]
        assert "o4-mini" in data["models"]
        assert "tools" in data
        assert "storage" in data


class TestGatewayResponses:
    """Test the gateway response creation and management."""
    
    @pytest.mark.asyncio
    async def test_create_response_success(self, client, mock_openai_provider):
        """Test successful response creation."""
        # Setup mock response
        mock_response = ResponseObject(
            id="resp_123",
            object="response",
            created=1234567890,
            model="gpt-4.1",
            output=[{"type": "text", "text": "Test response"}],
            input_tokens=10,
            output_tokens=20,
            reasoning_tokens=0,
            tool_calls=None,
            status="completed",
            incomplete_details=None,
            choices=None,
            data=None,
            usage={
                "input_tokens": 10,
                "output_tokens": 20,
                "reasoning_tokens": 0,
                "total_tokens": 30
            }
        )
        mock_openai_provider.create_response.return_value = mock_response
        
        # Inject mock provider
        with patch.dict(providers, {"openai": mock_openai_provider}):
            response = client.post("/v1/responses", json={
                "model": "gpt-4.1",
                "input": "Hello, world!",
                "instructions": "Respond politely"
            })
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "resp_123"
        assert data["output"] == [{"type": "text", "text": "Test response"}]
        assert data["usage"]["total_tokens"] == 30
    
    @pytest.mark.asyncio
    async def test_create_response_invalid_request(self, client):
        """Test response creation with invalid request data."""
        response = client.post("/v1/responses", json={
            # Missing required 'model' field
            "input": "Hello"
        })
        assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_retrieve_response(self, client, mock_openai_provider):
        """Test retrieving a stored response."""
        mock_response = ResponseObject(
            id="resp_123",
            object="response",
            created=1234567890,
            model="gpt-4.1",
            output=[{"type": "text", "text": "Retrieved response"}],
            input_tokens=5,
            output_tokens=10,
            reasoning_tokens=0,
            tool_calls=None,
            status="completed",
            incomplete_details=None,
            choices=None,
            data=None,
            usage={
                "input_tokens": 5,
                "output_tokens": 10,
                "reasoning_tokens": 0,
                "total_tokens": 15
            }
        )
        mock_openai_provider.retrieve_response.return_value = mock_response
        
        with patch.dict(providers, {"openai": mock_openai_provider}):
            response = client.get("/v1/responses/resp_123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "resp_123"
        assert data["output"] == [{"type": "text", "text": "Retrieved response"}]
    
    @pytest.mark.asyncio
    async def test_delete_response(self, client, mock_openai_provider):
        """Test deleting a stored response."""
        mock_openai_provider.delete_response.return_value = {
            "id": "resp_123",
            "deleted": True
        }
        
        with patch.dict(providers, {"openai": mock_openai_provider}):
            response = client.delete("/v1/responses/resp_123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "resp_123"
        assert data["deleted"] is True
    
    @pytest.mark.skip(reason="Streaming tests require special handling with TestClient")
    def test_streaming_response(self, client):
        """Test streaming response functionality."""
        # Create a mock provider that returns an async generator
        class MockStreamProvider:
            async def stream_response(self, request):
                yield '{"type": "response.text.delta", "delta": {"text": "Hello"}}'
                yield '{"type": "response.text.delta", "delta": {"text": " world"}}'
                yield '{"type": "response.done"}'
        
        mock_provider = MockStreamProvider()
        
        with patch.dict(providers, {"openai": mock_provider}):
            response = client.post("/v1/responses", json={
                "model": "gpt-4.1",
                "input": "Hello",
                "stream": True
            })
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
        
        # Verify SSE format
        content = response.text
        assert "data: " in content
        assert "data: [DONE]" in content


class TestGatewayErrorHandling:
    """Test error handling in the gateway."""
    
    def test_provider_not_configured(self, client):
        """Test response when provider is not configured."""
        with patch.dict(providers, {}, clear=True):
            response = client.post("/v1/responses", json={
                "model": "gpt-4.1",
                "input": "Hello"
            })
        assert response.status_code == 500
        assert "not configured" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_provider_error_handling(self, client, mock_openai_provider):
        """Test handling of provider errors."""
        mock_openai_provider.create_response.side_effect = Exception("API Error")
        
        with patch.dict(providers, {"openai": mock_openai_provider}):
            response = client.post("/v1/responses", json={
                "model": "gpt-4.1",
                "input": "Hello"
            })
        
        assert response.status_code == 500
        assert "Provider error" in response.json()["detail"]