"""Orchestrator for processing all claims across all documents."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from .claim_orchestrator import ClaimOrchestrator

logger = logging.getLogger(__name__)


class StudyOrchestrator:
    """Process all claims across all documents."""
    
    def __init__(
        self,
        claims_file: str,
        documents: List[str],
        cache_dir: Path = Path("data/cache"),
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize study orchestrator.
        
        Args:
            claims_file: Path to JSON file containing claims
            documents: List of document names to process
            cache_dir: Base cache directory
            config: Configuration options
        """
        self.claims_file = Path(claims_file)
        self.documents = documents
        self.cache_dir = Path(cache_dir)
        self.config = config or {}
        
        # Load claims
        self.claims = self._load_claims()
        
        # Results storage
        self.results = {
            "metadata": {
                "claims_file": str(self.claims_file),
                "documents": self.documents,
                "total_claims": len(self.claims),
                "started_at": None,
                "completed_at": None
            },
            "claims": {}
        }
    
    def _load_claims(self) -> List[Dict[str, str]]:
        """Load claims from JSON file."""
        if not self.claims_file.exists():
            # Try in data/claims directory
            alt_path = Path("data/claims") / self.claims_file.name
            if alt_path.exists():
                self.claims_file = alt_path
            else:
                raise FileNotFoundError(f"Claims file not found: {self.claims_file}")
        
        with open(self.claims_file, 'r') as f:
            data = json.load(f)
        
        # Handle different formats
        if isinstance(data, dict) and "claims" in data:
            claims = data["claims"]
        elif isinstance(data, list):
            claims = data
        else:
            raise ValueError(f"Invalid claims file format: {self.claims_file}")
        
        # Normalize to list of dicts
        normalized = []
        for claim in claims:
            if isinstance(claim, str):
                normalized.append({"claim": claim})
            elif isinstance(claim, dict) and "claim" in claim:
                normalized.append(claim)
            else:
                logger.warning(f"Skipping invalid claim: {claim}")
        
        return normalized
    
    async def run(self) -> Dict[str, Any]:
        """
        Run study processing all claims.
        
        Returns:
            Dictionary containing all results
        """
        self.results["metadata"]["started_at"] = datetime.now().isoformat()
        
        print(f"\n{'='*60}")
        print(f"Starting Study: {len(self.claims)} claims × {len(self.documents)} documents")
        print(f"{'='*60}\n")
        
        # Process each claim (outer loop)
        for idx, claim_data in enumerate(self.claims):
            claim_id = f"claim_{idx:03d}"
            claim_text = claim_data["claim"]
            
            print(f"\nClaim {idx+1}/{len(self.claims)}: {claim_text[:80]}...")
            print(f"{'-'*60}")
            
            # Create claim orchestrator
            claim_orchestrator = ClaimOrchestrator(
                claim_id=claim_id,
                claim_text=claim_text,
                documents=self.documents,
                cache_dir=self.cache_dir,
                config=self.config
            )
            
            # Process claim across all documents
            claim_results = await claim_orchestrator.process()
            self.results["claims"][claim_id] = claim_results
            
            # Print summary for this claim
            self._print_claim_summary(claim_results)
        
        self.results["metadata"]["completed_at"] = datetime.now().isoformat()
        
        # Generate and print overall summary
        self._generate_summary()
        self._print_study_summary()
        
        return self.results
    
    def _print_claim_summary(self, claim_results: Dict[str, Any]):
        """Print summary for a single claim."""
        successful_docs = 0
        strong_support = 0
        
        for doc_name, doc_result in claim_results["documents"].items():
            if doc_result.get("success"):
                successful_docs += 1
                judgment = doc_result.get("final_judgment", {})
                if judgment.get("verdict") in ["strongly_supported", "supported"]:
                    strong_support += 1
        
        print(f"\n  Processed: {successful_docs}/{len(self.documents)} documents")
        print(f"  Strong support in: {strong_support} documents")
    
    def _generate_summary(self):
        """Generate summary statistics."""
        total_claim_doc_pairs = len(self.claims) * len(self.documents)
        successful_pairs = 0
        
        judgment_counts = {
            "strongly_supported": 0,
            "supported": 0,
            "weakly_supported": 0,
            "unsupported": 0
        }
        
        for claim_id, claim_data in self.results["claims"].items():
            for doc_name, doc_result in claim_data["documents"].items():
                if doc_result.get("success"):
                    successful_pairs += 1
                    verdict = doc_result.get("final_judgment", {}).get("verdict")
                    if verdict in judgment_counts:
                        judgment_counts[verdict] += 1
        
        self.results["summary"] = {
            "total_claim_document_pairs": total_claim_doc_pairs,
            "successfully_processed": successful_pairs,
            "processing_rate": successful_pairs / total_claim_doc_pairs if total_claim_doc_pairs > 0 else 0,
            "judgment_distribution": judgment_counts
        }
    
    def _print_study_summary(self):
        """Print final study summary."""
        summary = self.results["summary"]
        
        print(f"\n{'='*60}")
        print("Study Complete")
        print(f"{'='*60}")
        print(f"Total claims: {len(self.claims)}")
        print(f"Total documents: {len(self.documents)}")
        print(f"Claim-document pairs processed: {summary['successfully_processed']}/{summary['total_claim_document_pairs']}")
        print(f"\nJudgment distribution:")
        for verdict, count in summary["judgment_distribution"].items():
            print(f"  {verdict}: {count}")
    
    def save_results(self, output_path: Optional[Path] = None):
        """Save study results to file."""
        if output_path is None:
            output_dir = Path("data/studies")
            output_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = output_dir / f"study_results_{timestamp}.json"
        
        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\nResults saved to: {output_path}")
        return output_path