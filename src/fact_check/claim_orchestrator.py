"""Claim-centric orchestrator for evidence extraction across multiple documents."""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from .agents.supporting_evidence_extractor import SupportingEvidenceExtractor

logger = logging.getLogger(__name__)


class ClaimOrchestrator:
    """Orchestrate evidence extraction for claims across multiple documents."""
    
    def __init__(
        self,
        claims_file: str,
        documents: List[str],
        cache_dir: Path = Path("data/cache"),
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the claim orchestrator.
        
        Args:
            claims_file: Path to JSON file containing claims
            documents: List of PDF names to search
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
        Run evidence extraction for all claims across all documents.
        
        Returns:
            Dictionary containing all results
        """
        self.results["metadata"]["started_at"] = datetime.now().isoformat()
        
        # Process each claim
        for idx, claim_data in enumerate(self.claims):
            claim_id = f"claim_{idx:03d}"
            claim_text = claim_data["claim"]
            
            print(f"\n{'='*60}")
            print(f"Processing {claim_id} ({idx+1}/{len(self.claims)})")
            print(f"Claim: {claim_text[:100]}...")
            print(f"{'='*60}")
            
            claim_results = await self._process_claim(claim_id, claim_text)
            self.results["claims"][claim_id] = claim_results
        
        self.results["metadata"]["completed_at"] = datetime.now().isoformat()
        
        # Generate summary statistics
        self._generate_summary()
        
        return self.results
    
    async def _process_claim(self, claim_id: str, claim_text: str) -> Dict[str, Any]:
        """Process a single claim across all documents."""
        claim_result = {
            "claim_id": claim_id,
            "claim": claim_text,
            "documents": {},
            "summary": {
                "total_documents": len(self.documents),
                "documents_with_evidence": 0,
                "total_snippets": 0
            }
        }
        
        # Check each document
        for document in self.documents:
            print(f"\n  Checking: {document}")
            
            # Check if already cached
            cached_result = self._get_cached_result(document, claim_id)
            
            if cached_result:
                print(f"    ✓ Using cached result ({cached_result['total_snippets_found']} snippets)")
                doc_result = cached_result
            else:
                print(f"    → Extracting evidence...")
                doc_result = await self._extract_from_document(document, claim_text, claim_id)
                
                if doc_result["extraction_result"]["success"]:
                    snippets_found = doc_result["extraction_result"]["total_snippets_found"]
                    print(f"    ✓ Found {snippets_found} supporting snippets")
                else:
                    print(f"    ✗ Extraction failed: {doc_result['extraction_result']['error']}")
            
            # Add to results
            claim_result["documents"][document] = doc_result
            
            # Update summary
            if doc_result["extraction_result"]["success"] and doc_result["extraction_result"]["total_snippets_found"] > 0:
                claim_result["summary"]["documents_with_evidence"] += 1
                claim_result["summary"]["total_snippets"] += doc_result["extraction_result"]["total_snippets_found"]
        
        # Print summary for this claim
        print(f"\n  Summary: {claim_result['summary']['total_snippets']} snippets from "
              f"{claim_result['summary']['documents_with_evidence']}/{len(self.documents)} documents")
        
        return claim_result
    
    async def _extract_from_document(self, document: str, claim: str, claim_id: str) -> Dict[str, Any]:
        """Extract evidence from a single document."""
        try:
            # Create agent instance
            agent_config = self.config.get("agent_config", {})
            agent = SupportingEvidenceExtractor(
                pdf_name=document,
                cache_dir=self.cache_dir,
                config=agent_config
            )
            
            # Extract evidence
            result = await agent.process_claim(claim, claim_id)
            
            # Save to cache
            self._save_to_cache(document, claim_id, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to extract from {document}: {e}")
            return {
                "claim_id": claim_id,
                "claim": claim,
                "document": {"pdf_name": document},
                "extraction_result": {
                    "success": False,
                    "total_snippets_found": 0,
                    "error": str(e)
                },
                "supporting_snippets": []
            }
    
    def _get_cached_result(self, document: str, claim_id: str) -> Optional[Dict[str, Any]]:
        """Check if we have cached results for this claim/document pair."""
        cache_path = (
            self.cache_dir / document / "agents" / "claims" / 
            claim_id / "supporting_evidence" / "extracted_snippets.json"
        )
        
        if cache_path.exists():
            try:
                with open(cache_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cached result: {e}")
                return None
        
        return None
    
    def _save_to_cache(self, document: str, claim_id: str, result: Dict[str, Any]):
        """Save extraction result to cache."""
        cache_dir = (
            self.cache_dir / document / "agents" / "claims" / 
            claim_id / "supporting_evidence"
        )
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Save the result
        with open(cache_dir / "extracted_snippets.json", 'w') as f:
            json.dump(result, f, indent=2)
        
        # Also save just the claim for reference
        claim_file = cache_dir.parent / "claim.json"
        with open(claim_file, 'w') as f:
            json.dump({
                "claim_id": claim_id,
                "claim": result["claim"]
            }, f, indent=2)
    
    def _generate_summary(self):
        """Generate summary statistics."""
        total_snippets = 0
        claims_with_evidence = 0
        document_coverage = {doc: 0 for doc in self.documents}
        
        for claim_id, claim_data in self.results["claims"].items():
            if claim_data["summary"]["total_snippets"] > 0:
                claims_with_evidence += 1
            
            total_snippets += claim_data["summary"]["total_snippets"]
            
            for doc in self.documents:
                if doc in claim_data["documents"]:
                    doc_result = claim_data["documents"][doc]
                    if doc_result["extraction_result"]["success"] and doc_result["extraction_result"]["total_snippets_found"] > 0:
                        document_coverage[doc] += 1
        
        self.results["summary"] = {
            "total_claims": len(self.claims),
            "claims_with_evidence": claims_with_evidence,
            "total_snippets_extracted": total_snippets,
            "document_coverage": document_coverage,
            "average_snippets_per_claim": total_snippets / len(self.claims) if self.claims else 0
        }
    
    def save_results(self, output_path: Optional[Path] = None):
        """Save orchestration results to file."""
        if output_path is None:
            output_dir = Path("data/studies/evidence_collection")
            output_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = output_dir / f"evidence_extraction_{timestamp}.json"
        
        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\nResults saved to: {output_path}")
        return output_path