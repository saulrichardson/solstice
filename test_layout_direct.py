#!/usr/bin/env python3
"""Direct test of layout detection bypassing the injestion __init__.py"""

import sys
sys.path.insert(0, "src")

# Import pipeline components directly
from pathlib import Path
from pdf2image import convert_from_path
from injestion.processing.layout_detector import LayoutDetectionPipeline
from injestion.storage.paths import pages_dir, stage_dir
from injestion.visualization.layout_visualizer import visualize_page_layout
from injestion.models.document import Block

def test_layout_detection():
    # Your marketing PDF
    pdf_path = Path("/Users/saul/projects/solstice/solstice/data/marketing_slide/FlublokOnePage.pdf")
    
    print(f"Testing layout detection on: {pdf_path.name}")
    print("-" * 50)
    
    # Convert PDF to images
    print("Converting PDF to images...")
    images = convert_from_path(str(pdf_path), dpi=400)
    print(f"  - Generated {len(images)} page images")
    
    # Run layout detection
    print("\nRunning layout detection...")
    detector = LayoutDetectionPipeline()
    layouts = detector.detect_images(images)
    
    # Analyze results
    for page_idx, (layout, image) in enumerate(zip(layouts, images)):
        print(f"\nPage {page_idx + 1}:")
        print(f"  - Image size: {image.width}x{image.height}")
        print(f"  - Detected {len(layout)} boxes:")
        
        # Group by type
        by_type = {}
        for box in layout:
            by_type.setdefault(str(box.type), []).append(box)
        
        for box_type, boxes in sorted(by_type.items()):
            print(f"    - {box_type}: {len(boxes)} boxes")
        
        # Show individual boxes
        print("\n  Detailed boxes:")
        for i, box in enumerate(layout):
            coords = f"({box.block.x_1:.0f},{box.block.y_1:.0f}) to ({box.block.x_2:.0f},{box.block.y_2:.0f})"
            print(f"    {i+1}. {box.type}: {coords} [score: {box.score:.2f}]")
        
        # Create visualization
        output_path = f"flublok_layout_test_p{page_idx+1}.png"
        print(f"\n  Saving visualization to: {output_path}")
        
        # Convert to Block objects for visualizer
        blocks = []
        for idx, box in enumerate(layout):
            block = Block(
                id=str(idx),
                page_index=page_idx,
                role=str(box.type),
                bbox=(box.block.x_1, box.block.y_1, box.block.x_2, box.block.y_2),
                metadata={"score": float(box.score)}
            )
            blocks.append(block)
        
        visualize_page_layout(
            image,
            blocks,
            reading_order=None,
            title=f"Layout Detection - Page {page_idx + 1}",
            save_path=output_path,
            show_labels=True,
            show_reading_order=False
        )

if __name__ == "__main__":
    test_layout_detection()