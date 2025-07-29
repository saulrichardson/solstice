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
        logger.info(f"Presenting evidence for {self.claim_id}")
        
        # Load verified evidence
        verifier_path = self.pdf_dir / "agents" / "claims" / self.claim_id / "evidence_verifier_v2" / "output.json"
        verifier_data = self.load_json(verifier_path)
        
        # Load completeness assessment
        completeness_path = self.pdf_dir / "agents" / "claims" / self.claim_id / "completeness_checker" / "output.json"
        completeness_data = {}
        if completeness_path.exists():
            completeness_data = self.load_json(completeness_path)
        
        claim = self.config.get("claim", verifier_data.get("claim", ""))
        
        # Get all verified evidence
        verified_evidence = verifier_data.get("verified_evidence", [])
        
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
            "evidence_summary": {
                "total_evidence_found": len(verified_evidence),
                "coverage": coverage,
                "missing_aspects": missing_aspects
            },
            "metadata": {
                "extraction_stats": verifier_data.get("verification_stats", {}),
                "rejected_count": len(verifier_data.get("rejected_evidence", []))
            }
        }
        
        logger.info(
            f"Presented {len(verified_evidence)} pieces of supporting evidence "
            f"(coverage: {coverage})"
        )
        
        return output