#!/usr/bin/env python3
"""Analyze overlapping regions in the marketing detection."""

from pathlib import Path
from pdf2image import convert_from_path
import layoutparser as lp
import matplotlib.pyplot as plt
import matplotlib.patches as patches


def analyze_overlaps():
    pdf_path = Path("data/marketing_slide/FlublokOnePage.pdf")
    images = convert_from_path(str(pdf_path), dpi=400)
    image = images[0]
    
    # Run detection
    model = lp.Detectron2LayoutModel(
        "lp://PrimaLayout/mask_rcnn_R_50_FPN_3x/config",
        extra_config=[
            "MODEL.ROI_HEADS.SCORE_THRESH_TEST", 0.15,
            "MODEL.ROI_HEADS.NMS_THRESH_TEST", 0.4,
        ],
        label_map={
            1: "TextRegion",
            2: "ImageRegion", 
            3: "TableRegion",
            4: "MathsRegion",
            5: "SeparatorRegion",
            6: "OtherRegion"
        }
    )
    
    layout = model.detect(image)
    
    # Find text regions in the bottom area (disclaimer/claims area)
    bottom_y_threshold = image.height * 0.7  # Bottom 30% of page
    
    bottom_texts = []
    all_texts = []
    
    for i, elem in enumerate(layout):
        if str(elem.type) == "TextRegion":
            all_texts.append((i, elem))
            if elem.block.y_1 > bottom_y_threshold:
                bottom_texts.append((i, elem))
    
    print(f"Total TextRegions: {len(all_texts)}")
    print(f"TextRegions in bottom area: {len(bottom_texts)}")
    print("\nBottom area text regions:")
    
    for idx, elem in bottom_texts:
        bbox = elem.block
        print(f"  Region {idx+1}: ({bbox.x_1:.0f},{bbox.y_1:.0f})-({bbox.x_2:.0f},{bbox.y_2:.0f}) score={elem.score:.2f}")
    
    # Check for overlaps
    print("\n\nChecking for overlapping regions...")
    overlaps = []
    
    for i, (idx1, elem1) in enumerate(all_texts):
        for j, (idx2, elem2) in enumerate(all_texts[i+1:], i+1):
            # Calculate overlap
            x_overlap = min(elem1.block.x_2, elem2.block.x_2) - max(elem1.block.x_1, elem2.block.x_1)
            y_overlap = min(elem1.block.y_2, elem2.block.y_2) - max(elem1.block.y_1, elem2.block.y_1)
            
            if x_overlap > 0 and y_overlap > 0:
                # Calculate overlap area
                overlap_area = x_overlap * y_overlap
                area1 = (elem1.block.x_2 - elem1.block.x_1) * (elem1.block.y_2 - elem1.block.y_1)
                area2 = (elem2.block.x_2 - elem2.block.x_1) * (elem2.block.y_2 - elem2.block.y_1)
                
                overlap_pct1 = overlap_area / area1 * 100
                overlap_pct2 = overlap_area / area2 * 100
                
                if overlap_pct1 > 10 or overlap_pct2 > 10:  # Significant overlap
                    overlaps.append({
                        'indices': (idx1, idx2),
                        'overlap_pct': max(overlap_pct1, overlap_pct2)
                    })
    
    print(f"\nFound {len(overlaps)} significant overlaps")
    for overlap in overlaps[:5]:  # Show first 5
        idx1, idx2 = overlap['indices']
        print(f"  Regions {idx1+1} and {idx2+1}: {overlap['overlap_pct']:.1f}% overlap")
    
    # Visualize just the bottom area
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 8))
    
    # Full image
    ax1.imshow(image)
    ax1.set_title("Full Detection")
    ax1.axis('off')
    
    for i, elem in enumerate(layout):
        if str(elem.type) == "TextRegion":
            rect = patches.Rectangle(
                (elem.block.x_1, elem.block.y_1),
                elem.block.x_2 - elem.block.x_1,
                elem.block.y_2 - elem.block.y_1,
                linewidth=1,
                edgecolor='blue',
                facecolor='none',
                alpha=0.5
            )
            ax1.add_patch(rect)
    
    # Zoomed bottom area
    ax2.imshow(image)
    ax2.set_xlim(0, image.width)
    ax2.set_ylim(image.height, bottom_y_threshold)
    ax2.set_title("Bottom Area (Claims/Disclaimers)")
    
    for idx, elem in bottom_texts:
        rect = patches.Rectangle(
            (elem.block.x_1, elem.block.y_1),
            elem.block.x_2 - elem.block.x_1,
            elem.block.y_2 - elem.block.y_1,
            linewidth=2,
            edgecolor='red',
            facecolor='none',
            alpha=0.7
        )
        ax2.add_patch(rect)
        
        # Add label
        ax2.text(
            elem.block.x_1,
            elem.block.y_1 - 10,
            f"{idx+1}",
            color='red',
            fontsize=12,
            fontweight='bold'
        )
    
    plt.tight_layout()
    plt.savefig("marketing_overlap_analysis.png", dpi=150, bbox_inches='tight')
    plt.close()
    
    print("\nAnalysis saved to: marketing_overlap_analysis.png")
    
    # Recommendation
    print("\n\nRECOMMENDATIONS:")
    print("1. The overlapping boxes need post-processing (overlap resolution)")
    print("2. The three claims could be either:")
    print("   - Three separate blocks (if you want individual claims)")
    print("   - One merged block (if you want the disclaimer section as a unit)")
    print("3. Consider using the overlap_resolver from your existing pipeline")


if __name__ == "__main__":
    analyze_overlaps()