"""Agent for making final judgment on claims based on evidence."""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..core.responses_client import ResponsesClient
from .base import BaseAgent, AgentError

logger = logging.getLogger(__name__)


class EvidenceJudge(BaseAgent):
    """Make final judgment on claims based on critiqued evidence"""
    
    @property
    def agent_name(self) -> str:
        return "evidence_judge"
    
    @property
    def required_inputs(self) -> List[str]:
        return [
            f"agents/claims/{self.claim_id}/evidence_critic/output.json"
        ]
    
    def __init__(
        self, 
        pdf_name: str,
        claim_id: str,
        cache_dir: Path = Path("data/cache"),
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize evidence judge agent."""
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
        Make final judgment on the claim.
        
        Returns:
            Dictionary containing final judgment
        """
        logger.info(f"Making final judgment for {self.claim_id}")
        
        # Get critiqued evidence from previous agent
        critic_path = self.pdf_dir / "agents" / "claims" / self.claim_id / "evidence_critic" / "output.json"
        critic_data = self.load_json(critic_path)
        
        # Extract evidence statistics from critic data
        critic_stats = critic_data.get("critic_stats", {})
        validated_snippets = critic_data.get("validated_snippets", [])
        
        # Count high quality evidence (score >= 8.0)
        high_quality_count = sum(1 for s in validated_snippets 
                                if s.get("critic_evaluation", {}).get("overall_score", 0) >= 8.0)
        total_snippets = len(validated_snippets)
        
        # Simple rule-based judgment for stub
        if high_quality_count >= 3:
            judgment = "strongly_supported"
            confidence = 0.9
        elif high_quality_count >= 1:
            judgment = "supported"
            confidence = 0.7
        elif total_snippets >= 1:
            judgment = "weakly_supported"
            confidence = 0.5
        else:
            judgment = "unsupported"
            confidence = 0.8
        
        output = {
            "claim_id": self.claim_id,
            "claim": critic_data.get("claim"),
            "judgment": {
                "verdict": judgment,
                "confidence": confidence,
                "reasoning": f"Based on {high_quality_count} high-quality snippets out of {total_snippets} total",
                "evidence_summary": {
                    "total_evidence": total_snippets,
                    "high_quality_evidence": high_quality_count,
                    "key_supporting_quotes": [
                        s["quote"][:100] + "..." 
                        for s in validated_snippets[:3]
                    ] if validated_snippets else []
                }
            },
            "document": {
                "pdf_name": self.pdf_name,
                "claim_id": self.claim_id
            }
        }
        
        # TODO: Actual implementation would:
        # 1. Send all evidence + critiques to LLM
        # 2. Ask for holistic judgment
        # 3. Get detailed reasoning
        # 4. Consider conflicting evidence
        # 5. Provide nuanced verdict beyond simple yes/no
        
        logger.info(f"Final judgment: {judgment} (confidence: {confidence})")
        
        return output