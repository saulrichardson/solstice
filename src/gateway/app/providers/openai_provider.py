"""
OpenAIProvider aligned strictly with latest openai>=1.24 Responses API; no legacy shims.

This implementation assumes the SDK always returns the modern schema with
`output`, `usage`, etc., so no compatibility layers are required.
"""
from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator, Dict, List, Union

import openai
from openai import AsyncOpenAI

from .base import Provider, ResponseRequest, ResponseObject
from ..config import settings

logger = logging.getLogger(__name__)


class OpenAIProvider(Provider):
    """Provider wrapper for OpenAI's *Responses* endpoint (latest schema only)."""

    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        self.client: AsyncOpenAI = AsyncOpenAI(api_key=settings.openai_api_key)
        logger.info("Using OpenAI SDK version %s", openai.__version__)

    # ------------------------------------------------------------------
    # Public  Provider interface
    # ------------------------------------------------------------------

    async def create_response(self, request: ResponseRequest) -> ResponseObject:
        payload = self._build_api_request(request)
        try:
            rsp = await self.client.responses.create(**payload)
        except Exception as exc:  # noqa: BLE001 – re‑raised after mapping
            self._handle_openai_error(exc, request.model)
        return self._to_response_object(rsp.model_dump())

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
    def _normalize_tools(tools: List[Union[str, dict]]) -> List[dict]:
        """Convert built‑in & function tools into the canonical structure."""
        normalized: List[dict] = []
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

    def _build_api_request(self, request: ResponseRequest, *, stream: bool = False) -> Dict[str, Any]:
        """Transform a `ResponseRequest` into kwargs for the SDK call."""
        payload: Dict[str, Any] = {"model": request.model}
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
        usage = data.get("usage", {})
        total_tokens = sum(usage.get(k, 0) for k in ("prompt_tokens", "completion_tokens", "reasoning_tokens"))
        return ResponseObject(
            id=data.get("id", ""),
            object=data.get("object", "response"),
            created=data.get("created", 0),
            model=data.get("model", ""),
            output=data.get("output"),
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            reasoning_tokens=usage.get("reasoning_tokens", 0),
            tool_calls=data.get("tool_calls"),
            status=data.get("status", "completed"),
            incomplete_details=data.get("incomplete_details"),
            choices=data.get("choices"),
            data=data.get("data"),
            usage={
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0),
                "reasoning_tokens": usage.get("reasoning_tokens", 0),
                "total_tokens": total_tokens,
            },
        )

    def _handle_openai_error(self, exc: Exception, requested_model: str) -> None:  # noqa: D401
        if hasattr(exc, "status_code") and exc.status_code == 404:
            raise ValueError(f"Model '{requested_model}' not found") from exc
        logger.error("OpenAI API error: %s", exc)
        raise exc

