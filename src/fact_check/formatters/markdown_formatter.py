"""Markdown formatter for human-readable study reports."""

from pathlib import Path
from typing import Dict, Any
from datetime import datetime

from .base_formatter import BaseFormatter
from .evidence_utils import extract_all_evidence


class MarkdownFormatter(BaseFormatter):
    """Formats study results into markdown documents."""
    
    def format(self, study_results: Dict[str, Any]) -> str:
        """Format study results into markdown."""
        md_lines = []
        
        # Header
        study_name = study_results.get("metadata", {}).get("study_name", "Fact-Checking Study")
        timestamp = study_results.get("metadata", {}).get("completed_at", datetime.now().isoformat())
        
        md_lines.extend([
            f"# {study_name} - Results Report",
            f"",
            f"**Generated:** {timestamp}",
            f"",
            "---",
            ""
        ])
        
        # Summary statistics
        summary = study_results.get("summary", {})
        md_lines.extend([
            "## Summary",
            "",
            f"- **Total Claims:** {len(study_results.get('claims', {}))}",
            f"- **Total Documents:** {len(study_results.get('metadata', {}).get('documents', []))}",
            f"- **Claims with Evidence:** {summary.get('claims_with_evidence', 0)}",
            f"- **Average Evidence per Claim:** {summary.get('average_evidence_per_claim', 0):.1f}",
            "",
            "---",
            ""
        ])
        
        # Claims and evidence
        md_lines.extend([
            "## Claims and Supporting Evidence",
            ""
        ])
        
        for claim_id, claim_data in study_results.get("claims", {}).items():
            claim_text = claim_data.get("claim_text", "")
            
            # Claim header
            md_lines.extend([
                f"### {claim_id.replace('_', ' ').title()}: {claim_text}",
                ""
            ])
            
            evidence_found = False
            
            # Process each document
            for doc_name, doc_result in claim_data.get("documents", {}).items():
                if not doc_result.get("success"):
                    continue
                
                # Extract all evidence using utility function
                all_evidence = extract_all_evidence(doc_result)
                
                if all_evidence:
                    evidence_found = True
                    md_lines.extend([
                        f"#### Source: {doc_name}",
                        ""
                    ])
                    
                    # Group by type
                    text_items = [e for e in all_evidence if e["type"] == "text"]
                    image_items = [e for e in all_evidence if e["type"] == "image"]
                    
                    # Text evidence
                    if text_items:
                        md_lines.append("**Text Evidence:**")
                        md_lines.append("")
                        for i, evidence in enumerate(text_items, 1):
                            quote = evidence["quote"]
                            explanation = evidence["explanation"]
                            md_lines.extend([
                                f"{i}. > {quote}",
                                f"   ",
                                f"   *{explanation}*",
                                ""
                            ])
                    
                    # Image evidence
                    if image_items:
                        md_lines.append("**Visual Evidence:**")
                        md_lines.append("")
                        for img in image_items:
                            filename = img["filename"]
                            reasoning = img["reasoning"]
                            md_lines.extend([
                                f"- **{filename}**: {reasoning}",
                                ""
                            ])
            
            if not evidence_found:
                md_lines.extend([
                    "*No supporting evidence found in the analyzed documents.*",
                    ""
                ])
            
            md_lines.append("---")
            md_lines.append("")
        
        return "\n".join(md_lines)
    
    def save(self, formatted_results: str, filename: str = "study_report.md") -> Path:
        """Save formatted results to markdown file."""
        output_path = self.output_dir / filename
        
        with open(output_path, 'w') as f:
            f.write(formatted_results)
        
        return output_path