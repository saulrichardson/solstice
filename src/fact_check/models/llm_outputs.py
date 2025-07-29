"""Pydantic models for LLM outputs in fact-checking system."""

from pydantic import BaseModel, Field, validator
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class ExtractorSnippet(BaseModel):
    """A single evidence snippet from the extractor."""
    quote: str = Field(..., min_length=1, description="Exact quote from document")
    relevance_explanation: str = Field(..., min_length=1, description="Why this quote supports the claim")


class ExtractorOutput(BaseModel):
    """Output from the evidence extractor LLM."""
    snippets: List[ExtractorSnippet] = Field(default_factory=list, description="List of supporting quotes")


class VerifierOutput(BaseModel):
    """Output from the evidence verifier LLM."""
    quote_found: bool = Field(..., description="Whether the quote was found in the document")
    found_explanation: str = Field(..., min_length=1, description="Explanation of whether/where the quote appears")
    supports_claim: bool = Field(..., description="Whether the quote supports the claim")
    support_explanation: str = Field(..., min_length=1, description="Explanation of why it does/doesn't support")
    
    @validator('support_explanation')
    def validate_support_explanation(cls, v, values):
        """Validate that support explanation makes sense given quote_found status."""
        if not values.get('quote_found') and v and 'not found' not in v.lower() and 'cannot evaluate' not in v.lower():
            # Be lenient - just log warning
            logger.warning("Quote not found but support_explanation doesn't mention this")
        return v