"""Box data model for layout detection."""

from typing import Tuple
from pydantic import BaseModel, Field


class Box(BaseModel):
    """Represents a detected layout element with bounding box."""
    id: str
    bbox: Tuple[float, float, float, float]  # (x1, y1, x2, y2)
    label: str = Field(..., description="Element type, e.g. 'Text', 'Table', 'Figure'")
    score: float = Field(..., ge=0, le=1, description="Detection confidence score")