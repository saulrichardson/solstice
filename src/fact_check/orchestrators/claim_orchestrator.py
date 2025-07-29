"""Orchestrator for processing a single claim across multiple documents."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from ..agents import (
    SupportingEvidenceExtractor,
    RegexVerifier, 
    EvidenceCritic,
    CompletenessChecker,
    EvidenceJudge
)

logger = logging.getLogger(__name__)


class ClaimOrchestrator:
    """Process one claim across all documents using agent pipeline."""
    
    def __init__(
        self,
        claim_id: str,
        claim_text: str,
        documents: List[str],
        cache_dir: Path = Path("data/cache"),
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize claim orchestrator.
        
        Args:
            claim_id: Unique identifier for claim (e.g., "claim_001")
            claim_text: The actual claim text
            documents: List of document names to process
            cache_dir: Base cache directory
            config: Configuration for agents
        """
        self.claim_id = claim_id
        self.claim_text = claim_text
        self.documents = documents
        self.cache_dir = Path(cache_dir)
        self.config = config or {}
        
        # Agent configuration with claim
        self.agent_config = self.config.get("agent_config", {})
        self.agent_config["claim"] = claim_text
        
        # Allow customizing which agents to run
        self.agents_to_run = self.config.get("agents", [
            "supporting_evidence", 
            "regex_verifier", 
            "evidence_critic", 
            "completeness_checker",
            "regex_verifier_final",
            "evidence_judge"
        ])
    
    async def process(self) -> Dict[str, Any]:
        """
        Process claim across all documents.
        
        Returns:
            Dictionary with results for each document
        """
        logger.info(f"Processing {self.claim_id}: {self.claim_text[:50]}...")
        
        results = {
            "claim_id": self.claim_id,
            "claim": self.claim_text,
            "started_at": datetime.now().isoformat(),
            "documents": {}
        }
        
        # Process each document
        for document in self.documents:
            logger.info(f"  Processing document: {document}")
            
            try:
                # Run agent pipeline (no caching on read)
                doc_result = await self._process_document(document)
                results["documents"][document] = doc_result
                
            except Exception as e:
                logger.error(f"    Failed to process {document}: {e}")
                results["documents"][document] = {
                    "success": False,
                    "error": str(e)
                }
        
        results["completed_at"] = datetime.now().isoformat()
        return results
    
    async def _process_document(self, document: str) -> Dict[str, Any]:
        """Run agent pipeline for one document."""
        doc_result = {
            "document": document,
            "agents_run": [],
            "final_judgment": None
        }
        
        # Define agent sequence - filter based on config
        all_agents = [
            (SupportingEvidenceExtractor, "supporting_evidence"),
            (RegexVerifier, "regex_verifier"),
            (EvidenceCritic, "evidence_critic"),
            (CompletenessChecker, "completeness_checker"),
            (RegexVerifier, "regex_verifier_final"),
            (EvidenceJudge, "evidence_judge")
        ]
        
        # Only run requested agents
        agents = [(cls, name) for cls, name in all_agents if name in self.agents_to_run]
        
        # Run each agent in sequence
        for agent_class, agent_name in agents:
            logger.info(f"    Running {agent_name}...")
            
            try:
                # Special configuration for second regex verifier pass
                agent_config = self.agent_config.copy()
                if agent_name == "regex_verifier_final":
                    agent_config["upstream_agent"] = "completeness_checker"
                    agent_config["input_field"] = "all_snippets"
                
                # Create agent instance
                agent = agent_class(
                    pdf_name=document,
                    claim_id=self.claim_id,
                    cache_dir=self.cache_dir,
                    config=agent_config
                )
                
                # Run agent
                result = await agent.process()
                
                # Save agent output
                self._save_agent_output(document, agent_name, result)
                
                doc_result["agents_run"].append({
                    "agent": agent_name,
                    "success": True,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Capture final judgment
                if agent_name == "evidence_judge":
                    doc_result["final_judgment"] = result.get("judgment")
                
            except Exception as e:
                logger.error(f"      Agent {agent_name} failed: {e}")
                doc_result["agents_run"].append({
                    "agent": agent_name,
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                
                # Decide whether to continue
                if not self.config.get("continue_on_error", True):
                    break
        
        doc_result["success"] = all(a["success"] for a in doc_result["agents_run"])
        return doc_result
    
    def _save_agent_output(self, document: str, agent_name: str, output: Dict[str, Any]):
        """Save agent output to disk."""
        output_dir = self.cache_dir / document / "agents" / "claims" / self.claim_id / agent_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / "output.json"
        
        # Import json here to avoid circular imports
        import json
        with open(output_file, 'w') as f:
            json.dump(output, f, indent=2)
    
