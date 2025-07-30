#!/usr/bin/env python3
"""Analyze cache data to generate statistics for the writeup."""

import json
from pathlib import Path
from collections import defaultdict


def analyze_cache(cache_dir: Path = Path("../data/cache")):
    """Analyze cache directory for statistics."""
    stats = {
        "documents": 0,
        "total_pages": 0,
        "total_blocks": 0,
        "total_figures": 0,
        "total_tables": 0,
        "claims_processed": set(),
        "evidence_by_claim": defaultdict(int),
        "image_analyses": 0,
        "supporting_images": 0,
        "verification_rates": [],
        "document_stats": {}
    }
    
    # Analyze each document
    for doc_dir in cache_dir.iterdir():
        if not doc_dir.is_dir() or doc_dir.name.startswith('.'):
            continue
            
        # Skip marketing materials
        if doc_dir.name == "FlublokOnePage":
            continue
            
        stats["documents"] += 1
        doc_stats = {"name": doc_dir.name}
        
        # Load document content
        content_path = doc_dir / "extracted" / "content.json"
        if content_path.exists():
            with open(content_path) as f:
                content = json.load(f)
                
            # Count blocks and types
            blocks = content.get("blocks", [])
            doc_stats["total_blocks"] = len(blocks)
            doc_stats["figures"] = sum(1 for b in blocks if b.get("role") == "Figure")
            doc_stats["tables"] = sum(1 for b in blocks if b.get("role") == "Table")
            doc_stats["pages"] = len(content.get("reading_order", []))
            
            stats["total_blocks"] += doc_stats["total_blocks"]
            stats["total_figures"] += doc_stats["figures"]
            stats["total_tables"] += doc_stats["tables"]
            stats["total_pages"] += doc_stats["pages"]
            
        # Analyze agent outputs
        agents_dir = doc_dir / "agents" / "claims"
        if agents_dir.exists():
            for claim_dir in agents_dir.iterdir():
                if not claim_dir.is_dir():
                    continue
                    
                claim_id = claim_dir.name
                stats["claims_processed"].add(claim_id)
                
                # Check verification results
                verifier_path = claim_dir / "evidence_verifier_v2" / "output.json"
                if verifier_path.exists():
                    with open(verifier_path) as f:
                        verifier_data = json.load(f)
                    
                    verified = len(verifier_data.get("verified_evidence", []))
                    total = verifier_data.get("verification_stats", {}).get("total_extracted", 0)
                    if total > 0:
                        rate = verifier_data.get("verification_stats", {}).get("verification_rate", 0)
                        stats["verification_rates"].append(rate)
                    
                    stats["evidence_by_claim"][claim_id] += verified
                
                # Count image analyses
                img_analyzer_dir = claim_dir / "image_evidence_analyzer"
                if img_analyzer_dir.exists():
                    for img_dir in img_analyzer_dir.iterdir():
                        if img_dir.is_dir():
                            output_path = img_dir / "output.json"
                            if output_path.exists():
                                stats["image_analyses"] += 1
                                with open(output_path) as f:
                                    img_data = json.load(f)
                                if img_data.get("supports_claim"):
                                    stats["supporting_images"] += 1
        
        stats["document_stats"][doc_dir.name] = doc_stats
    
    # Calculate averages
    stats["total_claims"] = len(stats["claims_processed"])
    stats["avg_verification_rate"] = (
        sum(stats["verification_rates"]) / len(stats["verification_rates"])
        if stats["verification_rates"] else 0
    )
    stats["avg_evidence_per_claim"] = (
        sum(stats["evidence_by_claim"].values()) / len(stats["evidence_by_claim"])
        if stats["evidence_by_claim"] else 0
    )
    stats["image_support_rate"] = (
        stats["supporting_images"] / stats["image_analyses"]
        if stats["image_analyses"] > 0 else 0
    )
    
    return stats


def save_stats_for_latex(stats):
    """Save statistics in format suitable for LaTeX."""
    output = {
        "documents": stats["documents"],
        "totalPages": stats["total_pages"],
        "totalBlocks": stats["total_blocks"],
        "totalFigures": stats["total_figures"],
        "totalTables": stats["total_tables"],
        "totalClaims": stats["total_claims"],
        "avgVerificationRate": f"{stats['avg_verification_rate']:.1%}",
        "avgEvidencePerClaim": f"{stats['avg_evidence_per_claim']:.1f}",
        "totalImageAnalyses": stats["image_analyses"],
        "imageSupportRate": f"{stats['image_support_rate']:.1%}",
        "supportingImages": stats["supporting_images"]
    }
    
    with open("cache_stats.json", "w") as f:
        json.dump(output, f, indent=2)
    
    # Also create a LaTeX command file
    with open("stats.tex", "w") as f:
        f.write("% Auto-generated statistics from cache analysis\n")
        for key, value in output.items():
            cmd_name = key[0].lower() + key[1:]  # camelCase to LaTeX command
            # Properly escape backslashes for LaTeX commands
            f.write(f"\\newcommand{{\\{cmd_name}}}{{{value}}}\n")


if __name__ == "__main__":
    stats = analyze_cache()
    save_stats_for_latex(stats)
    
    # Print summary
    print(f"Analyzed {stats['documents']} documents")
    print(f"Total pages: {stats['total_pages']}")
    print(f"Total visual elements: {stats['total_figures'] + stats['total_tables']}")
    print(f"Claims processed: {stats['total_claims']}")
    print(f"Average verification rate: {stats['avg_verification_rate']:.1%}")
    print(f"Image analyses: {stats['image_analyses']}")
    print(f"Image support rate: {stats['image_support_rate']:.1%}")