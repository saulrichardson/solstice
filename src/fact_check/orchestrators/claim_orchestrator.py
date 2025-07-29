"""Streamlined orchestrator for processing claims with supporting evidence pipeline."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from ..agents import (
    EvidenceExtractor,
    EvidenceVerifierV2,
    CompletenessChecker,
    EvidencePresenter
)

logger = logging.getLogger(__name__)


class ClaimOrchestrator:
    """Process one claim across all documents using streamlined evidence pipeline."""
    
    def __init__(
        self,
        claim_id: str,
        claim_text: str,
        documents: List[str],
        cache_dir: Path = Path("data/cache"),
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize streamlined claim orchestrator.
        
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
        
        # Fixed pipeline for streamlined architecture
        self.pipeline = [
            (EvidenceExtractor, "evidence_extractor"),
            (EvidenceVerifierV2, "evidence_verifier_v2"),
            (CompletenessChecker, "completeness_checker"),
            (EvidencePresenter, "evidence_presenter")
        ]
        
        # Whether to re-verify additional evidence found by completeness checker
        self.reverify_additional = self.config.get("reverify_additional", True)
    
    async def process(self) -> Dict[str, Any]:
        """
        Process claim across all documents.
        
        Returns:
            Dictionary with supporting evidence for each document
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
                # Run streamlined pipeline
                doc_result = await self._process_document(document)
                results["documents"][document] = doc_result
                
            except Exception as e:
                logger.error(f"    Failed to process {document}: {e}")
                results["documents"][document] = {
                    "success": False,
                    "error": str(e),
                    "supporting_evidence": []
                }
        
        results["completed_at"] = datetime.now().isoformat()
        return results
    
    async def _process_document(self, document: str) -> Dict[str, Any]:
        """Run streamlined pipeline for one document."""
        doc_result = {
            "document": document,
            "agents_run": [],
            "supporting_evidence": [],
            "loops_performed": 0
        }
        
        # Track all evidence across loops
        all_verified_evidence = []
        
        # Maximum number of loops to prevent infinite recursion
        max_loops = self.config.get("max_completeness_loops", 2)
        current_loop = 0
        
        while current_loop < max_loops:
            current_loop += 1
            loop_found_new = False
            
            logger.info(f"  Starting pipeline loop {current_loop}")
            
            # Run the main pipeline
            for agent_class, agent_name in self.pipeline:
                logger.info(f"    Running {agent_name}...")
                
                try:
                    # Use standard agent config
                    agent_config = self.agent_config.copy()
                    
                    # Create agent instance
                    agent = agent_class(
                        pdf_name=document,
                        claim_id=self.claim_id,
                        cache_dir=self.cache_dir,
                        config=agent_config
                    )
                    
                    # Add loop suffix to agent directory for subsequent loops
                    if current_loop > 1:
                        agent.agent_dir = agent.agent_dir.parent / f"{agent_name}_loop{current_loop}"
                        agent.agent_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Run agent
                    result = await agent.process()
                    
                    # Save agent output
                    output_name = agent_name if current_loop == 1 else f"{agent_name}_loop{current_loop}"
                    self._save_agent_output(document, output_name, result)
                    
                    doc_result["agents_run"].append({
                        "agent": output_name,
                        "success": True,
                        "timestamp": datetime.now().isoformat(),
                        "loop": current_loop
                    })
                    
                    # Collect verified evidence
                    if agent_name == "evidence_verifier_v2":
                        verified = result.get("verified_evidence", [])
                        all_verified_evidence.extend(verified)
                        logger.info(f"      Verified {len(verified)} evidence pieces")
                    
                    # Check if completeness checker found new evidence
                    if agent_name == "completeness_checker":
                        new_evidence = result.get("new_evidence", [])
                        if new_evidence and self.reverify_additional:
                            logger.info(f"      Found {len(new_evidence)} additional evidence pieces")
                            # Prepare for next loop
                            loop_found_new = True
                            # Update extractor output for next loop
                            await self._prepare_next_loop(document, new_evidence, current_loop)
                    
                    # Skip presenter on intermediate loops
                    if agent_name == "evidence_presenter" and loop_found_new and current_loop < max_loops:
                        logger.info("      Skipping presenter - will run after verification loop")
                        break
                        
                except Exception as e:
                    output_name = agent_name if current_loop == 1 else f"{agent_name}_loop{current_loop}"
                    logger.error(f"      Agent {agent_name} failed: {e}")
                    doc_result["agents_run"].append({
                        "agent": output_name,
                        "success": False,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat(),
                        "loop": current_loop
                    })
                    
                    # Decide whether to continue
                    if not self.config.get("continue_on_error", True):
                        break
            
            # If no new evidence found, break the loop
            if not loop_found_new:
                break
                
            doc_result["loops_performed"] = current_loop
        
        # Final presentation with all evidence
        if all_verified_evidence:
            await self._run_final_presenter(document, all_verified_evidence, doc_result)
        
        doc_result["success"] = all(a["success"] for a in doc_result["agents_run"])
        return doc_result
    
    async def _prepare_next_loop(
        self,
        document: str,
        new_evidence: List[Dict],
        current_loop: int
    ):
        """Prepare evidence extractor output for next loop."""
        # Create output in format expected by verifier
        next_extractor_output = {
            "claim_id": self.claim_id,
            "claim": self.claim_text,
            "document": {
                "pdf_name": document
            },
            "extraction_result": {
                "success": True,
                "total_snippets_found": len(new_evidence)
            },
            "extracted_evidence": new_evidence
        }
        
        # Save for next loop's verifier to read
        next_loop = current_loop + 1
        output_dir = self.cache_dir / document / "agents" / "claims" / self.claim_id / f"evidence_extractor_loop{next_loop}"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        import json
        with open(output_dir / "output.json", 'w') as f:
            json.dump(next_extractor_output, f, indent=2)
            
        logger.info(f"      Prepared evidence for loop {next_loop}")
    
    async def _run_final_presenter(
        self,
        document: str,
        all_verified_evidence: List[Dict],
        doc_result: Dict[str, Any]
    ):
        """Run final presenter with all collected evidence."""
        logger.info(f"    Running final evidence presenter with {len(all_verified_evidence)} total pieces")
        
        # Create consolidated verifier output
        consolidated_verifier = {
            "claim_id": self.claim_id,
            "claim": self.claim_text,
            "document": document,
            "verified_evidence": all_verified_evidence,
            "verification_stats": {
                "total_verified": len(all_verified_evidence)
            }
        }
        
        # Save consolidated output
        verifier_dir = self.cache_dir / document / "agents" / "claims" / self.claim_id / "evidence_verifier_v2_consolidated"
        verifier_dir.mkdir(parents=True, exist_ok=True)
        
        import json
        with open(verifier_dir / "output.json", 'w') as f:
            json.dump(consolidated_verifier, f, indent=2)
        
        # Run presenter
        try:
            presenter_config = self.agent_config.copy()
            presenter = EvidencePresenter(
                pdf_name=document,
                claim_id=self.claim_id,
                cache_dir=self.cache_dir,
                config=presenter_config
            )
            
            # Point presenter to consolidated evidence directory
            presenter.agent_dir = presenter.agent_dir.parent / "evidence_presenter_final"
            presenter.agent_dir.mkdir(parents=True, exist_ok=True)
            
            result = await presenter.process()
            
            self._save_agent_output(document, "evidence_presenter_final", result)
            
            doc_result["supporting_evidence"] = result.get("supporting_evidence", [])
            doc_result["evidence_summary"] = result.get("evidence_summary", {})
            
            doc_result["agents_run"].append({
                "agent": "evidence_presenter_final",
                "success": True,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"      Final presenter failed: {e}")
            doc_result["agents_run"].append({
                "agent": "evidence_presenter_final",
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
    
    def _save_agent_output(self, document: str, agent_name: str, output: Dict[str, Any]):
        """Save agent output to disk."""
        output_dir = self.cache_dir / document / "agents" / "claims" / self.claim_id / agent_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / "output.json"
        
        # Import json here to avoid circular imports
        import json
        with open(output_file, 'w') as f:
            json.dump(output, f, indent=2)