"""Evidence extraction logic for finding supporting text snippets for claims."""

import json
from typing import Dict, List, Optional
from pydantic import BaseModel
import logging

from .models.llm_outputs import ExtractorOutput, ExtractorSnippet
from .utils.llm_parser import LLMResponseParser

logger = logging.getLogger(__name__)


# Data models
class SupportingSnippet(BaseModel):
    """A text snippet that supports a claim"""
    id: int
    quote: str
    relevance_explanation: str


class EvidenceExtractionOutput(BaseModel):
    """Internal output format with IDs"""
    snippets: List[SupportingSnippet]


class EvidenceExtractionResult(BaseModel):
    """Result from the evidence extraction process"""
    claim: str
    success: bool
    supporting_snippets: List[SupportingSnippet] = []
    total_snippets_found: int = 0
    error: Optional[str] = None


class EvidenceExtractor:
    """Extract supporting evidence snippets for claims from documents"""
    
    def __init__(self, llm_client, config=None):
        """
        Initialize the evidence extractor.
        
        Args:
            llm_client: Client for LLM interactions (ResponsesClient)
            config: Optional configuration dict
        """
        self.llm_client = llm_client
        self.config = config or {}
        
    async def extract_supporting_evidence(self, claim: str, document_text: str) -> EvidenceExtractionResult:
        """
        Extract all text snippets that support the given claim.
        
        Args:
            claim: The claim to find evidence for
            document_text: The normalized document text to search
            
        Returns:
            EvidenceExtractionResult containing all supporting snippets
        """
        try:
            # Step 1: Use LLM to find supporting snippets
            extraction_output = await self._extract_snippets(claim, document_text)
            
            # Step 2: Return extracted snippets directly (no verification needed)
            verified_snippets = extraction_output.snippets
            
            # Step 3: Return results
            return EvidenceExtractionResult(
                claim=claim,
                success=True,
                supporting_snippets=verified_snippets,
                total_snippets_found=len(verified_snippets)
            )
            
        except Exception as e:
            logger.error(f"Failed to extract evidence: {e}")
            return EvidenceExtractionResult(
                claim=claim,
                success=False,
                error=str(e)
            )
    
    async def _extract_snippets(self, claim: str, document_text: str) -> EvidenceExtractionOutput:
        """
        Use LLM to extract supporting snippets.
        
        Args:
            claim: The claim to find evidence for
            document_text: The document text
            
        Returns:
            EvidenceExtractionOutput from the LLM
        """
        prompt = f'''Extract VERBATIM quotes from the document that support this claim.

Rules:
- Quotes must be exact text from the document (no modifications)
- No ellipsis (...) - extract complete segments
- A quote supports the claim if it provides evidence, data, or statements that directly relate to and affirm the claim

CLAIM: {claim}

Return your response as a JSON object with this structure:
{{
    "snippets": [
        {{
            "quote": "exact text from document",
            "relevance_explanation": "why this quote supports the claim"
        }},
        ...
    ]
}}

Document text to search:'''
        
        # Always pass complete document - no truncation
        prompt += f"\n{document_text}"
        
        if len(document_text) > 100000:
            logger.info(f"Processing large document ({len(document_text):,} characters)")

        try:
            # Use the robust parser with retry
            result = await LLMResponseParser.parse_with_retry(
                llm_client=self.llm_client,
                prompt=prompt,
                output_model=ExtractorOutput,
                max_retries=2,
                temperature=0.0,
                max_output_tokens=4000
            )
            
            return result
            
        except ValueError as e:
            logger.error(f"Failed to extract evidence after retries: {e}")
            # Return empty result on failure
            return ExtractorOutput(snippets=[])