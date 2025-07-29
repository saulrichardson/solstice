#!/usr/bin/env python3
"""Test layout detection on marketing PDF"""

from pathlib import Path
from pdf2image import convert_from_path
from injestion.processing.layout_detector import LayoutDetectionPipeline
from injestion.models.document import Block
from injestion.visualization.layout_visualizer import visualize_page_layout

def main():
    pdf_path = Path("../data/marketing_slide/FlublokOnePage.pdf")
    
    print(f"Processing: {pdf_path.name}")
    
    # Convert to images
    images = convert_from_path(str(pdf_path), dpi=400)
    
    # Run detection
    detector = LayoutDetectionPipeline()
    layouts = detector.detect_images(images)
    
    # Show results
    for page_idx, layout in enumerate(layouts):
        print(f"\nPage {page_idx + 1}: {len(layout)} boxes")
        for i, box in enumerate(layout):
            print(f"  {i+1}. {box.type}: ({box.block.x_1:.0f},{box.block.y_1:.0f})-({box.block.x_2:.0f},{box.block.y_2:.0f}) [{box.score:.2f}]")
        
        # Visualize
        blocks = [
            Block(
                id=str(i),
                page_index=page_idx,
                role=str(box.type),
                bbox=(box.block.x_1, box.block.y_1, box.block.x_2, box.block.y_2),
                metadata={"score": float(box.score)}
            )
            for i, box in enumerate(layout)
        ]
        
        visualize_page_layout(
            images[page_idx],
            blocks,
            reading_order=None,
            title=f"Flublok Layout - Page {page_idx + 1}",
            save_path=f"../flublok_layout_p{page_idx+1}.png"
        )

if __name__ == "__main__":
    main()