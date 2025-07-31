"""Formatter that creates consolidated JSON output matching desired format."""

import json
from pathlib import Path
from typing import Dict, Any, List

from .base_formatter import BaseFormatter


class ConsolidatedJsonFormatter(BaseFormatter):
    """Formats study results into consolidated JSON structure."""
    
    def format(self, study_results: Dict[str, Any]) -> Dict[str, Any]:
        """Format study results into consolidated structure.
        
        Creates a flat list of claims with their supporting evidence.
        """
        consolidated = {
            "study_name": study_results.get("metadata", {}).get("study_name", "unknown"),
            "timestamp": study_results.get("metadata", {}).get("completed_at"),
            "claims": []
        }
        
        # Process each claim
        for claim_id, claim_data in study_results.get("claims", {}).items():
            claim_text = claim_data.get("claim", "")
            
            # For each claim, create an entry with all its evidence
            claim_entry = {
                "claim": claim_text,
                "evidence": []
            }
            
            # Process evidence from each document
            for doc_name, doc_result in claim_data.get("documents", {}).items():
                if not doc_result.get("success"):
                    continue
                
                # Extract text evidence
                text_evidence = doc_result.get("supporting_evidence", [])
                for evidence in text_evidence:
                    claim_entry["evidence"].append({
                        "type": "text",
                        "document": doc_name,
                        "quote": evidence.get("quote", ""),
                        "explanation": evidence.get("explanation", "")
                    })
                
                # Extract image evidence
                image_evidence = doc_result.get("image_evidence", [])
                for img in image_evidence:
                    if img.get("supports_claim", True):  # Default to True if not specified
                        # For images, only include key fields
                        detailed = img.get("detailed_analysis", {})
                        reasoning = detailed.get("reasoning", img.get("explanation", ""))
                        
                        claim_entry["evidence"].append({
                            "type": "image",
                            "document": doc_name,
                            "filename": img.get("image_filename", ""),
                            "reasoning": reasoning
                        })
            
            # Only include claims that have evidence
            if claim_entry["evidence"]:
                consolidated["claims"].append(claim_entry)
        
        return consolidated
    
    def save(self, formatted_results: Dict[str, Any], filename: str = "consolidated_results.json") -> Path:
        """Save formatted results to JSON file."""
        output_path = self.output_dir / filename
        
        with open(output_path, 'w') as f:
            json.dump(formatted_results, f, indent=2)
        
        return output_path
    
    def create_summary(self, formatted_results: Dict[str, Any]) -> Dict[str, Any]:
        """Create a summary of the consolidated results."""
        claims = formatted_results.get("claims", [])
        
        total_claims = len(claims)
        total_evidence = sum(len(claim["evidence"]) for claim in claims)
        
        # Count evidence by document and type
        doc_evidence_count = {}
        type_count = {"text": 0, "image": 0}
        
        for claim in claims:
            for evidence in claim["evidence"]:
                doc_name = evidence["document"]
                doc_evidence_count[doc_name] = doc_evidence_count.get(doc_name, 0) + 1
                
                evidence_type = evidence.get("type", "text")
                type_count[evidence_type] = type_count.get(evidence_type, 0) + 1
        
        return {
            "total_claims_with_evidence": total_claims,
            "total_evidence_pieces": total_evidence,
            "average_evidence_per_claim": total_evidence / total_claims if total_claims > 0 else 0,
            "evidence_by_document": doc_evidence_count,
            "evidence_by_type": type_count
        }