#!/usr/bin/env python3
"""Test layout detection with different parameter tunings"""

import sys
import os
from pathlib import Path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import layoutparser as lp
from pdf2image import convert_from_path
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def test_with_params(image, score_threshold, nms_threshold, test_name):
    """Test detection with specific parameters"""
    
    print(f"\n{test_name}")
    print(f"  Score threshold: {score_threshold}")
    print(f"  NMS threshold: {nms_threshold}")
    
    # Initialize model with custom parameters
    model = lp.Detectron2LayoutModel(
        "lp://PubLayNet/mask_rcnn_R_50_FPN_3x/config",
        extra_config=[
            "MODEL.ROI_HEADS.SCORE_THRESH_TEST", score_threshold,
            "MODEL.ROI_HEADS.NMS_THRESH_TEST", nms_threshold,
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
    layout = model.detect(image)
    
    # Analyze results
    print(f"  Detected {len(layout)} boxes:")
    by_type = {}
    for box in layout:
        by_type.setdefault(str(box.type), []).append(box)
    
    for box_type, boxes in sorted(by_type.items()):
        print(f"    - {box_type}: {len(boxes)} boxes")
    
    # Create visualization
    fig, ax = plt.subplots(1, 1, figsize=(10, 14))
    ax.imshow(image)
    
    colors = {
        "Text": "blue",
        "Title": "red", 
        "List": "green",
        "Table": "orange",
        "Figure": "purple"
    }
    
    for i, box in enumerate(layout):
        rect = patches.Rectangle(
            (box.block.x_1, box.block.y_1),
            box.block.x_2 - box.block.x_1,
            box.block.y_2 - box.block.y_1,
            linewidth=2,
            edgecolor=colors.get(str(box.type), "black"),
            facecolor='none',
            alpha=0.8
        )
        ax.add_patch(rect)
        
        # Add box number for reference
        ax.text(
            box.block.x_1 + 5,
            box.block.y_1 + 20,
            f"{i+1}",
            color="white",
            fontsize=10,
            bbox=dict(boxstyle="round,pad=0.3", facecolor=colors.get(str(box.type), "black"), alpha=0.8)
        )
    
    ax.set_xlim(0, image.width)
    ax.set_ylim(image.height, 0)
    ax.axis('off')
    plt.title(f"{test_name} - {len(layout)} boxes")
    plt.tight_layout()
    
    # Save with descriptive filename
    output_path = f"flublok_test_{test_name.lower().replace(' ', '_')}.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"  Visualization saved to: {output_path}")
    
    return layout

def main():
    pdf_path = Path("/Users/saul/projects/solstice/solstice/data/marketing_slide/FlublokOnePage.pdf")
    
    print(f"Testing different parameters on: {pdf_path.name}")
    print("=" * 60)
    
    # Convert PDF to image
    images = convert_from_path(str(pdf_path), dpi=400)
    image = images[0]
    
    # Test different parameter combinations
    test_configs = [
        # (score_threshold, nms_threshold, test_name)
        (0.2, 0.5, "Original Settings"),      # Your current settings
        (0.1, 0.3, "Lower Thresholds"),       # More sensitive
        (0.05, 0.2, "Very Low Thresholds"),   # Very sensitive
        (0.3, 0.7, "Higher Thresholds"),      # Less sensitive
        (0.15, 0.4, "Balanced Low"),          # Compromise
    ]
    
    all_results = []
    for score_thresh, nms_thresh, name in test_configs:
        layout = test_with_params(image, score_thresh, nms_thresh, name)
        all_results.append((name, layout))
    
    # Compare text detection specifically
    print("\n" + "="*60)
    print("TEXT DETECTION COMPARISON:")
    print("="*60)
    
    for name, layout in all_results:
        text_boxes = [box for box in layout if str(box.type) == "Text"]
        print(f"\n{name}: {len(text_boxes)} text boxes")
        
        # Show first few text box locations
        for i, box in enumerate(text_boxes[:5]):
            coords = f"({box.block.x_1:.0f},{box.block.y_1:.0f})-({box.block.x_2:.0f},{box.block.y_2:.0f})"
            print(f"  Box {i+1}: {coords} [score: {box.score:.2f}]")
        
        if len(text_boxes) > 5:
            print(f"  ... and {len(text_boxes) - 5} more")

if __name__ == "__main__":
    main()