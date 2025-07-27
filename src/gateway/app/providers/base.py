from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from pydantic import BaseModel


class ResponseRequest(BaseModel):
    """Request model for Responses API"""
    model: str
    input: str | list[dict] | None = None
    previous_response_id: str | None = None
    instructions: str | None = None
    tools: list[dict] | None = None
    tool_choice: str | dict | None = "auto"
    parallel_tool_calls: bool | None = True
    store: bool | None = True
    background: bool | None = False
    reasoning: dict | None = None
    include: list[str] | None = None
    temperature: float | None = None
    top_p: float | None = None
    max_output_tokens: int | None = None
    truncation: dict | None = None
    metadata: dict | None = None
    stream: bool | None = False
    response_format: dict | None = None
    n: int | None = None
    presence_penalty: float | None = None
    frequency_penalty: float | None = None
    timeout: int | None = None


class ResponseObject(BaseModel):
    """Response model for Responses API"""
    id: str
    object: str = "response"
    created: int
    model: str
    output: list[dict] | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    reasoning_tokens: int | None = None
    tool_calls: list[dict] | None = None
    status: str | None = None
    incomplete_details: dict | None = None
    usage: dict | None = None
    choices: list[dict] | None = None
    data: dict | None = None

    # No additional validators—gateway now expects the nested `output` format


class Provider(ABC):
    """Base class for LLM providers using Responses API"""
    
    @abstractmethod
    async def create_response(self, request: ResponseRequest) -> ResponseObject:
        """Create a response using the Responses API"""
        pass
    
    @abstractmethod
    async def stream_response(self, request: ResponseRequest) -> AsyncIterator[str]:
        """Stream a response"""
        pass
    
    @abstractmethod
    async def retrieve_response(self, response_id: str) -> ResponseObject:
        """Retrieve a stored response"""
        pass
    
    @abstractmethod
    async def delete_response(self, response_id: str) -> dict:
        """Delete a stored response"""
        pass
