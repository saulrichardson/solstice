"""Agent for verifying evidence existence AND applicability to claims."""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..core.responses_client import ResponsesClient
from ..utils import document_utils
from ..models.llm_outputs import VerifierOutput
from ..utils.llm_parser import LLMResponseParser
from .base import BaseAgent, AgentError
from ..config.agent_models import get_model_for_agent

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
        # Use centrally configured model for this agent
        self.llm_client.model = get_model_for_agent(self.agent_name)
    
    async def process(self) -> Dict[str, Any]:
        """
        Verify evidence existence and applicability.
        
        Returns:
            Dictionary containing verified and rejected evidence
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"EVIDENCE VERIFIER V2: Starting for claim {self.claim_id}")
        logger.info(f"Document: {self.pdf_name}")
        logger.info(f"{'='*60}")
        
        # Find the appropriate extractor output
        extractor_path = None
        base_claim_dir = self.pdf_dir / "agents" / "claims" / self.claim_id
        
        # Check configuration for verification type
        if self.config.get("is_additional_verification", False):
            extractor_path = base_claim_dir / "evidence_extractor_additional" / "output.json"
            logger.info("\nRunning as ADDITIONAL verifier")
            logger.info(f"Using additional evidence from: {extractor_path}")
        else:
            # Standard verification - use main extractor output
            extractor_path = base_claim_dir / "evidence_extractor" / "output.json"
            logger.info("\nRunning as MAIN verifier")
            logger.info(f"Using extracted evidence from: {extractor_path}")
        
        extractor_data = self.load_json(extractor_path)
        
        # Load document
        content_path = self.pdf_dir / "extracted" / "content.json"
        document_data = self.load_json(content_path)
        
        # Get full text
        full_text = document_utils.get_text(document_data, include_figures=True)
        
        claim = self.config.get("claim")
        if not claim:
            raise AgentError("No claim provided in config")
        
        logger.info(f"\nClaim being verified: '{claim}'")
        
        # Process each extracted quote
        verified_evidence = []
        rejected_evidence = []
        
        extracted_quotes = extractor_data.get("extracted_evidence", [])
        logger.info(f"\nFound {len(extracted_quotes)} quotes to verify")
        logger.info(f"Using model: {self.llm_client.model}")
        
        for i, quote_data in enumerate(extracted_quotes, 1):
            quote = quote_data.get("quote", "")
            relevance_explanation = quote_data.get("relevance_explanation", "")
            
            logger.info(f"\nVerifying quote {i}/{len(extracted_quotes)}:")
            logger.info(f"  Quote: '{quote[:100]}...'")
            logger.info(f"  Original relevance: {relevance_explanation[:100]}...")
            
            # Verify both existence and applicability
            verification = await self._verify_evidence(
                claim=claim,
                quote=quote,
                full_document=full_text,
                relevance_explanation=relevance_explanation
            )
            
            if verification["keep"]:
                logger.info(f"  ✓ VERIFIED: Quote supports claim")
                logger.info(f"    Explanation: {verification['explanation'][:100]}...")
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
                logger.info(f"  ✗ REJECTED: {verification['reason']}")
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
        
        logger.info(f"\nVerification Results:")
        logger.info(f"  - Total quotes processed: {len(extracted_quotes)}")
        logger.info(f"  - Verified (supports claim): {len(verified_evidence)}")
        logger.info(f"  - Rejected: {len(rejected_evidence)}")
        logger.info(f"  - Verification rate: {output['verification_stats']['verification_rate']:.1%}")
        
        if rejected_evidence:
            logger.info("\nRejection reasons:")
            reason_counts = {}
            for rej in rejected_evidence:
                reason = rej['reason']
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
            for reason, count in reason_counts.items():
                logger.info(f"  - {reason}: {count}")
        
        logger.info(f"\n{'='*60}")
        logger.info(f"EVIDENCE VERIFIER V2: Completed for claim {self.claim_id}")
        logger.info(f"{'='*60}\n")
        
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
1. Find this quote in the document below
2. Determine if it genuinely supports the claim

CRITICAL: Base your verification solely on what is explicitly stated in the document. Do not infer or assume information not present in the text.

IMPORTANT context about quote matching:
- The quote may have been cleaned of OCR artifacts by the extractor
- Look for the same factual content, not character-perfect matches
- The extractor corrects mechanical errors like:
  * Split words ("immunogen i city" → "immunogenicity") 
  * Broken spacing ("fromFlublok" → "from Flublok")
  * OCR character errors ("0" vs "O", "l" vs "I")
- Focus on semantic equivalence - does it convey the same information?
- The quote should contain all the same facts, numbers, and technical content
- Consider it found if the meaning and data are preserved

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
    "support_explanation": "explanation of why it does/doesn't support the claim (if quote not found, state this clearly)"
}}

IMPORTANT: If quote_found is false, your support_explanation MUST mention that the quote was not found in the document.

FULL DOCUMENT:
{full_document}"""

        logger.debug(f"\nCalling LLM to verify quote...")
        
        try:
            # Use the robust parser with retry
            result = await LLMResponseParser.parse_with_retry(
                llm_client=self.llm_client,
                prompt=prompt,
                output_model=VerifierOutput,
                max_retries=2,
                temperature=0.0
                # Removed max_output_tokens - let model use what it needs
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
            logger.error(f"Exception type: {type(e).__name__}")
            # Default to rejecting on error
            return {
                "keep": False,
                "reason": "Verification failed",
                "explanation": str(e),
                "presence_explanation": "",
                "support_explanation": ""
            }
    
