"""Agent for verifying that quotes exist in documents using LLM."""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from ..utils import document_utils
from ..core.responses_client import ResponsesClient
from .base import BaseAgent, AgentError

logger = logging.getLogger(__name__)


class QuoteVerification(BaseModel):
    """Result of verifying a single quote."""
    found: bool
    confidence: str  # "high", "medium", "low"
    actual_text: Optional[str] = None
    differences: List[str] = []


class QuoteVerifier(BaseAgent):
    """Verify that quotes from supporting evidence exist in documents."""
    
    @property
    def agent_name(self) -> str:
        return "quote_verifier"
    
    @property
    def required_inputs(self) -> List[str]:
        # Need the document and supporting evidence output
        return ["extracted/content.json", "agents/claims/{claim_id}/supporting_evidence/output.json"]
    
    def __init__(
        self, 
        pdf_name: str,
        claim_id: str,
        cache_dir: Path = Path("data/cache"),
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize quote verifier agent.
        
        Args:
            pdf_name: Name of the PDF document
            claim_id: ID of the claim being processed (e.g., "claim_001")
            cache_dir: Base cache directory
            config: Agent configuration
        """
        super().__init__(pdf_name, cache_dir, config)
        self.claim_id = claim_id
        
        # Override agent directory to be claim-specific
        self.agent_dir = self.pdf_dir / "agents" / "claims" / claim_id / self.agent_name
        self.agent_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up LLM client
        self.llm_client = ResponsesClient()
        self.llm_client.model = self.config.get("model", "gpt-4.1")
    
    async def process(self) -> Dict[str, Any]:
        """
        Verify quotes from supporting evidence.
        
        Returns:
            Dictionary containing verification results
        """
        # Get the claim text from config
        claim = self.config.get("claim")
        if not claim:
            raise AgentError("No claim provided in config")
        
        # Load supporting evidence output
        evidence_path = self.pdf_dir / "agents" / "claims" / self.claim_id / "supporting_evidence" / "output.json"
        if not evidence_path.exists():
            raise AgentError(f"Supporting evidence not found at {evidence_path}")
        
        evidence_data = self.load_json(evidence_path)
        
        # Load document content
        content_path = self.pdf_dir / "extracted" / "content.json"
        document_data = self.load_json(content_path)
        
        # Get document text
        full_text = document_utils.get_text(document_data, include_figures=True)
        
        # Verify each quote
        verified_snippets = []
        failed_snippets = []
        
        for snippet in evidence_data.get("supporting_snippets", []):
            quote = snippet["quote"]
            
            # Find relevant chunk for this quote
            chunk = self._find_relevant_chunk(quote, full_text)
            
            # Verify with LLM
            verification = self._verify_quote(quote, chunk)
            
            # Build result
            snippet_result = {
                "id": snippet["id"],
                "quote": quote,
                "relevance_explanation": snippet["relevance_explanation"],
                "verification_status": "verified" if verification.found else "failed",
                "confidence": verification.confidence
            }
            
            if verification.found:
                if verification.actual_text:
                    snippet_result["actual_text"] = verification.actual_text
                if verification.differences:
                    snippet_result["differences"] = verification.differences
                verified_snippets.append(snippet_result)
            else:
                snippet_result["failure_reason"] = "Quote not found in document"
                failed_snippets.append(snippet_result)
        
        # Build output
        output = {
            "claim_id": self.claim_id,
            "claim": claim,
            "document": self.pdf_name,
            "verification_stats": {
                "total_snippets": len(evidence_data.get("supporting_snippets", [])),
                "verified": len(verified_snippets),
                "failed": len(failed_snippets),
                "high_confidence": sum(1 for s in verified_snippets if s["confidence"] == "high"),
                "medium_confidence": sum(1 for s in verified_snippets if s["confidence"] == "medium"),
                "low_confidence": sum(1 for s in verified_snippets if s["confidence"] == "low")
            },
            "verified_snippets": verified_snippets,
            "failed_snippets": failed_snippets,
            "model_used": self.llm_client.model
        }
        
        # Save output directly (BaseAgent expects this)
        self.save_outputs({"output.json": output})
        
        return output
    
    def _find_relevant_chunk(self, quote: str, full_text: str, chunk_size: int = 1000) -> str:
        """
        Find a relevant chunk of text that might contain the quote.
        
        Args:
            quote: The quote to find
            full_text: The full document text
            chunk_size: Size of chunk to extract
            
        Returns:
            Relevant text chunk
        """
        # Extract key terms from quote (simple approach)
        # Take first 3-5 significant words
        words = quote.split()
        key_terms = []
        for word in words:
            if len(word) > 4 and word.lower() not in ['that', 'this', 'with', 'from', 'have']:
                key_terms.append(word.lower())
            if len(key_terms) >= 3:
                break
        
        # If no good keywords, use first few words
        if not key_terms:
            key_terms = [w.lower() for w in words[:3]]
        
        # Find best matching position
        text_lower = full_text.lower()
        best_pos = -1
        best_score = 0
        
        # Sliding window search
        for i in range(0, len(full_text) - chunk_size, chunk_size // 2):
            chunk = text_lower[i:i + chunk_size]
            score = sum(1 for term in key_terms if term in chunk)
            if score > best_score:
                best_score = score
                best_pos = i
        
        # If we found a good match, use it
        if best_pos >= 0:
            # Extend chunk boundaries to word boundaries
            start = max(0, best_pos - 100)
            end = min(len(full_text), best_pos + chunk_size + 100)
            
            # Find word boundaries
            while start > 0 and full_text[start] not in ' \n':
                start -= 1
            while end < len(full_text) and full_text[end] not in ' \n':
                end += 1
            
            return full_text[start:end].strip()
        
        # Fallback: return a chunk from the middle of the document
        mid = len(full_text) // 2
        start = max(0, mid - chunk_size // 2)
        end = min(len(full_text), mid + chunk_size // 2)
        return full_text[start:end].strip()
    
    def _verify_quote(self, quote: str, chunk: str) -> QuoteVerification:
        """
        Use LLM to verify if quote exists in chunk.
        
        Args:
            quote: The quote to verify
            chunk: The document chunk to search in
            
        Returns:
            QuoteVerification result
        """
        prompt = f'''Verify if this quote appears in the document text below.

QUOTE TO VERIFY:
"{quote}"

DOCUMENT TEXT:
{chunk}

Is this quote present in the document? Consider:
- Minor spacing differences (e.g., "HAproteins" vs "HA proteins")
- Punctuation variations
- Ligature differences (ﬁ vs fi, ﬂ vs fl)
- Unicode differences (different types of dashes, quotes)

The quote should convey the same meaning, even if not character-for-character identical.

Return your response as JSON:
{{
    "found": true or false,
    "confidence": "high" or "medium" or "low",
    "actual_text": "exact text as it appears in document" (only if found),
    "differences": ["list of minor differences noted"] (only if found and there are differences)
}}'''

        try:
            response = self.llm_client.create_response(
                input=prompt,
                model=self.llm_client.model,
                temperature=0.0,
                max_output_tokens=1000,
                disable_cache=self.config.get("disable_cache", True)
            )
            
            # Parse response
            content = ResponsesClient.extract_text(response)
            
            # Handle markdown-wrapped JSON
            if content.startswith('```json') and content.endswith('```'):
                content = content[7:-3].strip()
            elif content.startswith('```') and content.endswith('```'):
                content = content[3:-3].strip()
            
            # Parse JSON
            data = json.loads(content)
            
            return QuoteVerification(
                found=data.get("found", False),
                confidence=data.get("confidence", "low"),
                actual_text=data.get("actual_text"),
                differences=data.get("differences", [])
            )
            
        except Exception as e:
            logger.error(f"Failed to verify quote: {e}")
            # Default to not found on error
            return QuoteVerification(
                found=False,
                confidence="low",
                differences=[f"Verification error: {str(e)}"]
            )