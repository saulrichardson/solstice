"""Agent for presenting final evidence in a clean format."""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from .base import BaseAgent, AgentError

logger = logging.getLogger(__name__)


class EvidencePresenter(BaseAgent):
    """
    Present all verified supporting evidence in a clean, structured format.
    
    This is a simple formatting agent - no LLM calls needed.
    """
    
    @property
    def agent_name(self) -> str:
        return "evidence_presenter"
    
    @property
    def required_inputs(self) -> List[str]:
        return [
            f"agents/claims/{self.claim_id}/evidence_verifier_v2/output.json",
            f"agents/claims/{self.claim_id}/completeness_checker/output.json"
        ]
    
    def __init__(
        self, 
        pdf_name: str,
        claim_id: str,
        cache_dir: Path = Path("data/cache"),
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize evidence presenter agent."""
        super().__init__(pdf_name, cache_dir, config)
        self.claim_id = claim_id
        
        # Override agent directory to be claim-specific
        self.agent_dir = self.pdf_dir / "agents" / "claims" / claim_id / self.agent_name
        self.agent_dir.mkdir(parents=True, exist_ok=True)
    
    async def process(self) -> Dict[str, Any]:
        """
        Format and present all supporting evidence.
        
        Returns:
            Dictionary containing formatted evidence
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"EVIDENCE PRESENTER: Starting for claim {self.claim_id}")
        logger.info(f"Document: {self.pdf_name}")
        logger.info(f"{'='*60}")
        
        # Load verified evidence from main verifier
        verifier_path = self.pdf_dir / "agents" / "claims" / self.claim_id / "evidence_verifier_v2" / "output.json"
        logger.info(f"\nLoading main verified evidence from: {verifier_path}")
        verifier_data = self.load_json(verifier_path)
        
        # Check for additional verified evidence
        additional_verifier_path = self.pdf_dir / "agents" / "claims" / self.claim_id / "evidence_verifier_v2_additional" / "output.json"
        if additional_verifier_path.exists():
            logger.info(f"Found additional verified evidence at: {additional_verifier_path}")
            additional_data = self.load_json(additional_verifier_path)
            # Merge additional verified evidence
            verified_evidence = verifier_data.get("verified_evidence", [])
            additional_verified = additional_data.get("verified_evidence", [])
            logger.info(f"  Main evidence count: {len(verified_evidence)}")
            logger.info(f"  Additional evidence count: {len(additional_verified)}")
            
            # Deduplicate by quote text
            seen_quotes = {e["quote"] for e in verified_evidence}
            merged_count = 0
            for evidence in additional_verified:
                if evidence["quote"] not in seen_quotes:
                    verified_evidence.append(evidence)
                    seen_quotes.add(evidence["quote"])
                    merged_count += 1
            
            logger.info(f"  Merged {merged_count} new unique evidence pieces")
            logger.info(f"  Total after merge: {len(verified_evidence)}")
            
            # Update the data with merged evidence
            verifier_data["verified_evidence"] = verified_evidence
            verifier_data["verification_stats"]["total_verified"] = len(verified_evidence)
        
        # Load completeness assessment
        completeness_path = self.pdf_dir / "agents" / "claims" / self.claim_id / "completeness_checker" / "output.json"
        completeness_data = {}
        if completeness_path.exists():
            logger.info(f"\nLoading completeness assessment from: {completeness_path}")
            completeness_data = self.load_json(completeness_path)
        else:
            logger.info(f"\nNo completeness assessment found at: {completeness_path}")
        
        claim = self.config.get("claim", verifier_data.get("claim", ""))
        logger.info(f"\nClaim: '{claim}'")
        
        # Get all verified evidence
        verified_evidence = verifier_data.get("verified_evidence", [])
        logger.info(f"\nTotal verified evidence pieces: {len(verified_evidence)}")
        
        # Get image evidence if available
        image_evidence = verifier_data.get("image_evidence", [])
        logger.info(f"Total image evidence pieces: {len(image_evidence)}")
        
        # Get completeness info
        completeness_assessment = completeness_data.get("completeness_assessment", {})
        missing_aspects = completeness_assessment.get("missing_aspects", [])
        
        # Calculate coverage
        if not missing_aspects:
            coverage = "complete"
        elif len(verified_evidence) == 0:
            coverage = "none"
        else:
            coverage = "partial"
        
        logger.info(f"\nCoverage assessment: {coverage}")
        if missing_aspects:
            logger.info(f"Missing aspects: {missing_aspects}")
        
        # Format the output
        output = {
            "claim_id": self.claim_id,
            "claim": claim,
            "document": self.pdf_name,
            "supporting_evidence": [
                {
                    "quote": evidence["quote"],
                    "explanation": evidence["explanation"]
                }
                for evidence in verified_evidence
            ],
            "image_supporting_evidence": [
                {
                    "image_filename": img["image_filename"],
                    "explanation": img["explanation"]
                }
                for img in image_evidence
            ],
            "evidence_summary": {
                "total_text_evidence_found": len(verified_evidence),
                "total_image_evidence_found": len(image_evidence),
                "total_evidence_found": len(verified_evidence) + len(image_evidence),
                "coverage": coverage,
                "missing_aspects": missing_aspects
            },
            "metadata": {
                "extraction_stats": verifier_data.get("verification_stats", {}),
                "rejected_count": len(verifier_data.get("rejected_evidence", []))
            }
        }
        
        logger.info(f"\nFormatted Evidence Summary:")
        logger.info(f"  - Text evidence pieces: {len(verified_evidence)}")
        logger.info(f"  - Image evidence pieces: {len(image_evidence)}")
        logger.info(f"  - Total evidence: {len(verified_evidence) + len(image_evidence)}")
        logger.info(f"  - Coverage: {coverage}")
        logger.info(f"  - Rejected count: {output['metadata']['rejected_count']}")
        
        if verified_evidence:
            logger.info("\nText evidence pieces:")
            for i, evidence in enumerate(output['supporting_evidence'], 1):
                logger.info(f"  {i}. '{evidence['quote'][:80]}...'")
                logger.info(f"     Explanation: {evidence['explanation'][:100]}...")
        
        if image_evidence:
            logger.info("\nImage evidence pieces:")
            for i, img in enumerate(output['image_supporting_evidence'], 1):
                logger.info(f"  {i}. Image: {img['image_filename']}")
                logger.info(f"     Explanation: {img['explanation'][:100]}...")
        
        logger.info(f"\n{'='*60}")
        logger.info(f"EVIDENCE PRESENTER: Completed for claim {self.claim_id}")
        logger.info(f"{'='*60}\n")
        
        return output