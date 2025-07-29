#!/usr/bin/env python3
"""Direct test of marketing module bypassing injestion __init__.py"""

import sys
from pathlib import Path
sys.path.insert(0, "src")

# Direct imports to avoid __init__.py
from pdf2image import convert_from_path
from injestion.marketing.detector import MarketingLayoutDetector


def main():
    pdf_path = Path("data/marketing_slide/FlublokOnePage.pdf")
    
    print("Testing Marketing Module - Direct Import")
    print("=" * 60)
    print(f"PDF: {pdf_path.name}")
    
    # Convert PDF to images
    print("\nConverting PDF to images...")
    images = convert_from_path(str(pdf_path), dpi=400)
    print(f"  Generated {len(images)} page(s)")
    
    # Test marketing detector
    print("\nTesting MarketingLayoutDetector (PrimaLayout)...")
    detector = MarketingLayoutDetector()
    
    # Show configuration
    print(f"  Score threshold: {detector._score_threshold}")
    print(f"  NMS threshold: {detector._nms_threshold}")
    print(f"  Max detections: {detector._max_detections}")
    
    # Run detection
    print("\nRunning detection...")
    layouts = detector.detect_images(images)
    
    # Analyze results
    for page_idx, layout in enumerate(layouts):
        print(f"\nPage {page_idx + 1} Results:")
        print(f"  Total detections: {len(layout)}")
        
        # Group by type
        by_type = {}
        for elem in layout:
            elem_type = str(elem.type)
            by_type[elem_type] = by_type.get(elem_type, 0) + 1
        
        print("  By type:")
        for elem_type, count in sorted(by_type.items()):
            print(f"    {elem_type}: {count}")
        
        # Show some sample detections
        print("\n  Sample detections:")
        for i, elem in enumerate(layout[:5]):
            bbox = elem.block
            print(f"    {i+1}. {elem.type} at ({bbox.x_1:.0f},{bbox.y_1:.0f})-({bbox.x_2:.0f},{bbox.y_2:.0f}) [score: {elem.score:.2f}]")
        
        if len(layout) > 5:
            print(f"    ... and {len(layout) - 5} more")
    
    # Compare with PubLayNet
    print("\n\nComparison with PubLayNet:")
    print("-" * 40)
    print("PubLayNet (previous): ~6 Text regions")
    print(f"PrimaLayout (current): {by_type.get('TextRegion', 0)} TextRegions")
    print("\nPrimaLayout captures much more text content!")
    
    # Create simple visualization
    try:
        import matplotlib.pyplot as plt
        import matplotlib.patches as patches
        
        fig, ax = plt.subplots(1, 1, figsize=(10, 14))
        ax.imshow(images[0])
        
        # Color map for PrimaLayout types
        colors = {
            "TextRegion": "blue",
            "ImageRegion": "green",
            "TableRegion": "orange",
            "SeparatorRegion": "red",
            "OtherRegion": "purple"
        }
        
        for elem in layouts[0]:
            rect = patches.Rectangle(
                (elem.block.x_1, elem.block.y_1),
                elem.block.x_2 - elem.block.x_1,
                elem.block.y_2 - elem.block.y_1,
                linewidth=2,
                edgecolor=colors.get(str(elem.type), "black"),
                facecolor='none',
                alpha=0.8
            )
            ax.add_patch(rect)
        
        ax.set_xlim(0, images[0].width)
        ax.set_ylim(images[0].height, 0)
        ax.axis('off')
        plt.title(f"Marketing Module Detection - {len(layouts[0])} regions")
        plt.tight_layout()
        
        output_path = "marketing_module_test.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"\nVisualization saved to: {output_path}")
        
    except Exception as e:
        print(f"\nCould not create visualization: {e}")


if __name__ == "__main__":
    main()