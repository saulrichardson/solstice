"""Evidence extraction logic for finding supporting text snippets for claims."""

import json
from typing import Dict, List, Optional
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


# Data models
class SupportingSnippet(BaseModel):
    """A text snippet that supports a claim"""
    id: int
    quote: str
    relevance_explanation: str
    context: Optional[str] = None  # Surrounding text for context
    start: Optional[int] = None  # Character position in document
    end: Optional[int] = None
    page_index: Optional[int] = None


class EvidenceExtractionOutput(BaseModel):
    """Output from the evidence extractor LLM"""
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
    
    def __init__(self, llm_client):
        """
        Initialize the evidence extractor.
        
        Args:
            llm_client: Client for LLM interactions (ResponsesClient)
        """
        self.llm_client = llm_client
        
    async def extract_supporting_evidence(self, claim: str, document_text: str) -> EvidenceExtractionResult:
        """
        Extract all text snippets that support the given claim.
        
        Args:
            claim: The claim to find evidence for
            document_text: The full document text to search
            
        Returns:
            EvidenceExtractionResult containing all supporting snippets
        """
        try:
            # Step 1: Use LLM to find supporting snippets
            extraction_output = await self._extract_snippets(claim, document_text)
            
            # Step 2: Verify quotes exist in document
            verified_snippets = self._verify_snippets(extraction_output.snippets, document_text)
            
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
        prompt = f'''You are an evidence extraction system. Your task is to find all text snippets 
in the document that provide evidence supporting the following claim.

Claim: {claim}

Instructions:
1. Search through the entire document for text that supports or is relevant to this claim
2. Extract exact quotes (word-for-word) from the document
3. For each quote, explain why it supports or relates to the claim
4. Include surrounding context if helpful
5. Find ALL relevant snippets, not just the first one

Return your response as a JSON object with this structure:
{{
    "snippets": [
        {{
            "id": 1,
            "quote": "exact text from document",
            "relevance_explanation": "why this quote supports the claim",
            "context": "optional surrounding text for context"
        }},
        ...
    ]
}}

Document:
{document_text[:50000]}  # Limit to first 50k chars for context window

Find all supporting evidence for the claim.'''

        try:
            response = await self.llm_client.create_response(
                input=prompt,
                model=self.llm_client.model if hasattr(self.llm_client, 'model') else "gpt-4.1",
                temperature=0.0,
                max_output_tokens=4000
            )
            
            # Parse response
            return self._parse_extraction_output(response)
            
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            # Return empty result on failure
            return EvidenceExtractionOutput(snippets=[])
    
    def _parse_extraction_output(self, response: Dict) -> EvidenceExtractionOutput:
        """Parse LLM response into EvidenceExtractionOutput."""
        try:
            # Extract content from response
            content = response.get("output_text", "")
            if not content:
                content = response.get("output", {}).get("content", "")
                
            if not content:
                logger.error(f"No content found in response output: {response}")
                return EvidenceExtractionOutput(snippets=[])
            
            # Handle markdown-wrapped JSON
            if content.startswith('```json') and content.endswith('```'):
                content = content[7:-3].strip()
            elif content.startswith('```') and content.endswith('```'):
                content = content[3:-3].strip()
                
            data = json.loads(content)
            
            # Handle case where LLM returns a list instead of dict
            if isinstance(data, list):
                logger.warning("LLM returned a list instead of dict, wrapping in snippets key")
                data = {"snippets": data}
            
            # Convert to our model
            snippets = []
            for i, snippet_data in enumerate(data.get("snippets", [])):
                # Ensure required fields
                if not isinstance(snippet_data, dict):
                    continue
                    
                snippet = SupportingSnippet(
                    id=snippet_data.get("id", i + 1),
                    quote=snippet_data.get("quote", ""),
                    relevance_explanation=snippet_data.get("relevance_explanation", ""),
                    context=snippet_data.get("context")
                )
                
                if snippet.quote:  # Only add if quote is not empty
                    snippets.append(snippet)
            
            return EvidenceExtractionOutput(snippets=snippets)
            
        except Exception as e:
            logger.error(f"Failed to parse extraction output: {e}")
            logger.error(f"Response was: {response}")
            return EvidenceExtractionOutput(snippets=[])
    
    def _verify_snippets(self, snippets: List[SupportingSnippet], document_text: str) -> List[SupportingSnippet]:
        """
        Verify that snippets actually exist in the document and add position info.
        
        Args:
            snippets: List of extracted snippets
            document_text: The document text
            
        Returns:
            List of verified snippets with position information
        """
        verified = []
        
        for snippet in snippets:
            # Skip empty quotes
            if not snippet.quote or not snippet.quote.strip():
                logger.warning(f"Skipping empty quote in snippet {snippet.id}")
                continue
                
            # Find the quote in the document
            position = document_text.find(snippet.quote)
            
            if position == -1:
                # Try with normalized whitespace
                normalized_quote = " ".join(snippet.quote.split())
                normalized_doc = " ".join(document_text.split())
                position = normalized_doc.find(normalized_quote)
                
                if position == -1:
                    logger.warning(f"Quote not found in document: {snippet.quote[:50]}...")
                    continue
                
                # Adjust position for original document
                # This is approximate due to whitespace normalization
                snippet.quote = normalized_quote
            
            # Add position information
            snippet.start = position
            snippet.end = position + len(snippet.quote)
            
            verified.append(snippet)
        
        return verified