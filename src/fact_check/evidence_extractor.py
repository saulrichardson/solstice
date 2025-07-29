"""Evidence extraction logic for finding supporting text snippets for claims."""

import json
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel
import logging
import difflib

logger = logging.getLogger(__name__)


# Data models
class SupportingSnippet(BaseModel):
    """A text snippet that supports a claim"""
    id: int
    quote: str
    relevance_explanation: str
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
    
    def __init__(self, llm_client, config=None):
        """
        Initialize the evidence extractor.
        
        Args:
            llm_client: Client for LLM interactions (ResponsesClient)
            config: Optional configuration dict
        """
        self.llm_client = llm_client
        self.config = config or {}
        
    def extract_supporting_evidence(self, claim: str, document_text: str) -> EvidenceExtractionResult:
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
            extraction_output = self._extract_snippets(claim, document_text)
            
            # Step 2: Verify quotes and find positions in the same normalized text
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
    
    def _extract_snippets(self, claim: str, document_text: str) -> EvidenceExtractionOutput:
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
        
        # Handle long documents by warning and using what we can
        if len(document_text) > 50000:
            logger.warning(
                f"Document is {len(document_text)} characters, truncating to 50k for LLM context window. "
                f"Evidence beyond character 50,000 may be missed."
            )
            prompt += f"\n{document_text[:50000]}\n\n[Document truncated - showing first 50,000 of {len(document_text)} characters]"
        else:
            prompt += f"\n{document_text}"

        try:
            # We explicitly set store=False so that OpenAI *does not* cache the
            # completion.  Without this flag the Responses API keeps an
            # internal copy and will serve identical requests instantly on
            # subsequent calls, which can hide legitimate issues during
            # development and debugging.
            response = self.llm_client.create_response(
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
    
    def _verify_snippets(self, snippets: List[SupportingSnippet], document_text: str) -> List[SupportingSnippet]:
        """
        Verify that snippets exist in the document text and find their positions.
        
        Args:
            snippets: List of extracted snippets
            document_text: The normalized document text
            
        Returns:
            List of verified snippets with position information
        """
        verified = []
        
        for snippet in snippets:
            # Skip empty quotes
            if not snippet.quote or not snippet.quote.strip():
                logger.warning(f"Skipping empty quote in snippet {snippet.id}")
                continue
            
            # Try exact match first
            position = document_text.find(snippet.quote)
            
            if position != -1:
                # Exact match found
                snippet.start = position
                snippet.end = position + len(snippet.quote)
                verified.append(snippet)
                logger.debug(f"Found quote (exact match) at position {position}")
            else:
                # Try fuzzy match as fallback
                match_result = self._fuzzy_find_quote(snippet.quote, document_text)
                
                if match_result is not None:
                    position, matched_text, similarity = match_result
                    snippet.start = position
                    snippet.end = position + len(matched_text)
                    verified.append(snippet)
                    logger.info(f"Found quote (fuzzy match, {similarity:.1%} similar) at position {position}")
                    if similarity < 0.95:
                        logger.debug(f"Original: {snippet.quote[:100]}")
                        logger.debug(f"Matched:  {matched_text[:100]}")
                else:
                    # Quote not found even with fuzzy match - this is likely hallucination
                    logger.warning(f"Quote not found in document (hallucination): {snippet.quote[:50]}...")
                    logger.debug(f"Full quote: {snippet.quote}")
                    logger.debug(f"Relevance explanation: {snippet.relevance_explanation}")
        
        logger.info(f"Verified {len(verified)}/{len(snippets)} snippets")
        return verified
    
    def _fuzzy_find_quote(self, quote: str, text: str, threshold: float = 0.85) -> Optional[Tuple[int, str, float]]:
        """
        Find a quote in text using fuzzy matching.
        
        This handles cases where the LLM adds spaces to concatenated words.
        E.g., "HAproteins" in text vs "HA proteins" in quote.
        
        Args:
            quote: The quote to find
            text: The text to search in
            threshold: Minimum similarity ratio (0.0 to 1.0)
            
        Returns:
            Tuple of (position, matched_text, similarity) or None if not found
        """
        # First, try a simpler approach: remove all spaces and compare
        quote_no_space = quote.replace(" ", "").lower()
        text_lower = text.lower()
        
        # Look for the spaceless version
        pos = text_lower.replace(" ", "").find(quote_no_space)
        if pos != -1:
            # Found it! Now find the actual position in the original text
            # Count characters up to this position
            char_count = 0
            actual_pos = 0
            for i, char in enumerate(text):
                if char != ' ':
                    if char_count == pos:
                        actual_pos = i
                        break
                    char_count += 1
            
            # Extract the matching text with original spacing
            end_pos = actual_pos
            matched_chars = 0
            for i in range(actual_pos, len(text)):
                if text[i] != ' ':
                    matched_chars += 1
                if matched_chars >= len(quote_no_space):
                    end_pos = i + 1
                    break
            
            matched_text = text[actual_pos:end_pos]
            return (actual_pos, matched_text, 0.92)  # High confidence for space-only differences
        
        # If that didn't work, fall back to sliding window (but with optimization)
        quote_len = len(quote)
        
        # Only check ±10% length variation (spaces don't add that much)
        window_len = quote_len
        
        # Use a step size for long quotes to speed up
        step = max(1, quote_len // 10)
        
        best_ratio = 0.0
        best_pos = -1
        best_match = ""
        
        for i in range(0, len(text) - window_len + 1, step):
            candidate = text[i:i + window_len]
            
            # Quick check: if first few characters are very different, skip
            if len(quote) > 10 and quote[:3].lower() != candidate[:3].lower():
                continue
            
            # Use sequence matcher for similarity
            matcher = difflib.SequenceMatcher(None, quote.lower(), candidate.lower())
            ratio = matcher.ratio()
            
            if ratio > best_ratio:
                best_ratio = ratio
                best_pos = i
                best_match = candidate
                
                # If we found a great match, refine the position
                if ratio >= 0.85:
                    # Check positions around this one
                    for j in range(max(0, i - step), min(len(text) - window_len + 1, i + step)):
                        candidate2 = text[j:j + window_len]
                        matcher2 = difflib.SequenceMatcher(None, quote, candidate2)
                        ratio2 = matcher2.ratio()
                        if ratio2 > best_ratio:
                            best_ratio = ratio2
                            best_pos = j
                            best_match = candidate2
            
            # Early exit if we found a very good match
            if best_ratio >= 0.95:
                break
        
        # Return best match if above threshold
        if best_ratio >= threshold:
            return (best_pos, best_match, best_ratio)
        
        return None
