"""Agent for verifying evidence existence AND applicability to claims."""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..core.responses_client import ResponsesClient
from ..utils import document_utils
from ..models.llm_outputs import VerifierOutput
from ..utils.llm_parser import LLMResponseParser
from .base import BaseAgent, AgentError

logger = logging.getLogger(__name__)


class EvidenceVerifierV2(BaseAgent):
    """
    Verify that extracted quotes exist in the document AND genuinely support the claim.
    
    This agent combines quote verification with relevance checking, using the standard:
    "Would this evidence convince a skeptical reader?"
    """
    
    @property
    def agent_name(self) -> str:
        return "evidence_verifier_v2"
    
    @property
    def required_inputs(self) -> List[str]:
        return [
            "extracted/content.json",
            f"agents/claims/{self.claim_id}/evidence_extractor/output.json"
        ]
    
    def __init__(
        self, 
        pdf_name: str,
        claim_id: str,
        cache_dir: Path = Path("data/cache"),
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize evidence verifier agent."""
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
        Verify evidence existence and applicability.
        
        Returns:
            Dictionary containing verified and rejected evidence
        """
        logger.info(f"Verifying evidence for {self.claim_id}")
        
        # Find the most recent extractor output (could be from a loop)
        extractor_path = None
        base_claim_dir = self.pdf_dir / "agents" / "claims" / self.claim_id
        
        # Check for loop extractor outputs first
        for i in range(5, 0, -1):
            loop_path = base_claim_dir / f"evidence_extractor_loop{i}" / "output.json"
            if loop_path.exists():
                extractor_path = loop_path
                logger.info(f"  Using loop {i} extractor output")
                break
        
        # Fall back to standard extractor
        if extractor_path is None:
            extractor_path = base_claim_dir / "evidence_extractor" / "output.json"
        
        extractor_data = self.load_json(extractor_path)
        
        # Load document
        content_path = self.pdf_dir / "extracted" / "content.json"
        document_data = self.load_json(content_path)
        
        # Get full text
        full_text = document_utils.get_text(document_data, include_figures=True)
        
        claim = self.config.get("claim")
        if not claim:
            raise AgentError("No claim provided in config")
        
        # Process each extracted quote
        verified_evidence = []
        rejected_evidence = []
        
        extracted_quotes = extractor_data.get("extracted_evidence", [])
        logger.info(f"Verifying {len(extracted_quotes)} extracted quotes")
        
        for quote_data in extracted_quotes:
            quote = quote_data.get("quote", "")
            relevance_explanation = quote_data.get("relevance_explanation", "")
            
            # Verify both existence and applicability
            verification = await self._verify_evidence(
                claim=claim,
                quote=quote,
                full_document=full_text,
                relevance_explanation=relevance_explanation
            )
            
            if verification["keep"]:
                verified_evidence.append({
                    "id": quote_data.get("id"),
                    "quote": quote,  # Use original quote
                    "supports_claim": True,
                    "explanation": verification["explanation"],
                    "presence_explanation": verification.get("presence_explanation", ""),
                    "support_explanation": verification.get("support_explanation", ""),
                    "original_relevance": relevance_explanation
                })
            else:
                rejected_evidence.append({
                    "id": quote_data.get("id"),
                    "quote": quote,
                    "reason": verification["reason"],
                    "original_explanation": relevance_explanation
                })
        
        output = {
            "claim_id": self.claim_id,
            "claim": claim,
            "document": self.pdf_name,
            "verification_stats": {
                "total_extracted": len(extracted_quotes),
                "verified": len(verified_evidence),
                "rejected": len(rejected_evidence),
                "verification_rate": len(verified_evidence) / len(extracted_quotes) if extracted_quotes else 0
            },
            "verified_evidence": verified_evidence,
            "rejected_evidence": rejected_evidence,
            "model_used": self.llm_client.model
        }
        
        logger.info(
            f"Verified {len(verified_evidence)} of {len(extracted_quotes)} quotes "
            f"({output['verification_stats']['verification_rate']:.1%})"
        )
        
        return output
    
    
    async def _verify_evidence(
        self, 
        claim: str, 
        quote: str, 
        full_document: str,
        relevance_explanation: str
    ) -> Dict[str, Any]:
        """
        Verify if evidence genuinely supports the claim.
        
        Uses the standard: "Would this convince a skeptical reader?"
        """
        prompt = f"""You are verifying if a quote exists in the document AND genuinely supports a claim.

CLAIM: {claim}

QUOTE TO VERIFY: "{quote}"

ORIGINAL RELEVANCE EXPLANATION: {relevance_explanation}

Your task:
1. Find this quote (or a very similar version) in the document below
2. Determine if it genuinely supports the claim

IMPORTANT: Be flexible when matching quotes:
- Minor wording differences are acceptable (e.g., "30 percent" vs "30%")
- Different punctuation or capitalization is fine
- Small grammatical variations are okay
- Missing or added articles (a, an, the) are acceptable
- The quote might be split across lines or have different spacing
- If you find the core content even with variations, consider it found

For supporting the claim, accept quotes that:
- Directly state what the claim asserts, OR
- Provide specific facts/numbers that substantiate the claim

Reject quotes that:
- Only tangentially relate to the topic
- Require significant inference or assumptions
- Are about something else but happen to mention similar words
- Actually contradict the claim

Return your response as a JSON object:
{{
    "quote_found": true/false,
    "found_explanation": "explanation of whether/where the quote appears (be specific about any differences found)",
    "supports_claim": true/false,
    "support_explanation": "explanation of why it does/doesn't support the claim"
}}

FULL DOCUMENT:
{full_document}"""

        try:
            # Use the robust parser with retry
            result = await LLMResponseParser.parse_with_retry(
                llm_client=self.llm_client,
                prompt=prompt,
                output_model=VerifierOutput,
                max_retries=2,
                temperature=0.0,
                max_output_tokens=500
            )
            
            # Convert to expected format
            keep = result.quote_found and result.supports_claim
            
            if not result.quote_found:
                reason = "not found"
            elif not result.supports_claim:
                reason = "does not support claim"
            else:
                reason = ""
            
            return {
                "keep": keep,
                "presence_explanation": result.found_explanation,
                "support_explanation": result.support_explanation,
                "explanation": f"{result.found_explanation}. {result.support_explanation}".strip(),
                "reason": reason
            }
            
        except ValueError as e:
            logger.error(f"Failed to verify quote after retries: {e}")
            # Default to rejecting on error
            return {
                "keep": False,
                "reason": "Verification failed",
                "explanation": str(e),
                "presence_explanation": "",
                "support_explanation": ""
            }
    
