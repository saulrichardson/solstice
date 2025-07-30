"""Generate visual evidence reports from fact-checking results."""

import json
from pathlib import Path
from typing import Dict, List, Any


def generate_evidence_report(
    claim_id: str,
    document: str,
    cache_dir: Path = Path("data/cache"),
    output_path: Optional[Path] = None
) -> Path:
    """
    Generate an HTML report with text quotes and supporting images.
    
    Args:
        claim_id: Claim identifier (e.g., "claim_000")
        document: Document name
        cache_dir: Base cache directory
        output_path: Where to save report (default: same as presenter output)
        
    Returns:
        Path to generated report
    """
    # Load presenter output
    presenter_path = (
        cache_dir / document / "agents" / "claims" / claim_id / 
        "evidence_presenter" / "output.json"
    )
    
    if not presenter_path.exists():
        raise FileNotFoundError(f"No presenter output found for {claim_id} in {document}")
    
    with open(presenter_path) as f:
        presenter_data = json.load(f)
    
    # Extract data
    claim_text = presenter_data["claim"]
    text_evidence = presenter_data.get("supporting_evidence", [])
    image_evidence = presenter_data.get("image_evidence", [])
    
    # Build HTML
    html_parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<title>Evidence Report</title>",
        "<style>",
        "body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }",
        "h1 { color: #333; border-bottom: 2px solid #0066cc; padding-bottom: 10px; }",
        "h2 { color: #0066cc; margin-top: 30px; }",
        ".evidence-section { margin: 20px 0; padding: 20px; background: #f5f5f5; border-radius: 8px; }",
        "blockquote { border-left: 4px solid #0066cc; padding-left: 20px; margin: 20px 0; }",
        ".explanation { color: #666; font-style: italic; margin-top: 10px; }",
        "figure { margin: 20px 0; text-align: center; }",
        "figure img { max-width: 100%; height: auto; border: 1px solid #ddd; }",
        "figcaption { margin-top: 10px; color: #666; }",
        ".stats { background: #e8f4f8; padding: 15px; border-radius: 5px; margin: 20px 0; }",
        "</style>",
        "</head>",
        "<body>",
        
        f"<h1>Evidence Report</h1>",
        f"<div class='stats'>",
        f"<strong>Document:</strong> {document}<br>",
        f"<strong>Claim:</strong> {claim_text}<br>",
        f"<strong>Evidence Found:</strong> {len(text_evidence)} text quotes, {len(image_evidence)} supporting images",
        f"</div>",
    ]
    
    # Add text evidence
    if text_evidence:
        html_parts.append("<h2>Text Evidence</h2>")
        for i, evidence in enumerate(text_evidence, 1):
            html_parts.extend([
                "<div class='evidence-section'>",
                f"<h3>Quote {i}</h3>",
                f"<blockquote>{evidence['quote']}</blockquote>",
                f"<div class='explanation'>{evidence['explanation']}</div>",
                "</div>"
            ])
    
    # Add image evidence
    if image_evidence:
        html_parts.append("<h2>Visual Evidence</h2>")
        
        # Group by support status
        supporting = [img for img in image_evidence if img.get("supports_claim", False)]
        
        for img in supporting:
            # Build full image path
            img_path = cache_dir / img["image_path"]
            
            # Convert to relative path for HTML
            rel_path = img_path.relative_to(cache_dir / document)
            
            html_parts.extend([
                "<figure>",
                f"<img src='{rel_path}' alt='{img.get('image_type', 'Figure')}'>",
                f"<figcaption>",
                f"<strong>{img.get('image_type', 'Figure')} from page {img.get('page_number', '?')}</strong><br>",
                f"{img.get('explanation', '')}",
                f"</figcaption>",
                "</figure>"
            ])
    
    html_parts.extend([
        "</body>",
        "</html>"
    ])
    
    # Save report
    if output_path is None:
        output_path = presenter_path.parent / "evidence_report.html"
    
    output_path.write_text("\n".join(html_parts))
    
    print(f"Report generated: {output_path}")
    print(f"Open in browser: file://{output_path.absolute()}")
    
    return output_path


def generate_study_summary_report(
    study_results_path: Path,
    output_dir: Path = Path("data/reports")
) -> Path:
    """Generate a summary report for an entire study."""
    output_dir.mkdir(exist_ok=True)
    
    with open(study_results_path) as f:
        study_data = json.load(f)
    
    # Generate individual claim reports
    for claim_id, claim_data in study_data["claims"].items():
        for doc_name, doc_result in claim_data.get("documents", {}).items():
            if doc_result.get("success") and doc_result.get("supporting_evidence"):
                try:
                    generate_evidence_report(
                        claim_id=claim_id,
                        document=doc_name,
                        output_path=output_dir / f"{claim_id}_{doc_name}_evidence.html"
                    )
                except Exception as e:
                    print(f"Failed to generate report for {claim_id}/{doc_name}: {e}")
    
    return output_dir