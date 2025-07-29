"""Agent for verifying extracted quotes exist in the document using regex."""

import re
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from difflib import SequenceMatcher

from .base import BaseAgent, AgentError

logger = logging.getLogger(__name__)


class RegexVerifier(BaseAgent):
    """Verify that extracted quotes actually exist in the document"""
    
    @property
    def agent_name(self) -> str:
        return "regex_verifier"
    
    @property
    def required_inputs(self) -> List[str]:
        # Support different upstream agents
        upstream = self.config.get("upstream_agent", "supporting_evidence")
        return [
            "extracted/content.json",
            f"agents/claims/{self.claim_id}/{upstream}/output.json"
        ]
    
    def __init__(
        self, 
        pdf_name: str,
        claim_id: str,
        cache_dir: Path = Path("data/cache"),
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize regex verifier agent."""
        super().__init__(pdf_name, cache_dir, config)
        self.claim_id = claim_id
        
        # Support multiple verification stages
        self.upstream_agent = self.config.get("upstream_agent", "supporting_evidence")
        self.input_field = self.config.get("input_field", "supporting_snippets")
        
        # Different output dirs for different stages
        suffix = "_final" if self.upstream_agent != "supporting_evidence" else ""
        self.agent_dir = self.pdf_dir / "agents" / "claims" / claim_id / f"{self.agent_name}{suffix}"
        self.agent_dir.mkdir(parents=True, exist_ok=True)
    
    async def process(self) -> Dict[str, Any]:
        """
        Verify extracted quotes using regex matching with fuzzy fallback.
        
        Returns:
            Dictionary containing verified snippets
        """
        logger.info(f"Verifying quotes for {self.claim_id} from {self.upstream_agent}")
        
        # Get evidence from upstream agent
        evidence_path = self.pdf_dir / "agents" / "claims" / self.claim_id / self.upstream_agent / "output.json"
        evidence_data = self.load_json(evidence_path)
        
        # Load document content
        content_path = self.pdf_dir / "extracted" / "content.json"
        document_data = self.load_json(content_path)
        
        # Import document utilities
        from ..utils import document_utils
        
        # Get normalized full text using utility
        full_text = document_utils.get_text(document_data, include_figures=True)
        
        # Process snippets
        snippets_to_verify = evidence_data.get(self.input_field, [])
        verified_snippets = []
        failed_snippets = []
        modified_snippets = []
        
        for snippet in snippets_to_verify:
            quote = snippet.get("quote", "")
            
            # Try exact match first
            exact_result = self._verify_exact(quote, full_text)
            if exact_result["found"]:
                snippet["verification_status"] = "exact_match"
                snippet["verified_location"] = exact_result["location"]
                verified_snippets.append(snippet)
            else:
                # Try fuzzy matching
                fuzzy_result = self._verify_fuzzy(quote, full_text)
                if fuzzy_result["found"]:
                    snippet["verification_status"] = "fuzzy_match"
                    snippet["original_quote"] = quote
                    snippet["verified_quote"] = fuzzy_result["matched_text"]
                    snippet["match_score"] = fuzzy_result["score"]
                    snippet["verified_location"] = fuzzy_result["location"]
                    verified_snippets.append(snippet)
                    modified_snippets.append(snippet)
                else:
                    snippet["verification_status"] = "failed"
                    snippet["failure_reason"] = "Quote not found in document"
                    failed_snippets.append(snippet)
        
        output = {
            "claim_id": self.claim_id,
            "claim": evidence_data.get("claim"),
            "document": self.pdf_name,
            "verification_stats": {
                "total_snippets": len(snippets_to_verify),
                "verified": len(verified_snippets),
                "failed": len(failed_snippets),
                "modified": len(modified_snippets),
                "exact_matches": len([s for s in verified_snippets if s["verification_status"] == "exact_match"]),
                "fuzzy_matches": len([s for s in verified_snippets if s["verification_status"] == "fuzzy_match"])
            },
            "verified_snippets": verified_snippets,
            "failed_snippets": failed_snippets
        }
        
        # If this is a completeness check, also include validated snippets from critic
        if self.input_field == "all_snippets" and "validated_snippets" in evidence_data:
            # These were already verified, so just pass them through
            for snippet in evidence_data.get("validated_snippets", []):
                if snippet not in verified_snippets:
                    snippet["verification_status"] = "previously_verified"
                    verified_snippets.append(snippet)
            output["verified_snippets"] = verified_snippets
            output["verification_stats"]["verified"] = len(verified_snippets)
        
        logger.info(
            f"Verified {output['verification_stats']['verified']} of "
            f"{output['verification_stats']['total_snippets']} snippets "
            f"({output['verification_stats']['exact_matches']} exact, "
            f"{output['verification_stats']['fuzzy_matches']} fuzzy)"
        )
        
        return output
    
    def _normalize_text(self, text: str) -> str:
        """Minimal text normalization for matching.
        
        Note: Most normalization is already done by ingestion pipeline.
        This only handles quote variations for better matching.
        """
        # Only normalize quote variations (not handled by ingestion)
        text = text.replace('"', '"').replace('"', '"').replace("'", "'").replace("'", "'")
        return text
    
    def _verify_exact(self, quote: str, document: str) -> Dict[str, Any]:
        """Verify exact match with normalized text."""
        normalized_quote = self._normalize_text(quote)
        normalized_doc = self._normalize_text(document)
        
        if normalized_quote in normalized_doc:
            start_pos = normalized_doc.find(normalized_quote)
            return {
                "found": True,
                "location": {
                    "start": start_pos,
                    "end": start_pos + len(normalized_quote)
                }
            }
        return {"found": False}
    
    def _verify_fuzzy(self, quote: str, document: str, threshold: float = 0.85) -> Dict[str, Any]:
        """
        Fuzzy match using sequence matching for robust verification.
        
        Returns:
            Dict with found status, matched text, score, and location
        """
        normalized_quote = self._normalize_text(quote)
        normalized_doc = self._normalize_text(document)
        
        # Skip if quote is too short
        if len(normalized_quote) < 20:
            return {"found": False}
        
        # Use sliding window with sequence matcher
        quote_len = len(normalized_quote)
        best_match = {"found": False, "score": 0}
        
        # Optimize by using word boundaries
        words = normalized_doc.split()
        quote_words = normalized_quote.split()
        quote_word_count = len(quote_words)
        
        # Slide through document by words for efficiency
        for i in range(len(words) - quote_word_count + 1):
            # Reconstruct text window
            window_words = words[i:i + quote_word_count + 5]  # Extra words for context
            window_text = " ".join(window_words)
            
            # Use SequenceMatcher for fuzzy matching
            matcher = SequenceMatcher(None, normalized_quote, window_text)
            
            # Find longest matching subsequence
            match = matcher.find_longest_match(0, len(normalized_quote), 0, len(window_text))
            
            if match.size > len(normalized_quote) * 0.8:  # At least 80% must match
                # Get the actual matched text
                matched_text = window_text[match.b:match.b + match.size]
                
                # Calculate similarity for the full quote
                full_matcher = SequenceMatcher(None, normalized_quote, matched_text)
                score = full_matcher.ratio()
                
                if score > best_match["score"] and score >= threshold:
                    # Calculate character position in original document
                    char_pos = len(" ".join(words[:i])) + (i if i > 0 else 0)
                    
                    best_match = {
                        "found": True,
                        "score": score,
                        "matched_text": matched_text,
                        "location": {
                            "start": char_pos,
                            "end": char_pos + len(matched_text)
                        }
                    }
        
        # If no good match found, try character-level sliding window for short quotes
        if not best_match["found"] and quote_len < 100:
            best_match = self._verify_fuzzy_char_level(normalized_quote, normalized_doc, threshold)
        
        return best_match
    
    def _verify_fuzzy_char_level(self, quote: str, document: str, threshold: float = 0.85) -> Dict[str, Any]:
        """Character-level fuzzy matching for short quotes."""
        quote_len = len(quote)
        best_match = {"found": False, "score": 0}
        
        # Slide through document
        for i in range(0, len(document) - quote_len + 1, 10):  # Step by 10 chars for efficiency
            window = document[i:i + quote_len + 50]  # Extra chars for flexibility
            
            matcher = SequenceMatcher(None, quote, window)
            match = matcher.find_longest_match(0, len(quote), 0, len(window))
            
            if match.size > len(quote) * 0.8:
                matched_text = window[match.b:match.b + match.size]
                score = SequenceMatcher(None, quote, matched_text).ratio()
                
                if score > best_match["score"] and score >= threshold:
                    best_match = {
                        "found": True,
                        "score": score,
                        "matched_text": matched_text,
                        "location": {
                            "start": i + match.b,
                            "end": i + match.b + match.size
                        }
                    }
        
        return best_match