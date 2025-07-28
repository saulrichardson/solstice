"""
OpenAIProvider aligned strictly with latest openai>=1.24 Responses API.

This implementation preserves all fields from OpenAI responses, including
usage details like cached_tokens.
"""
from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any, Union

import openai
from openai import AsyncOpenAI

from ..openai_client import get_async_openai_client, OpenAIClientError
from .base import Provider, ResponseObject, ResponseRequest

logger = logging.getLogger(__name__)


class OpenAIProvider(Provider):
    """Provider wrapper for OpenAI's *Responses* endpoint with full field preservation."""

    def __init__(self) -> None:
        try:
            self.client: AsyncOpenAI = get_async_openai_client()
        except OpenAIClientError as e:
            raise RuntimeError(str(e)) from e
        logger.info("Using OpenAI SDK version %s", openai.__version__)

    # ------------------------------------------------------------------
    # Public  Provider interface
    # ------------------------------------------------------------------

    async def create_response(self, request: ResponseRequest) -> ResponseObject:
        print("[OPENAI] create_response called", flush=True)
        payload = self._build_api_request(request)
        print(f"[OPENAI] Payload: {payload}", flush=True)
        try:
            rsp = await self.client.responses.create(**payload)
        except Exception as exc:  # – re‑raised after mapping
            self._handle_openai_error(exc, request.model)
        
        # Debug: Log the raw response
        response_data = rsp.model_dump()
        print(f"[OPENAI] Got response with keys: {list(response_data.keys())}", flush=True)
        if "usage" in response_data:
            print(f"[OPENAI] Raw usage data: {response_data['usage']}", flush=True)
        
        result = self._to_response_object(response_data)
        print(f"[OPENAI] Returning ResponseObject with usage: {result.usage}", flush=True)
        # Also check the kwargs
        if hasattr(result, '__pydantic_extra__'):
            print(f"[OPENAI] Extra fields: {result.__pydantic_extra__}", flush=True)
        return result

    async def stream_response(self, request: ResponseRequest) -> AsyncIterator[str]:
        payload = self._build_api_request(request, stream=True)
        try:
            stream = await self.client.responses.create(**payload)
        except Exception as exc:
            self._handle_openai_error(exc, request.model)
        async for chunk in stream:
            yield json.dumps(chunk.model_dump())

    async def retrieve_response(self, response_id: str) -> ResponseObject:
        rsp = await self.client.responses.retrieve(response_id)
        return self._to_response_object(rsp.model_dump())

    async def delete_response(self, response_id: str) -> dict[str, Any]:
        await self.client.responses.delete(response_id)
        return {"id": response_id, "deleted": True}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_tools(tools: list[Union[str, dict]]) -> list[dict]:
        """Convert built‑in & function tools into the canonical structure."""
        normalized: list[dict] = []
        for tool in tools:
            if isinstance(tool, str):
                normalized.append({"type": tool.replace("_", "-")})
            else:
                # Ensure custom functions include the wrapper type
                if "function" in tool and tool.get("type") != "function":
                    tool = {"type": "function", "function": tool["function"]}
                normalized.append(tool)
        return normalized

    @staticmethod
    def _normalize_reasoning(reasoning: Union[dict, str, None]):
        if reasoning is None:
            return None
        if isinstance(reasoning, dict) and "level" in reasoning:
            level_map = {"low": "low", "medium": "medium", "high": "high"}
            return {"effort": level_map.get(reasoning["level"], "medium")}
        if isinstance(reasoning, str):
            return {"effort": reasoning}
        return reasoning

    def _build_api_request(
        self, request: ResponseRequest, *, stream: bool = False
    ) -> dict[str, Any]:
        """Transform a `ResponseRequest` into kwargs for the SDK call."""
        payload: dict[str, Any] = {"model": request.model}
        if stream:
            payload["stream"] = True

        # Copy all simple scalar/list fields when set
        simple_fields = (
            "input",
            "previous_response_id",
            "instructions",
            "tool_choice",
            "parallel_tool_calls",
            "store",
            "background",
            "include",
            "temperature",
            "top_p",
            "max_output_tokens",
            "truncation",
            "metadata",
            "response_format",
            "n",
            "presence_penalty",
            "frequency_penalty",
            "timeout",
        )
        for field in simple_fields:
            if (value := getattr(request, field, None)) is not None:
                payload[field] = value

        if request.tools:
            payload["tools"] = self._normalize_tools(request.tools)
        if (norm_reasoning := self._normalize_reasoning(request.reasoning)) is not None:
            payload["reasoning"] = norm_reasoning
        return payload

    @staticmethod
    def _to_response_object(data: dict) -> ResponseObject:
        """
        Convert OpenAI response to ResponseObject, preserving ALL fields
        including usage details like cached_tokens.
        """
        # Define the known fields that map to ResponseObject attributes
        known_fields = {
            "id", "object", "created", "model", "output", "tool_calls",
            "status", "incomplete_details", "choices", "data", "usage"
        }
        
        # Extract usage for convenience fields (but preserve the full object)
        usage = data.get("usage", {})
        print(f"[OPENAI DEBUG] Raw usage from OpenAI: {usage}", flush=True)
        print(f"[OPENAI DEBUG] Full data keys: {list(data.keys())}", flush=True)
        
        # Note: Responses API uses input_tokens/output_tokens instead of prompt_tokens/completion_tokens
        total_tokens = sum(
            usage.get(k, 0)
            for k in ("input_tokens", "output_tokens", "reasoning_tokens")
        )
        
        # Build the base response object
        response_obj = ResponseObject(
            id=data.get("id", ""),
            object=data.get("object", "response"),
            created=data.get("created_at", 0),  # Responses API uses created_at
            model=data.get("model", ""),
            output=data.get("output"),
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            reasoning_tokens=usage.get("reasoning_tokens", 0),
            tool_calls=data.get("tool_calls"),
            status=data.get("status", "completed"),
            incomplete_details=data.get("incomplete_details"),
            choices=data.get("choices"),
            data=data.get("data"),
            usage=usage,  # Pass through the complete usage object
        )
        
        # Add any extra fields not in the known set
        for key, value in data.items():
            if key not in known_fields and not hasattr(response_obj, key):
                setattr(response_obj, key, value)
        
        return response_obj

    def _handle_openai_error(self, exc: Exception, requested_model: str) -> None:
        if hasattr(exc, "status_code") and exc.status_code == 404:
            raise ValueError(f"Model '{requested_model}' not found") from exc
        logger.error("OpenAI API error: %s", exc)
        raise exc