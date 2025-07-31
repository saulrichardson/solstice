"""Streamlined study orchestrator for running fact-checking across multiple claims."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from .claim_orchestrator import ClaimOrchestrator

logger = logging.getLogger(__name__)


class StudyOrchestrator:
    """Run streamlined fact-checking pipeline across multiple claims and documents."""
    
    def __init__(
        self,
        claims_file: Path,
        documents: List[str],
        cache_dir: Path = Path("data/scientific_cache"),
        output_dir: Path = Path("data/studies"),
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize streamlined study orchestrator.
        
        Args:
            claims_file: Path to JSON file containing claims
            documents: List of document names to check
            cache_dir: Base cache directory
            output_dir: Directory for study results
            config: Configuration for agents and orchestration
        """
        self.claims_file = Path(claims_file)
        self.documents = documents
        self.cache_dir = Path(cache_dir)
        self.output_dir = Path(output_dir)
        self.config = config or {}
        
        # Load claims
        self.claims = self._load_claims()
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_claims(self) -> List[Dict[str, str]]:
        """Load claims from JSON file."""
        with open(self.claims_file, 'r') as f:
            data = json.load(f)
        
        claims = data.get("claims", [])
        
        # Add IDs if not present
        for i, claim in enumerate(claims):
            if "id" not in claim:
                claim["id"] = f"claim_{i:03d}"
        
        return claims
    
    async def process(self) -> Dict[str, Any]:
        """
        Process all claims across all documents.
        
        Returns:
            Study results dictionary
        """
        logger.info(f"Starting streamlined study: {len(self.claims)} claims × {len(self.documents)} documents")
        
        study_results = {
            "metadata": {
                "claims_file": str(self.claims_file),
                "documents": self.documents,
                "total_claims": len(self.claims),
                "started_at": datetime.now().isoformat()
            },
            "claims": {}
        }
        
        # Process claims with limited parallelism
        import asyncio
        
        # Simple parallelism - process 2-3 claims at once
        max_concurrent_claims = self.config.get("max_concurrent_claims", 2)
        logger.info(f"Processing claims with max {max_concurrent_claims} concurrent")
        
        semaphore = asyncio.Semaphore(max_concurrent_claims)
        
        async def process_single_claim(i, claim_data):
            async with semaphore:
                claim_id = claim_data["id"]
                claim_text = claim_data["claim"]
                
                logger.info(f"\n[Claim {i+1}/{len(self.claims)}] Starting: {claim_text[:50]}...")
                
                # Create claim orchestrator
                claim_orchestrator = ClaimOrchestrator(
                    claim_id=claim_id,
                    claim_text=claim_text,
                    documents=self.documents,
                    cache_dir=self.cache_dir,
                    config=self.config
                )
                
                # Process claim
                try:
                    claim_results = await claim_orchestrator.process()
                    
                    # Print progress
                    logger.info(f"[Claim {i+1}/{len(self.claims)}] Completed: {claim_text[:50]}...")
                    self._print_claim_summary(claim_id, claim_text, claim_results)
                    
                    return claim_id, claim_results
                    
                except Exception as e:
                    logger.error(f"[Claim {i+1}/{len(self.claims)}] Failed: {claim_id}: {e}")
                    return claim_id, {
                        "claim_id": claim_id,
                        "claim": claim_text,
                        "error": str(e),
                        "documents": {}
                    }
        
        # Create all tasks
        tasks = [
            process_single_claim(i, claim_data) 
            for i, claim_data in enumerate(self.claims)
        ]
        
        # Run with controlled parallelism
        results = await asyncio.gather(*tasks)
        
        # Store results
        for claim_id, claim_result in results:
            study_results["claims"][claim_id] = claim_result
        
        study_results["metadata"]["completed_at"] = datetime.now().isoformat()
        
        # Generate summary
        study_results["summary"] = self._generate_summary(study_results)
        
        # Save results
        self.save_results(study_results)
        
        return study_results
    
    def _print_claim_summary(self, claim_id: str, claim_text: str, results: Dict[str, Any]):
        """Print summary of claim processing."""
        print("-" * 60)
        print(f"Claim: {claim_text[:70]}...")
        
        total_evidence = 0
        for doc_name, doc_result in results.get("documents", {}).items():
            evidence_count = len(doc_result.get("supporting_evidence", []))
            total_evidence += evidence_count
            print(f"  {doc_name}: {evidence_count} evidence pieces")
        
        print(f"  Total evidence: {total_evidence}")
    
    def _generate_summary(self, study_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary statistics."""
        total_pairs = 0
        successful_pairs = 0
        evidence_by_claim = {}  # Track evidence per claim across all documents
        coverage_dist = {"complete": 0, "partial": 0, "none": 0}
        
        for claim_id, claim_result in study_results["claims"].items():
            claim_evidence_count = 0
            
            for doc_name, doc_result in claim_result.get("documents", {}).items():
                total_pairs += 1
                if doc_result.get("success", False):
                    successful_pairs += 1
                    
                    # Count evidence
                    evidence_count = len(doc_result.get("supporting_evidence", []))
                    claim_evidence_count += evidence_count
                    
                    # Track coverage
                    coverage = doc_result.get("evidence_summary", {}).get("coverage", "none")
                    if coverage in coverage_dist:
                        coverage_dist[coverage] += 1
            
            # Store total evidence for this claim across all documents
            evidence_by_claim[claim_id] = claim_evidence_count
        
        # Calculate average evidence per claim (not per pair)
        all_evidence_counts = list(evidence_by_claim.values())
        avg_evidence_per_claim = sum(all_evidence_counts) / len(all_evidence_counts) if all_evidence_counts else 0
        
        return {
            "total_claim_document_pairs": total_pairs,
            "successfully_processed": successful_pairs,
            "processing_rate": successful_pairs / total_pairs if total_pairs > 0 else 0,
            "average_evidence_per_claim": avg_evidence_per_claim,
            "average_evidence_per_successful_pair": sum(all_evidence_counts) / successful_pairs if successful_pairs > 0 else 0,
            "coverage_distribution": coverage_dist,
            "claims_with_no_evidence": sum(1 for count in all_evidence_counts if count == 0),
            "claims_with_evidence": sum(1 for count in all_evidence_counts if count > 0)
        }
    
    def save_results(self, results: Dict[str, Any]):
        """Save study results to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"study_results_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"\nResults saved to: {output_file}")
        
        # Also save consolidated JSON format
        try:
            from ..formatters import ConsolidatedJsonFormatter
            
            # JSON consolidated format
            json_formatter = ConsolidatedJsonFormatter(self.output_dir)
            consolidated = json_formatter.format(results)
            consolidated_path = json_formatter.save(consolidated)
            logger.info(f"Consolidated results saved to: {consolidated_path}")
            
        except Exception as e:
            logger.warning(f"Failed to save consolidated format: {e}")
        
        # Print final summary
        summary = results["summary"]
        print("\n" + "=" * 60)
        print("Study Complete")
        print("=" * 60)
        print(f"Total claims: {len(self.claims)}")
        print(f"Total documents: {len(self.documents)}")
        print(f"Claim-document pairs processed: {summary['successfully_processed']}/{summary['total_claim_document_pairs']}")
        print(f"\nCoverage distribution:")
        for coverage, count in summary['coverage_distribution'].items():
            print(f"  {coverage}: {count}")
        print(f"\nAverage evidence per claim: {summary['average_evidence_per_claim']:.1f}")
