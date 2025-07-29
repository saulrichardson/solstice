#!/usr/bin/env python3
"""Standalone test that bypasses injestion __init__.py issues"""

import sys
import os
from pathlib import Path

# Add src to path without importing injestion
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import components directly without triggering __init__.py
import layoutparser as lp
from pdf2image import convert_from_path

def test_marketing_pdf():
    pdf_path = Path("/Users/saul/projects/solstice/solstice/data/marketing_slide/FlublokOnePage.pdf")
    
    print(f"Testing layout detection on: {pdf_path.name}")
    print("-" * 50)
    
    # Convert PDF to images
    print("Converting PDF to images...")
    images = convert_from_path(str(pdf_path), dpi=400)
    print(f"  - Generated {len(images)} page images")
    
    # Initialize layout model directly
    print("\nInitializing layout detection model...")
    model = lp.Detectron2LayoutModel(
        "lp://PubLayNet/mask_rcnn_R_50_FPN_3x/config",
        extra_config=[
            "MODEL.ROI_HEADS.SCORE_THRESH_TEST", 0.2,
            "MODEL.ROI_HEADS.NMS_THRESH_TEST", 0.5,
        ],
        label_map={
            0: "Text",
            1: "Title", 
            2: "List",
            3: "Table",
            4: "Figure",
        }
    )
    
    # Run detection
    print("\nRunning layout detection...")
    layouts = [model.detect(image) for image in images]
    
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
        
        # Save visualization
        import matplotlib.pyplot as plt
        import matplotlib.patches as patches
        
        fig, ax = plt.subplots(1, 1, figsize=(10, 14))
        ax.imshow(image)
        
        # Define colors for each type
        colors = {
            "Text": "blue",
            "Title": "red", 
            "List": "green",
            "Table": "orange",
            "Figure": "purple"
        }
        
        # Draw boxes
        for box in layout:
            rect = patches.Rectangle(
                (box.block.x_1, box.block.y_1),
                box.block.x_2 - box.block.x_1,
                box.block.y_2 - box.block.y_1,
                linewidth=2,
                edgecolor=colors.get(str(box.type), "black"),
                facecolor='none'
            )
            ax.add_patch(rect)
            
            # Add label
            ax.text(
                box.block.x_1,
                box.block.y_1 - 5,
                f"{box.type}",
                color=colors.get(str(box.type), "black"),
                fontsize=8,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8)
            )
        
        ax.set_xlim(0, image.width)
        ax.set_ylim(image.height, 0)
        ax.axis('off')
        plt.title(f"Layout Detection - Page {page_idx + 1}")
        plt.tight_layout()
        
        output_path = f"flublok_standalone_layout_p{page_idx+1}.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"\n  Visualization saved to: {output_path}")

if __name__ == "__main__":
    test_marketing_pdf()