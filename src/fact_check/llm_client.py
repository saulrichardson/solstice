"""LLM Client adapter for the fact checker to use the gateway"""

import httpx
from typing import Dict, Any


class GatewayLLMClient:
    """Client for making LLM calls through the Solstice Gateway"""
    
    def __init__(self, gateway_url: str = "http://localhost:8000"):
        self.gateway_url = gateway_url
        self.client = httpx.AsyncClient()
    
    async def create_response(self, request_data: Any) -> Dict[str, Any]:
        """
        Make a request to the gateway's /v1/responses endpoint
        
        Args:
            request_data: Request data matching ResponseRequest schema (dict or object)
            
        Returns:
            Response data from the gateway
        """
        # Convert to dict if it's a Pydantic model
        if hasattr(request_data, 'model_dump'):
            json_data = request_data.model_dump(exclude_none=True)
        else:
            json_data = request_data
            
        response = await self.client.post(
            f"{self.gateway_url}/v1/responses",
            json=json_data
        )
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()