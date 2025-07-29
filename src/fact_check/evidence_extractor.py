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
            # We explicitly set store=False so that OpenAI *does not* cache the
            # completion.  Without this flag the Responses API keeps an
            # internal copy and will serve identical requests instantly on
            # subsequent calls, which can hide legitimate issues during
            # development and debugging.
            response = await self.llm_client.create_response(
                input=prompt,
                model=self.llm_client.model if hasattr(self.llm_client, 'model') else "gpt-4.1",
                temperature=0.0,
                max_output_tokens=4000,
                disable_cache=self.config.get("disable_cache", False),
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
            # Use standardized extraction method - will raise ValueError if format is wrong
            from .core.responses_client import ResponsesClient
            content = ResponsesClient.extract_text(response)
            
            # Handle markdown-wrapped JSON
            if content.startswith('```json') and content.endswith('```'):
                content = content[7:-3].strip()
            elif content.startswith('```') and content.endswith('```'):
                content = content[3:-3].strip()
            
            # Handle case where LLM adds notes after JSON
            # Find the last closing brace of the JSON
            if content.count('{') > 0:
                # Find matching closing brace for the first opening brace
                brace_count = 0
                json_end = -1
                for i, char in enumerate(content):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break
                
                if json_end > 0 and json_end < len(content):
                    # Extract only the JSON part
                    json_content = content[:json_end]
                    extra_content = content[json_end:].strip()
                    if extra_content:
                        logger.warning(f"LLM added extra content after JSON: {extra_content[:100]}...")
                    content = json_content
            
            # Try to parse JSON with error recovery
            try:
                data = json.loads(content)
            except json.JSONDecodeError as je:
                logger.warning(f"JSON decode error: {je}")
                # Try to fix common issues
                # Remove trailing commas
                content_fixed = content.replace(',]', ']').replace(',}', '}')
                # Try again
                try:
                    data = json.loads(content_fixed)
                    logger.info("Successfully parsed JSON after fixing trailing commas")
                except:
                    # If still failing, try to extract snippets manually
                    logger.warning("Falling back to manual extraction")
                    data = self._extract_snippets_manually(content)
            
            # Handle case where LLM returns a list instead of dict
            if isinstance(data, list):
                logger.warning("LLM returned a list instead of dict, wrapping in snippets key")
                data = {"snippets": data}
            
            # Convert to our model with error handling for each snippet
            snippets = []
            for i, snippet_data in enumerate(data.get("snippets", [])):
                try:
                    # Ensure required fields
                    if not isinstance(snippet_data, dict):
                        logger.warning(f"Snippet {i} is not a dict, skipping")
                        continue
                    
                    quote = snippet_data.get("quote", "").strip()
                    relevance = snippet_data.get("relevance_explanation", "").strip()
                    
                    if not quote:
                        logger.warning(f"Snippet {i} has empty quote, skipping")
                        continue
                    
                    snippet = SupportingSnippet(
                        id=i + 1,
                        quote=quote,
                        relevance_explanation=relevance or "No explanation provided"
                    )
                    snippets.append(snippet)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse snippet {i}: {e}")
                    continue
            
            logger.info(f"Successfully parsed {len(snippets)} snippets from LLM response")
            return EvidenceExtractionOutput(snippets=snippets)
            
        except Exception as e:
            logger.error(f"Failed to parse extraction output: {e}")
            logger.debug(f"Response type: {type(response)}")
            if isinstance(response, dict):
                logger.debug(f"Response keys: {list(response.keys())}")
            return EvidenceExtractionOutput(snippets=[])
    
    def _extract_snippets_manually(self, content: str) -> Dict:
        """Fallback manual extraction when JSON parsing fails."""
        snippets = []
        
        # Look for quote patterns
        import re
        quote_pattern = r'"quote"\s*:\s*"([^"]+)"'
        relevance_pattern = r'"relevance_explanation"\s*:\s*"([^"]+)"'
        
        quotes = re.findall(quote_pattern, content)
        relevances = re.findall(relevance_pattern, content)
        
        # Pair them up
        for i, quote in enumerate(quotes):
            relevance = relevances[i] if i < len(relevances) else "Extracted from malformed response"
            snippets.append({
                "quote": quote,
                "relevance_explanation": relevance
            })
        
        logger.info(f"Manually extracted {len(snippets)} snippets from malformed JSON")
        return {"snippets": snippets}
    
