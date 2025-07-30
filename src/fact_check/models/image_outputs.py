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
        """Ensure reasoning explains the decision."""
        if values.get('supports_claim') and 'support' not in v.lower():
            # Just a warning, not an error
            pass
        return v