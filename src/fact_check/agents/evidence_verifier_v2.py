"""Agent for verifying evidence existence AND applicability to claims."""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..core.responses_client import ResponsesClient
from ..utils import document_utils
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

First, check if this quote (or a very similar version) exists in the document below.
Then, determine if it genuinely supports the claim.

Accept quotes that:
1. Exist in the document (exact or with minor formatting differences), AND
2. Directly state what the claim asserts, OR provide specific facts/numbers that substantiate the claim

Reject quotes that:
- Cannot be found in the document
- Only tangentially relate to the topic
- Require significant inference or assumptions  
- Are about something else but happen to mention similar words
- Actually contradict the claim

Be strict - we want evidence that would convince a skeptical reader.

Provide your verdict in this format:
VERDICT: KEEP or REJECT
EXPLANATION: [Why this does/doesn't support the claim - 1-2 sentences]
REASON_IF_REJECTED: [Only if REJECT - specific issue like "not found", "too tangential", "requires inference", etc.]

FULL DOCUMENT:
{full_document}"""

        try:
            response = await self.llm_client.create_response(
                input=prompt,
                model=self.llm_client.model,
                temperature=0.0,
                max_output_tokens=500,
                disable_cache=self.config.get("disable_cache", True)
            )
            
            content = ResponsesClient.extract_text(response)
            return self._parse_verification_response(content)
            
        except Exception as e:
            logger.error(f"Error verifying quote: {e}")
            # Default to rejecting on error
            return {
                "keep": False,
                "reason": f"Verification error: {str(e)}",
                "explanation": ""
            }
    
    def _parse_verification_response(self, response: str) -> Dict[str, Any]:
        """Parse the verification response."""
        result = {
            "keep": False,
            "explanation": "",
            "reason": ""
        }
        
        try:
            lines = response.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                if line.startswith("VERDICT:"):
                    verdict = line.split(":", 1)[1].strip().upper()
                    result["keep"] = verdict == "KEEP"
                elif line.startswith("EXPLANATION:"):
                    result["explanation"] = line.split(":", 1)[1].strip()
                elif line.startswith("REASON_IF_REJECTED:"):
                    result["reason"] = line.split(":", 1)[1].strip()
            
            # Use explanation as reason if rejected but no specific reason
            if not result["keep"] and not result["reason"] and result["explanation"]:
                result["reason"] = result["explanation"]
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing verification response: {e}")
            return {
                "keep": False,
                "reason": "Failed to parse verification response",
                "explanation": ""
            }