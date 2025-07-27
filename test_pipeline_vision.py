#!/usr/bin/env python3
"""Test the vision-enhanced pipeline with caption association."""

import json
from pathlib import Path
from src.injestion.pipeline_vision import ingest_pdf_vision, extract_content_with_groups


def test_vision_pipeline():
    """Test the vision pipeline on a PDF."""
    
    pdf_path = Path("Liu et al. (2024).pdf")
    if not pdf_path.exists():
        print(f"Error: {pdf_path} not found")
        return
    
    print("Testing Vision-Enhanced Pipeline")
    print("="*70)
    
    # Process with vision pipeline
    print("\nProcessing PDF with vision-based caption association...")
    refined_pages = ingest_pdf_vision(
        pdf_path,
        detection_dpi=200,
        merge_strategy="weighted",
        use_vision_captions=True,
        debug=False
    )
    
    print(f"\nProcessed {len(refined_pages)} pages")
    
    # Extract content with groups
    print("\nExtracting content with semantic groups...")
    extracted = extract_content_with_groups(refined_pages)
    
    # Print summary
    print("\n" + "="*70)
    print("EXTRACTION SUMMARY:")
    print("="*70)
    
    metadata = extracted["metadata"]
    print(f"Total pages: {metadata['total_pages']}")
    print(f"\nFigures:")
    print(f"  Total: {metadata['total_figures']}")
    print(f"  With captions: {metadata['figures_with_captions']}")
    if metadata['total_figures'] > 0:
        caption_rate = metadata['figures_with_captions'] / metadata['total_figures'] * 100
        print(f"  Caption rate: {caption_rate:.1f}%")
    
    print(f"\nTables:")
    print(f"  Total: {metadata['total_tables']}")
    print(f"  With captions: {metadata['tables_with_captions']}")
    if metadata['total_tables'] > 0:
        caption_rate = metadata['tables_with_captions'] / metadata['total_tables'] * 100
        print(f"  Caption rate: {caption_rate:.1f}%")
    
    # Save detailed results
    output_file = Path("vision_pipeline_results.json")
    with open(output_file, "w") as f:
        json.dump(extracted, f, indent=2)
    
    print(f"\nDetailed results saved to {output_file}")
    
    # Show example figure with caption
    for fig in extracted["figures"]:
        if fig["has_caption"]:
            print("\nExample figure with caption:")
            print(f"  Page: {fig['page']}")
            print(f"  Figure bbox: {fig['bbox']}")
            print(f"  Caption bbox: {fig['caption_bbox']}")
            print(f"  Association confidence: {fig['group_confidence']:.2f}")
            break


def compare_pipelines():
    """Compare simple pipeline vs vision pipeline."""
    
    pdf_path = Path("Liu et al. (2024).pdf")
    if not pdf_path.exists():
        print(f"Error: {pdf_path} not found")
        return
    
    print("Comparing Simple vs Vision Pipeline")
    print("="*70)
    
    # Process with simple pipeline
    from src.injestion.pipeline_simple import ingest_pdf_simple
    
    print("\n1. Processing with simple pipeline...")
    simple_pages = ingest_pdf_simple(pdf_path)
    
    # Count figures and tables in simple pipeline
    simple_figures = 0
    simple_tables = 0
    for page in simple_pages:
        simple_figures += sum(1 for b in page.boxes if b.label == "Figure")
        simple_tables += sum(1 for b in page.boxes if b.label == "Table")
    
    print(f"   Found {simple_figures} figures, {simple_tables} tables")
    
    # Process with vision pipeline
    print("\n2. Processing with vision pipeline...")
    vision_pages = ingest_pdf_vision(
        pdf_path,
        use_vision_captions=True,
        debug=False
    )
    
    extracted = extract_content_with_groups(vision_pages)
    metadata = extracted["metadata"]
    
    print(f"   Found {metadata['total_figures']} figures ({metadata['figures_with_captions']} with captions)")
    print(f"   Found {metadata['total_tables']} tables ({metadata['tables_with_captions']} with captions)")
    
    # Compare results
    print("\n" + "="*70)
    print("COMPARISON:")
    print("="*70)
    
    print("\nSimple Pipeline:")
    print(f"  - Detects layout elements: ✓")
    print(f"  - Merges overlapping boxes: ✓")
    print(f"  - Associates captions: ✗")
    
    print("\nVision Pipeline:")
    print(f"  - Detects layout elements: ✓")
    print(f"  - Merges overlapping boxes: ✓")
    print(f"  - Associates captions: ✓")
    print(f"  - Caption accuracy: {metadata['figures_with_captions']}/{metadata['total_figures']} figures")
    
    print("\nThe vision pipeline provides semantic grouping of figures/tables with their captions,")
    print("enabling better downstream extraction and understanding.")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "compare":
        compare_pipelines()
    else:
        test_vision_pipeline()