#!/usr/bin/env python3
"""Test layout refinement on a single page"""

import json
from pathlib import Path
from pdf2image import convert_from_path
from src.injestion.layout_pipeline import LayoutDetectionPipeline
from src.injestion.agent.refine_layout import refine_page_layout, Box
import uuid

def test_single_page():
    """Test refinement on just the first page"""
    pdf_path = Path("Liu et al. (2024).pdf")
    
    print("Testing layout refinement on page 1...")
    
    # Get raw detections
    pipeline = LayoutDetectionPipeline()
    layouts = pipeline.process_pdf(pdf_path)
    
    # Convert first page to image
    images = convert_from_path(pdf_path, first_page=1, last_page=1)
    page_image = images[0]
    
    # Convert first page layout to Box format
    page_layout = layouts[0]
    boxes = [
        Box(
            id=str(uuid.uuid4())[:8],
            bbox=(
                float(elem.block.x_1),
                float(elem.block.y_1),
                float(elem.block.x_2),
                float(elem.block.y_2),
            ),
            label=str(elem.type) if elem.type else "Unknown",
            score=float(elem.score or 0.0),
        )
        for elem in page_layout
    ]
    
    print(f"Raw detection found {len(boxes)} elements")
    
    # Test refinement
    print("\nCalling GPT-4o-mini for refinement...")
    try:
        refined = refine_page_layout(0, boxes, page_image=page_image)
        
        print(f"\nRefinement complete!")
        print(f"Refined to {len(refined.boxes)} elements")
        print(f"Reading order: {refined.reading_order}")
        
        # Save results
        result = {
            "raw_count": len(boxes),
            "refined_count": len(refined.boxes),
            "raw_boxes": [{"label": b.label, "bbox": b.bbox} for b in boxes][:5],  # First 5
            "refined_boxes": [{"label": b.label, "bbox": b.bbox} for b in refined.boxes][:5],  # First 5
            "reading_order": refined.reading_order[:10]  # First 10
        }
        
        with open("single_page_refinement.json", "w") as f:
            json.dump(result, f, indent=2)
            
        print("\nResults saved to single_page_refinement.json")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_single_page()