"""Agent for checking completeness of evidence extraction and finding missing evidence."""

import logging
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from .base import BaseAgent, AgentError
from ..core.responses_client import ResponsesClient
from ..models.llm_outputs import ExtractorOutput
from ..utils.llm_parser import LLMResponseParser

logger = logging.getLogger(__name__)


class CompletenessChecker(BaseAgent):
    """
    Check for missing evidence and extract additional snippets.
    
    This agent:
    1. Reviews existing validated evidence
    2. Analyzes the document for potentially missed evidence
    3. Extracts additional supporting quotes
    4. Ensures comprehensive coverage of the claim
    """
    
    @property
    def agent_name(self) -> str:
        return "completeness_checker"
    
    @property
    def required_inputs(self) -> List[str]:
        return [
            "extracted/content.json",
            f"agents/claims/{self.claim_id}/evidence_verifier_v2/output.json"
        ]
    
    def __init__(
        self, 
        pdf_name: str,
        claim_id: str,
        cache_dir: Path = Path("data/cache"),
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize completeness checker agent."""
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
        Check for missing evidence and extract additional snippets.
        
        Returns:
            Dictionary containing all evidence (existing + new)
        """
        logger.info(f"Checking evidence completeness for {self.claim_id}")
        
        # Get verified evidence
        verifier_path = self.pdf_dir / "agents" / "claims" / self.claim_id / "evidence_verifier_v2" / "output.json"
        verifier_data = self.load_json(verifier_path)
        
        # Load document
        content_path = self.pdf_dir / "extracted" / "content.json"
        document_data = self.load_json(content_path)
        
        # Import document utilities
        from ..utils import document_utils
        
        # Get normalized text using utility
        normalized_text = document_utils.get_text(document_data, include_figures=True)
        
        claim = self.config.get("claim")
        if not claim:
            raise AgentError("No claim provided in config")
        
        # Get existing evidence
        existing_snippets = verifier_data.get("verified_evidence", [])
        existing_quotes = [s.get("quote", "") for s in existing_snippets]
        
        # Check if there's any additional evidence we missed
        additional_snippets = await self._check_for_additional_evidence(
            claim=claim,
            document_text=normalized_text,
            existing_quotes=existing_quotes
        )
        
        # Combine all evidence (existing verified + new)
        all_snippets = existing_snippets + additional_snippets
        
        output = {
            "claim_id": self.claim_id,
            "claim": claim,
            "document": self.pdf_name,
            "additional_evidence_check": {
                "checked_for_more": True,
                "found_additional": len(additional_snippets) > 0,
                "additional_count": len(additional_snippets)
            },
            "completeness_stats": {
                "existing_evidence": len(existing_snippets),
                "new_evidence_found": len(additional_snippets),
                "total_evidence": len(all_snippets)
            },
            "verified_evidence": existing_snippets,    # Already verified evidence
            "new_evidence": additional_snippets,       # New evidence to be verified
            "model_used": self.llm_client.model
        }
        
        logger.info(
            f"Found {output['completeness_stats']['new_evidence_found']} additional snippets, "
            f"total: {output['completeness_stats']['total_evidence']}"
        )
        
        return output
    
    
    async def _check_for_additional_evidence(
        self, 
        claim: str, 
        document_text: str,
        existing_quotes: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Check if there's any additional supporting evidence we missed.
        
        Returns:
            List of new evidence snippets
        """
        # Show LLM what we already found
        existing_evidence_text = "\n".join([f"- {quote[:150]}..." for quote in existing_quotes[:10]])

        try:
            # Build the full prompt for finding additional evidence
            full_prompt = f'''Extract VERBATIM quotes from the document that support this claim.

Rules:
- Quotes must be exact text from the document (no modifications)
- No ellipsis (...) - extract complete segments
- Only return quotes that are DIFFERENT from the evidence already found
- A quote supports the claim if it provides evidence, data, or statements that directly relate to and affirm the claim

Standard for "supports the claim":
"Would this quote help convince a skeptical reader that the claim is true?"

CLAIM: {claim}

Note: You already found some evidence for this claim. Look for ANY ADDITIONAL quotes that support it.

EVIDENCE ALREADY FOUND:
{existing_evidence_text}

Find ANY OTHER quotes that support this claim that weren't already found.
Don't force it - if there's no additional evidence, that's fine.

Return your response as a JSON object:
{{
    "snippets": [
        {{
            "quote": "exact quote from document",
            "relevance_explanation": "1-2 sentences explaining how this supports the claim"
        }}
    ]
}}

DOCUMENT:
{document_text}'''

            # Call LLM directly using parser
            result = await LLMResponseParser.parse_with_retry(
                llm_client=self.llm_client,
                prompt=full_prompt,
                output_model=ExtractorOutput,
                max_retries=2,
                temperature=0.0,
                max_output_tokens=4000
            )
            
            # Process results - trust the LLM to not duplicate
            new_snippets = []
            for i, snippet in enumerate(result.snippets):
                new_snippet = {
                    "id": f"comp_{i+1}",
                    "quote": snippet.quote,
                    "relevance_explanation": snippet.relevance_explanation,
                    "source": "completeness_check",
                    "metadata": {
                        "extraction_round": 2,
                        "targeted_aspect": "general"
                    }
                }
                new_snippets.append(new_snippet)
            
            return new_snippets
            
        except Exception as e:
            logger.error(f"Error finding additional evidence: {e}")
            return []
    
    
    
