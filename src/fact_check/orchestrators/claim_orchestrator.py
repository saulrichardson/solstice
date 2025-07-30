"""Streamlined orchestrator for processing claims with supporting evidence pipeline."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from ..agents import (
    EvidenceExtractor,
    EvidenceVerifierV2,
    CompletenessChecker,
    EvidencePresenter,
    ImageEvidenceAnalyzer
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
        # Note: Pipeline order matters for proper data flow
        self.pipeline = [
            (EvidenceExtractor, "evidence_extractor"),
            (EvidenceVerifierV2, "evidence_verifier_v2"),
            (CompletenessChecker, "completeness_checker"),
            # Additional verifier run will happen if completeness checker finds new evidence
            (EvidencePresenter, "evidence_presenter")
        ]
    
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
            "supporting_evidence": []
        }
        
        # Track all evidence
        all_verified_evidence = []
        
        logger.info(f"  Starting pipeline")
        
        # Run initial extraction and verification
        initial_evidence_verified = False
        additional_evidence_found = False
        
        for agent_class, agent_name in self.pipeline:
            # Skip presenter until we've processed all evidence
            if agent_name == "evidence_presenter" and additional_evidence_found:
                continue
                
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
                
                # Run agent
                result = await agent.process()
                
                # Save agent output
                self._save_agent_output(document, agent_name, result)
                
                doc_result["agents_run"].append({
                    "agent": agent_name,
                    "success": True,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Collect verified evidence
                if agent_name == "evidence_verifier_v2":
                    verified = result.get("verified_evidence", [])
                    all_verified_evidence.extend(verified)
                    logger.info(f"      Verified {len(verified)} evidence pieces")
                    initial_evidence_verified = True
                
                # Check if completeness checker found additional evidence
                if agent_name == "completeness_checker":
                    new_evidence = result.get("new_evidence", [])
                    if new_evidence:
                        logger.info(f"      Found {len(new_evidence)} additional evidence pieces")
                        additional_evidence_found = True
                        # Prepare additional evidence for verification
                        await self._prepare_additional_evidence(document, new_evidence)
                    
            except Exception as e:
                logger.error(f"      Agent {agent_name} failed: {e}")
                doc_result["agents_run"].append({
                    "agent": agent_name,
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                
                # Decide whether to continue
                if not self.config.get("continue_on_error", False):
                    break
        
        # If additional evidence was found, verify it
        if additional_evidence_found:
            await self._verify_additional_evidence(document, doc_result, all_verified_evidence)
        
        # NEW: Run image analysis after text pipeline completes
        logger.info(f"  Running image analysis...")
        image_evidence = await self._run_image_analysis(document, doc_result)
        doc_result["image_evidence"] = image_evidence
        
        # Now run the presenter with all verified evidence (text + images)
        await self._run_presenter(document, doc_result, all_verified_evidence)
        
        doc_result["success"] = all(a["success"] for a in doc_result["agents_run"])
        return doc_result
    
    async def _prepare_additional_evidence(self, document: str, new_evidence: List[Dict]):
        """Prepare additional evidence found by completeness checker for verification."""
        # Create output in format expected by verifier
        additional_extractor_output = {
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
        
        # Save for additional verifier to read
        output_dir = self.cache_dir / document / "agents" / "claims" / self.claim_id / "evidence_extractor_additional"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        import json
        with open(output_dir / "output.json", 'w') as f:
            json.dump(additional_extractor_output, f, indent=2)
    
    async def _verify_additional_evidence(
        self, 
        document: str, 
        doc_result: Dict[str, Any],
        all_verified_evidence: List[Dict]
    ):
        """Verify additional evidence found by completeness checker."""
        logger.info("    Running evidence_verifier_v2 for additional evidence...")
        
        try:
            # Create verifier for additional evidence
            agent_config = self.agent_config.copy()
            verifier = EvidenceVerifierV2(
                pdf_name=document,
                claim_id=self.claim_id,
                cache_dir=self.cache_dir,
                config=agent_config
            )
            
            # Point to additional evidence directory
            verifier.agent_dir = verifier.agent_dir.parent / "evidence_verifier_v2_additional"
            verifier.agent_dir.mkdir(parents=True, exist_ok=True)
            
            # Run verification
            result = await verifier.process()
            
            # Save output
            self._save_agent_output(document, "evidence_verifier_v2_additional", result)
            
            # Collect additional verified evidence
            additional_verified = result.get("verified_evidence", [])
            all_verified_evidence.extend(additional_verified)
            logger.info(f"      Verified {len(additional_verified)} additional evidence pieces")
            
            doc_result["agents_run"].append({
                "agent": "evidence_verifier_v2_additional",
                "success": True,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"      Additional evidence verification failed: {e}")
            doc_result["agents_run"].append({
                "agent": "evidence_verifier_v2_additional",
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
    
    async def _run_presenter(
        self,
        document: str,
        doc_result: Dict[str, Any],
        all_verified_evidence: List[Dict]
    ):
        """Run presenter with all verified evidence."""
        logger.info(f"    Running evidence_presenter with {len(all_verified_evidence)} text evidence pieces...")
        
        # Get image evidence from doc_result
        image_evidence = doc_result.get("image_evidence", [])
        logger.info(f"    And {len(image_evidence)} supporting images...")
        
        # Create consolidated verifier output for presenter
        consolidated_verifier = {
            "claim_id": self.claim_id,
            "claim": self.claim_text,
            "document": document,
            "verified_evidence": all_verified_evidence,
            "verification_stats": {
                "total_verified": len(all_verified_evidence)
            },
            # NEW: Add image evidence
            "image_evidence": image_evidence
        }
        
        # Save consolidated output
        verifier_dir = self.cache_dir / document / "agents" / "claims" / self.claim_id / "evidence_verifier_v2_consolidated"
        verifier_dir.mkdir(parents=True, exist_ok=True)
        
        import json
        with open(verifier_dir / "output.json", 'w') as f:
            json.dump(consolidated_verifier, f, indent=2)
        
        try:
            # Create presenter
            agent_config = self.agent_config.copy()
            presenter = EvidencePresenter(
                pdf_name=document,
                claim_id=self.claim_id,
                cache_dir=self.cache_dir,
                config=agent_config
            )
            
            # Run presenter
            result = await presenter.process()
            
            # Save output
            self._save_agent_output(document, "evidence_presenter", result)
            
            # Update doc_result with presenter output
            doc_result["supporting_evidence"] = result.get("supporting_evidence", [])
            doc_result["evidence_summary"] = result.get("evidence_summary", {})
            
            doc_result["agents_run"].append({
                "agent": "evidence_presenter",
                "success": True,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"      Evidence presenter failed: {e}")
            doc_result["agents_run"].append({
                "agent": "evidence_presenter",
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
    
    async def _run_image_analysis(self, document: str, doc_result: Dict[str, Any]) -> List[Dict]:
        """
        Analyze all images in the document for supporting evidence.
        
        Returns:
            List of image analysis results (only those that support the claim)
        """
        # Load document content to get image metadata
        from ..utils import document_utils
        
        content_path = self.cache_dir / document / "extracted" / "content.json"
        if not content_path.exists():
            logger.info("    No content.json found, skipping image analysis")
            return []
        
        try:
            with open(content_path, 'r') as f:
                content_json = json.load(f)
        except Exception as e:
            logger.error(f"    Failed to load content.json: {e}")
            return []
        
        # Get all images with metadata
        images = document_utils.get_images(content_json)
        
        if not images:
            logger.info("    No images found in document")
            return []
        
        logger.info(f"    Found {len(images)} images to analyze")
        
        # Analyze each image in parallel using asyncio.gather
        import asyncio
        
        tasks = []
        for image_metadata in images:
            analyzer = ImageEvidenceAnalyzer(
                pdf_name=document,
                claim_id=self.claim_id,
                image_metadata=image_metadata,
                cache_dir=self.cache_dir,
                config=self.agent_config
            )
            tasks.append(analyzer.process())
        
        # Run all image analyses in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        supporting_images = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                image_id = images[i].get('block_id', f"image_{i}")
                logger.error(f"      Image analysis failed for {image_id}: {result}")
                doc_result["agents_run"].append({
                    "agent": f"image_evidence_analyzer_{image_id}",
                    "success": False,
                    "error": str(result),
                    "timestamp": datetime.now().isoformat()
                })
            else:
                # Save the output to image-specific directory
                image_id = result.get('block_id', result.get('image_filename', '').replace('.png', '').replace('.jpg', ''))
                self._save_agent_output(document, f"image_evidence_analyzer/{image_id}", result)
                
                # Track in agents_run
                doc_result["agents_run"].append({
                    "agent": f"image_evidence_analyzer_{result.get('image_filename', '')}",
                    "success": True,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Only include images that support the claim
                if result.get("supports_claim"):
                    supporting_images.append(result)
                    logger.info(f"      ✓ {result.get('image_filename')} supports claim")
                else:
                    logger.info(f"      ✗ {result.get('image_filename')} does not support claim")
        
        logger.info(f"    Found {len(supporting_images)} supporting images out of {len(images)} analyzed")
        return supporting_images
    
    def _save_agent_output(self, document: str, agent_name: str, output: Dict[str, Any]):
        """Save agent output to disk."""
        output_dir = self.cache_dir / document / "agents" / "claims" / self.claim_id / agent_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / "output.json"
        
        # Import json here to avoid circular imports
        import json
        with open(output_file, 'w') as f:
            json.dump(output, f, indent=2)