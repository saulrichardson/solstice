#!/usr/bin/env python3
"""Test script for layout parser with Liu et al. (2024).pdf"""

import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from injestion.pipeline import ingest_pdf
from injestion.layout_pipeline import LayoutDetectionPipeline
import layoutparser as lp


def test_layout_detection_only():
    """Test the raw layout detection without LLM refinement."""
    print("=== Testing Layout Detection Only ===")
    
    pdf_path = "Liu et al. (2024).pdf"
    
    # Check available backends
    print(f"Available backends:")
    print(f"  - Detectron2: {lp.is_detectron2_available()}")
    print(f"  - PyTorch: {lp.is_torch_available()}")
    print(f"  - PaddlePaddle: {lp.is_paddle_available()}")
    
    # Fix the downloaded model files if needed
    import os
    import glob
    cache_dir = os.path.expanduser("~/.torch/iopath_cache/s/")
    if os.path.exists(cache_dir):
        for dirpath, _, filenames in os.walk(cache_dir):
            for filename in filenames:
                if filename.endswith("?dl=1"):
                    old_path = os.path.join(dirpath, filename)
                    new_path = old_path[:-5]  # Remove ?dl=1
                    if not os.path.exists(new_path):
                        try:
                            os.rename(old_path, new_path)
                            print(f"Fixed: {filename} -> {os.path.basename(new_path)}")
                        except:
                            pass
    
    pipeline = LayoutDetectionPipeline()
    
    try:
        layouts = pipeline.process_pdf(pdf_path)
        print(f"\nSuccessfully processed {len(layouts)} pages")
        
        for page_idx, page_layout in enumerate(layouts):
            print(f"\nPage {page_idx + 1}:")
            print(f"  Detected {len(page_layout)} layout elements")
            
            for elem in page_layout:
                bbox = elem.block
                label = elem.type if elem.type else "Unknown"
                score = elem.score if elem.score else 0.0
                print(f"  - {label}: bbox=({bbox.x_1:.1f}, {bbox.y_1:.1f}, {bbox.x_2:.1f}, {bbox.y_2:.1f}), score={score:.3f}")
                
    except Exception as e:
        print(f"Error in layout detection: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


def test_full_pipeline():
    """Test the full pipeline including LLM refinement."""
    print("\n\n=== Testing Full Pipeline with LLM Refinement ===")
    
    pdf_path = "Liu et al. (2024).pdf"
    
    try:
        refined_pages = ingest_pdf(pdf_path)
        print(f"Successfully processed {len(refined_pages)} pages with refinement")
        
        for page_idx, refined_page in enumerate(refined_pages):
            print(f"\nPage {page_idx + 1} (Refined):")
            print(f"  Refined to {len(refined_page.boxes)} elements")
            print(f"  Reading order: {refined_page.reading_order}")
            
            for box in refined_page.boxes:
                print(f"  - ID: {box.id}, Label: {box.label}, bbox=({box.bbox[0]:.1f}, {box.bbox[1]:.1f}, {box.bbox[2]:.1f}, {box.bbox[3]:.1f}), score={box.score:.3f}")
                
    except Exception as e:
        print(f"Error in full pipeline: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


def save_results_json():
    """Save detection results to JSON for further analysis."""
    print("\n\n=== Saving Results to JSON ===")
    
    pdf_path = "Liu et al. (2024).pdf"
    pipeline = LayoutDetectionPipeline()
    
    try:
        layouts = pipeline.process_pdf(pdf_path)
        
        # Convert to JSON-serializable format
        results = []
        for page_idx, page_layout in enumerate(layouts):
            page_data = {
                "page": page_idx + 1,
                "elements": []
            }
            
            for elem in page_layout:
                elem_data = {
                    "type": str(elem.type) if elem.type else "Unknown",
                    "bbox": {
                        "x1": float(elem.block.x_1),
                        "y1": float(elem.block.y_1),
                        "x2": float(elem.block.x_2),
                        "y2": float(elem.block.y_2)
                    },
                    "score": float(elem.score) if elem.score else 0.0
                }
                page_data["elements"].append(elem_data)
            
            results.append(page_data)
        
        # Save to file
        output_path = "layout_detection_results.json"
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"Results saved to {output_path}")
        
    except Exception as e:
        print(f"Error saving results: {type(e).__name__}: {e}")


if __name__ == "__main__":
    print("Starting layout parser test...\n")
    
    # Run layout detection only first
    test_layout_detection_only()
    
    # Uncomment to test full pipeline with LLM refinement
    # Note: This requires the gateway to be running and configured
    # test_full_pipeline()
    
    # Save results for analysis
    save_results_json()