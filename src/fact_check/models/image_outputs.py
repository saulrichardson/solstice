"""Pydantic models for image analysis outputs."""

from pydantic import BaseModel, Field, validator
from typing import Optional


class ImageAnalysisOutput(BaseModel):
    """Output from the image evidence analyzer."""
    
    supports_claim: bool = Field(
        ..., 
        description="Whether this image contains evidence that supports the claim"
    )
    
    image_description: str = Field(
        ...,
        min_length=10,
        description="Objective description of what the image contains"
    )
    
    evidence_found: Optional[str] = Field(
        None,
        description="Specific evidence found in the image that relates to the claim (if any)"
    )
    
    reasoning: str = Field(
        ...,
        min_length=10,
        description="Explanation of why the image does or doesn't support the claim"
    )
    
    confidence_notes: Optional[str] = Field(
        None,
        description="Any caveats, limitations, or confidence issues with the analysis"
    )
    
    @validator('evidence_found')
    def validate_evidence_consistency(cls, v, values):
        """Ensure evidence_found is provided when supports_claim is True."""
        if values.get('supports_claim') and not v:
            raise ValueError("evidence_found must be provided when supports_claim is True")
        return v
    
    @validator('reasoning')
    def validate_reasoning(cls, v, values):
        """Ensure the reasoning text is consistent with the decision.

        If the image is marked as supporting the claim we expect the word
        "support" (or a close variant) to appear in the explanation to make it
        explicit why the claim is supported.  Conversely, when the image does
        not support the claim we expect a negative phrasing such as "not
        support", "doesn't support", or "refute".  This lightweight heuristic
        catches obvious mismatches between the boolean flag and the free-text
        justification while still allowing flexible language.
        """
        supports_claim = values.get('supports_claim')
        reasoning_lc = v.lower()

        if supports_claim:
            if "support" not in reasoning_lc:
                raise ValueError("Reasoning must explicitly mention how the image supports the claim")
        else:
            negative_keywords = ["not support", "doesn't support", "does not support", "refute", "refutes"]
            if not any(kw in reasoning_lc for kw in negative_keywords):
                raise ValueError("Reasoning must explain why the image does not support the claim")
        return v
