"""Box data model for layout detection."""

from typing import Tuple

# Pydantic v2
from pydantic import BaseModel, Field, field_validator


class Box(BaseModel):
    """Represents a detected layout element with bounding box."""
    id: str
    bbox: Tuple[float, float, float, float]  # (x1, y1, x2, y2)
    label: str = Field(..., description="Element type, e.g. 'Text', 'Table', 'Figure'")
    # Score is optional when boxes are created by hand (e.g. in unit-tests).
    # Detectors occasionally emit scores slightly above 1 due to floating
    # point artefacts.  We therefore *accept* any non-negative value but clip
    # it into the conventional [0, 1] range on model creation rather than
    # failing validation.

    score: float = Field(
        1.0,
        ge=0.0,
        description="Detection confidence score clipped to [0, 1] on input.",
    )

    # Page index is useful for multi-page processing but should not be
    # mandatory in every context (e.g. algorithm-level unit-tests that only
    # need geometric information).  We therefore keep it optional.
    page_index: int | None = Field(
        default=None,
        description="Zero-based index of the page the box belongs to (optional)",
    )

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @field_validator("score", mode="before")
    @classmethod
    def _clip_score(cls, v: float):  # noqa: D401 – short validator name
        """Clip incoming score into the [0, 1] interval.

        The function is executed *before* other validations, ensuring that
        subsequent ge/Range checks always pass.
        """

        # Guard against None even though the field is required with default
        if v is None:
            return 1.0
        return max(0.0, min(float(v), 1.0))
