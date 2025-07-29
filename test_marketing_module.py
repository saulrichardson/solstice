#!/usr/bin/env python3
"""Test the standalone marketing document processing module."""

import sys
from pathlib import Path
sys.path.insert(0, "src")

from injestion.marketing import MarketingPipeline


def test_marketing_pipeline():
    """Test the marketing pipeline on Flublok PDF."""
    
    # Path to marketing PDF
    pdf_path = Path("data/marketing_slide/FlublokOnePage.pdf")
    
    if not pdf_path.exists():
        print(f"Error: PDF not found at {pdf_path}")
        return
    
    print("Marketing Document Processing Test")
    print("=" * 60)
    print(f"PDF: {pdf_path.name}")
    print(f"File size: {pdf_path.stat().st_size / 1024:.1f} KB")
    print()
    
    # Test 1: Without vision adjustment
    print("Test 1: PrimaLayout only (no vision adjustment)")
    print("-" * 40)
    
    pipeline_no_vision = MarketingPipeline(use_vision_adjustment=False)
    doc_no_vision = pipeline_no_vision.process_pdf(pdf_path)
    
    print(f"\nResults:")
    print(f"  Total blocks: {len(doc_no_vision.blocks)}")
    
    # Count by type
    by_type = {}
    for block in doc_no_vision.blocks:
        by_type[block.role] = by_type.get(block.role, 0) + 1
    
    print("  Blocks by type:")
    for role, count in sorted(by_type.items()):
        print(f"    {role}: {count}")
    
    # Test 2: With vision adjustment (if API key is available)
    import os
    if os.getenv("OPENAI_API_KEY"):
        print("\n\nTest 2: PrimaLayout + Vision LLM adjustment")
        print("-" * 40)
        
        pipeline_with_vision = MarketingPipeline(use_vision_adjustment=True)
        doc_with_vision = pipeline_with_vision.process_pdf(pdf_path)
        
        print(f"\nResults:")
        print(f"  Total blocks: {len(doc_with_vision.blocks)}")
        
        # Count by type
        by_type_vision = {}
        for block in doc_with_vision.blocks:
            by_type_vision[block.role] = by_type_vision.get(block.role, 0) + 1
        
        print("  Blocks by type:")
        for role, count in sorted(by_type_vision.items()):
            print(f"    {role}: {count}")
            
        # Compare
        print("\n  Comparison:")
        print(f"    Blocks before vision: {len(doc_no_vision.blocks)}")
        print(f"    Blocks after vision: {len(doc_with_vision.blocks)}")
    else:
        print("\n\nSkipping Test 2: No OPENAI_API_KEY found")
        print("Set OPENAI_API_KEY environment variable to test vision adjustments")
    
    # Show sample extracted text
    print("\n\nSample Extracted Text")
    print("-" * 40)
    
    text_blocks = [b for b in doc_no_vision.blocks if b.role == "Text" and b.text][:5]
    for i, block in enumerate(text_blocks, 1):
        text_preview = block.text[:100] + "..." if len(block.text) > 100 else block.text
        print(f"{i}. {text_preview}")
    
    if len(text_blocks) < 5:
        print(f"\n(Showing all {len(text_blocks)} text blocks)")
    
    # Output locations
    print("\n\nOutput Locations")
    print("-" * 40)
    print(f"Marketing outputs: data/cache/{pdf_path.stem}/stages/marketing/")
    print(f"Visualizations: data/cache/{pdf_path.stem}/stages/marketing/visualizations/")


def test_detector_only():
    """Test just the detector component."""
    
    print("\n\nDetector Component Test")
    print("=" * 60)
    
    from pdf2image import convert_from_path
    from injestion.marketing.detector import MarketingLayoutDetector
    
    pdf_path = Path("data/marketing_slide/FlublokOnePage.pdf")
    images = convert_from_path(str(pdf_path), dpi=400)
    
    detector = MarketingLayoutDetector()
    layouts = detector.detect_images(images)
    
    print(f"Page 1 detections: {len(layouts[0])} regions")
    
    # Group by type
    by_type = {}
    for elem in layouts[0]:
        elem_type = str(elem.type)
        by_type[elem_type] = by_type.get(elem_type, 0) + 1
    
    print("By type:")
    for elem_type, count in sorted(by_type.items()):
        print(f"  {elem_type}: {count}")


if __name__ == "__main__":
    test_marketing_pipeline()
    test_detector_only()