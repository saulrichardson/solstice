"""LLM-powered refinement of raw LayoutParser boxes.

This module provides :func:`refine_page_layout` which takes the raw detection
output for a single page and asks an LLM (through the gateway) to:

1. Merge boxes that belong to the same logical element.
2. Tighten bounding-box coordinates where necessary.
3. Return explicit reading order indices.

The exchange contract is strict JSON so that the downstream pipeline can parse
the response deterministically.  Validation is done with *pydantic* and we
retry up to *N* times if the LLM fails to comply.
"""

from __future__ import annotations

import json
import logging
from typing import List, Sequence, Tuple

import base64
import io

from PIL import Image

from pydantic import BaseModel, Field, ValidationError

# from .llm_client import call_llm  # LLM agent removed from pipeline

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic schema used for validation of the LLM output
# ---------------------------------------------------------------------------


class Box(BaseModel):
    id: str
    bbox: Tuple[float, float, float, float]
    label: str = Field(..., description="Raw detector label, e.g. 'Table'")
    score: float = Field(..., ge=0, le=1)


class RefinedPage(BaseModel):
    boxes: List[Box]
    reading_order: List[str]
    page_index: int = 0
    detection_dpi: int = 200  # DPI at which detection was performed


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------


SYSTEM_PROMPT = """You are a document-layout expert.  You receive bounding boxes
detected by a computer-vision model and must merge or adjust them so they match
logical reading units in the PDF.  Respond *only* with valid JSON matching the
provided schema, no prose."""

USER_PROMPT_TEMPLATE = """
<<DETECTED_BOXES_JSON_START>>
{boxes_json}
<<DETECTED_BOXES_JSON_END>>

Tasks:
1. Merge boxes that belong to the same paragraph or caption.
2. Output tightened bounding-box coordinates for each final element.
3. Provide `reading_order` – an array of element *ids* in the order they should
   be read by a human.

Return JSON exactly matching this schema:
{{
  "boxes": [{{"id": "string", "bbox": [x1, y1, x2, y2], "label": "string", "score": 0-1}}],
  "reading_order": ["id", ...]
}}
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def refine_page_layout(
    page_index: int,
    raw_boxes: Sequence[Box],
    *,
    page_image: Image.Image,
    retries: int = 3,
    model: str = "gpt-4.1",
) -> RefinedPage:
    """Return an LLM-refined layout for a single page."""

    # 1. Prepare input JSON (pretty-printed improves model reliability)
    boxes_json = json.dumps([box.model_dump() for box in raw_boxes], indent=2)
    user_prompt = USER_PROMPT_TEMPLATE.format(boxes_json=boxes_json, page=page_index)

    last_error: Exception | None = None
    # Build input array for vision model: one text block containing instructions
    # followed by cropped images (data URLs) for each box.

    def _crop_to_data_url(bbox: Tuple[float, float, float, float]) -> str:
        x1, y1, x2, y2 = map(int, bbox)
        crop = page_image.crop((x1, y1, x2, y2))
        buf = io.BytesIO()
        crop.save(buf, format="PNG")
        encoded = base64.b64encode(buf.getvalue()).decode()
        return f"data:image/png;base64,{encoded}"

    # For Responses API, we need to format images with "input_image" type
    image_blocks = [
        {
            "type": "image_url",
            "image_url": {"url": _crop_to_data_url(b.bbox), "detail": "low"},
        }
        for b in raw_boxes
    ]

    # Combine text and images in the content array
    input_blocks = [
        {"type": "text", "text": user_prompt},
        *image_blocks,
    ]

    for attempt in range(1, retries + 1):
        try:
            reply = call_llm(
                system_prompt=SYSTEM_PROMPT,
                user_content=input_blocks,  # list of content blocks
                model=model,
                temperature=0.3,
            )
            refined = RefinedPage.model_validate_json(reply)
            logger.debug("Refined layout for page %d obtained in %d attempt(s)", page_index, attempt)
            return refined
        except (ValidationError, ValueError) as exc:
            logger.warning("LLM returned invalid JSON on attempt %d/%d: %s", attempt, retries, exc)
            last_error = exc

    raise RuntimeError("Failed to obtain valid refined layout after retries") from last_error
