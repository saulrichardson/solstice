"""Box data model for layout detection."""

from typing import Tuple
from pydantic import BaseModel, Field


class Box(BaseModel):
    """Represents a detected layout element with bounding box."""
    id: str
    bbox: Tuple[float, float, float, float]  # (x1, y1, x2, y2)
    label: str = Field(..., description="Element type, e.g. 'Text', 'Table', 'Figure'")
    # Score is optional when boxes are created by hand (e.g. in unit-tests).
    score: float = Field(
        1.0,
        ge=0,
        le=1,
        description="Detection confidence score.  Defaults to 1.0 when omitted.",
    )

    # Page index is useful for multi-page processing but should not be
    # mandatory in every context (e.g. algorithm-level unit-tests that only
    # need geometric information).  We therefore keep it optional.
    page_index: int | None = Field(
        default=None,
        description="Zero-based index of the page the box belongs to (optional)",
    )
