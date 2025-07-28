"""Agent for critiquing the quality of evidence."""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..core.responses_client import ResponsesClient
from .base import BaseAgent, AgentError

logger = logging.getLogger(__name__)


class EvidenceCritic(BaseAgent):
    """Critique the quality and relevance of extracted evidence"""
    
    @property
    def agent_name(self) -> str:
        return "evidence_critic"
    
    @property
    def required_inputs(self) -> List[str]:
        return [
            f"agents/claims/{self.claim_id}/regex_verifier/output.json"
        ]
    
    def __init__(
        self, 
        pdf_name: str,
        claim_id: str,
        cache_dir: Path = Path("data/cache"),
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize evidence critic agent."""
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
        Critique the quality of evidence.
        
        Returns:
            Dictionary containing critique of each snippet
        """
        logger.info(f"Critiquing evidence for {self.claim_id}")
        
        # Get verified snippets from previous agent
        verifier_path = self.pdf_dir / "agents" / "claims" / self.claim_id / "regex_verifier" / "output.json"
        verifier_data = self.load_json(verifier_path)
        
        # TODO: Implement actual critique using LLM
        # For now, assign mock quality scores
        
        critiqued_snippets = []
        for snippet in verifier_data.get("verified_snippets", []):
            critiqued = snippet.copy()
            critiqued["critique"] = {
                "relevance_score": 0.8,  # How relevant to the claim
                "specificity_score": 0.7,  # How specific vs general
                "directness_score": 0.9,  # How directly it supports
                "credibility_score": 0.85,  # Source credibility
                "overall_quality": 0.8,
                "critique_notes": "Placeholder critique - implement LLM analysis"
            }
            critiqued_snippets.append(critiqued)
        
        output = {
            "claim_id": self.claim_id,
            "claim": verifier_data.get("claim"),
            "critique_summary": {
                "total_snippets": len(critiqued_snippets),
                "high_quality": sum(1 for s in critiqued_snippets if s["critique"]["overall_quality"] >= 0.8),
                "medium_quality": sum(1 for s in critiqued_snippets if 0.5 <= s["critique"]["overall_quality"] < 0.8),
                "low_quality": sum(1 for s in critiqued_snippets if s["critique"]["overall_quality"] < 0.5)
            },
            "critiqued_snippets": critiqued_snippets
        }
        
        # TODO: Actual implementation would:
        # 1. Send each snippet + claim to LLM for critique
        # 2. Ask for specific quality dimensions
        # 3. Get reasoning for scores
        # 4. Possibly filter out low-quality evidence
        
        logger.info(f"Critiqued {len(critiqued_snippets)} snippets")
        
        return output