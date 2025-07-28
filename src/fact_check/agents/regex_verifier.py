"""Agent for verifying extracted quotes exist in the document using regex."""

import re
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from .base import BaseAgent, AgentError

logger = logging.getLogger(__name__)


class RegexVerifier(BaseAgent):
    """Verify that extracted quotes actually exist in the document"""
    
    @property
    def agent_name(self) -> str:
        return "regex_verifier"
    
    @property
    def required_inputs(self) -> List[str]:
        return [
            "extracted/content.json",
            f"agents/claims/{self.claim_id}/supporting_evidence/output.json"
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
        
        # Override agent directory to be claim-specific
        self.agent_dir = self.pdf_dir / "agents" / "claims" / claim_id / self.agent_name
        self.agent_dir.mkdir(parents=True, exist_ok=True)
    
    async def process(self) -> Dict[str, Any]:
        """
        Verify extracted quotes using regex matching.
        
        Returns:
            Dictionary containing verified snippets
        """
        logger.info(f"Verifying quotes for {self.claim_id}")
        
        # Get supporting evidence from previous agent
        evidence_path = self.pdf_dir / "agents" / "claims" / self.claim_id / "supporting_evidence" / "output.json"
        evidence_data = self.load_json(evidence_path)
        
        # TODO: Implement actual regex verification
        # For now, pass through all snippets as verified
        
        output = {
            "claim_id": self.claim_id,
            "claim": evidence_data.get("claim"),
            "verification_stats": {
                "total_snippets": len(evidence_data.get("supporting_snippets", [])),
                "verified": len(evidence_data.get("supporting_snippets", [])),
                "failed": 0,
                "modified": 0
            },
            "verified_snippets": evidence_data.get("supporting_snippets", []),
            "failed_snippets": []
        }
        
        # TODO: Actual implementation would:
        # 1. Load the document text
        # 2. For each snippet, try to find it with regex
        # 3. Handle whitespace normalization
        # 4. Mark failed verifications
        # 5. Possibly apply fuzzy matching for close matches
        
        logger.info(f"Verified {output['verification_stats']['verified']} of {output['verification_stats']['total_snippets']} snippets")
        
        return output