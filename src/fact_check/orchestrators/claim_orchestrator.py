"""Streamlined orchestrator for processing claims with supporting evidence pipeline."""

import copy
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
        # Use deep copy to avoid shared state between concurrent orchestrators
        # This ensures nested dictionaries/lists are also copied, not just referenced
        self.agent_config = copy.deepcopy(self.config.get("agent_config", {}))
        self.agent_config["claim"] = claim_text
        
        # Fixed pipeline for streamlined architecture.  The presenter is
        # executed exactly once *after* all evidence has been collected and
        # verified (see `_run_presenter`).  Keeping it out of the main loop
        # prevents duplicate execution and simplifies control-flow.
        # New simplified linear pipeline
        self.pipeline = [
            (EvidenceExtractor, "evidence_extractor"),
            (CompletenessChecker, "completeness_checker"),
            (EvidenceVerifierV2, "evidence_verifier_v2"),
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
        
        # Track all verified evidence
        all_verified_evidence = []
        logger.info(f"  Starting pipeline")
        
        # Track if pipeline was stopped early
        pipeline_stopped_early = False
        
        for agent_class, agent_name in self.pipeline:
            logger.info(f"    Running {agent_name}...")
            
            try:
                # Use deep copy for agent config to ensure isolation
                agent_config = copy.deepcopy(self.agent_config)

                # Create agent instance
                agent = agent_class(
                    pdf_name=document,
                    claim_id=self.claim_id,
                    cache_dir=self.cache_dir,
                    config=agent_config,
                )

                # Execute via BaseAgent.run() which handles validation,
                # metadata, and output persistence.
                result = await agent.run()
                
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
                
                # After completeness checker, no immediate side-effects; merged
                # evidence will be verified in the next pipeline step.
                    
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
                    pipeline_stopped_early = True
                    logger.info(f"    Stopping pipeline early due to error (continue_on_error=False)")
                    break
        
        # Only run subsequent steps if pipeline completed or continue_on_error is True
        if not pipeline_stopped_early:
            # Run image analysis after text pipeline completes
            logger.info(f"  Running image analysis...")
            image_evidence = await self._run_image_analysis(document, doc_result)
            doc_result["image_evidence"] = image_evidence
            
            # Now run the presenter with all verified evidence (text + images)
            await self._run_presenter(document, doc_result, all_verified_evidence)
        else:
            # Pipeline stopped early - set empty results
            logger.info(f"  Skipping image analysis and presenter due to pipeline error")
            doc_result["image_evidence"] = []
            doc_result["supporting_evidence"] = []
            doc_result["evidence_summary"] = {
                "total_text_evidence_found": 0,
                "total_image_evidence_found": 0,
                "total_evidence_found": 0,
                "coverage": "none",
                "missing_aspects": ["Pipeline stopped early due to error"]
            }
        
        # ------------------------------------------------------------------
        # Determine overall success
        # ------------------------------------------------------------------
        # Simplified rule: a document is successful when *all* executed
        # agents completed without error.  This avoids the previous split
        # between “core” and “optional” and produces a single, consistent
        # interpretation for downstream analytics.

        doc_result["success"] = all(a["success"] for a in doc_result["agents_run"])
        return doc_result
    
    
    
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
            # Create presenter with deep copied config
            agent_config = copy.deepcopy(self.agent_config)
            presenter = EvidencePresenter(
                pdf_name=document,
                claim_id=self.claim_id,
                cache_dir=self.cache_dir,
                config=agent_config
            )
            
            # Run presenter via BaseAgent.run()
            result = await presenter.run()
            
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
        
        # Validate that all images have required fields
        valid_images = []
        for img in images:
            if not img.get('image_path'):
                logger.warning(f"    Skipping image {img.get('block_id', 'unknown')} - missing image_path")
                continue
            valid_images.append(img)
        
        if not valid_images:
            logger.info("    No valid images found in document")
            return []
        
        logger.info(f"    Found {len(valid_images)} valid images to analyze (skipped {len(images) - len(valid_images)} invalid)")
        
        # Analyze each image with controlled parallelism
        import asyncio
        
        # Limit concurrent image analyses to prevent memory issues
        max_concurrent = self.config.get("max_concurrent_images", 5)
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def analyze_image_with_limit(image_metadata):
            async with semaphore:
                # Deep copy config for each image analyzer to ensure isolation
                analyzer = ImageEvidenceAnalyzer(
                    pdf_name=document,
                    claim_id=self.claim_id,
                    image_metadata=image_metadata,
                    cache_dir=self.cache_dir,
                    config=copy.deepcopy(self.agent_config)
                )
                return await analyzer.run()
        
        # Create tasks with semaphore limiting (use valid_images)
        tasks = [analyze_image_with_limit(img) for img in valid_images]
        
        # Run all image analyses with controlled parallelism
        logger.info(f"    Analyzing images with max {max_concurrent} concurrent processes...")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        supporting_images = []
        for i, result in enumerate(results):
            # Get consistent image identifier
            image_metadata = valid_images[i]
            image_filename = image_metadata.get('image_filename', '')
            image_id = image_metadata.get('block_id', image_filename.replace('.png', '').replace('.jpg', '') or f"image_{i}")
            
            if isinstance(result, Exception) or result.get("error"):
                logger.error(f"      Image analysis failed for {image_filename}: {result}")
                doc_result["agents_run"].append({
                    "agent": f"image_evidence_analyzer_{image_id}",
                    "success": False,
                    "error": str(result),
                    "timestamp": datetime.now().isoformat(),
                })
            else:
                # Track in agents_run with consistent naming
                doc_result["agents_run"].append({
                    "agent": f"image_evidence_analyzer_{image_id}",
                    "success": True,
                    "timestamp": datetime.now().isoformat(),
                })

                # Only include images that support the claim
                if result.get("supports_claim"):
                    supporting_images.append(result)
                    logger.info(f"      ✓ {image_filename} supports claim")
                else:
                    logger.info(f"      ✗ {image_filename} does not support claim")
        
        logger.info(f"    Found {len(supporting_images)} supporting images out of {len(valid_images)} analyzed")
        return supporting_images
