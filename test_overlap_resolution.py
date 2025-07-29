#!/usr/bin/env python3
"""Test overlap resolution in marketing pipeline"""

from pathlib import Path
from pdf2image import convert_from_path
import layoutparser as lp
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import uuid

# Simple Box class for testing
class Box:
    def __init__(self, id, bbox, label, score):
        self.id = id
        self.bbox = bbox
        self.label = label
        self.score = score

# Simple overlap check
def calculate_iou(box1, box2):
    """Calculate Intersection over Union"""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])
    
    if x2 < x1 or y2 < y1:
        return 0.0
    
    intersection = (x2 - x1) * (y2 - y1)
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union = area1 + area2 - intersection
    
    return intersection / union if union > 0 else 0


def test_overlap_resolution():
    pdf_path = Path("data/marketing_slide/FlublokOnePage.pdf")
    images = convert_from_path(str(pdf_path), dpi=400)
    image = images[0]
    
    # Run PrimaLayout detection
    model = lp.Detectron2LayoutModel(
        "lp://PrimaLayout/mask_rcnn_R_50_FPN_3x/config",
        extra_config=[
            "MODEL.ROI_HEADS.SCORE_THRESH_TEST", 0.1,
            "MODEL.ROI_HEADS.NMS_THRESH_TEST", 0.3,
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
    
    # Convert to Box objects
    boxes_before = []
    for i, elem in enumerate(layout):
        box = Box(
            id=f"box_{i}",
            bbox=(elem.block.x_1, elem.block.y_1, elem.block.x_2, elem.block.y_2),
            label=str(elem.type),
            score=float(elem.score)
        )
        boxes_before.append(box)
    
    # Apply overlap resolution
    boxes_after = no_overlap_pipeline(
        boxes=boxes_before.copy(),
        merge_same_type_first=True,
        merge_threshold=0.3  # 30% IoU threshold
    )
    
    print("Overlap Resolution Results")
    print("=" * 60)
    print(f"Boxes before: {len(boxes_before)}")
    print(f"Boxes after: {len(boxes_after)}")
    print(f"Reduction: {len(boxes_before) - len(boxes_after)} boxes merged")
    
    # Count by type
    def count_by_type(boxes):
        counts = {}
        for box in boxes:
            counts[box.label] = counts.get(box.label, 0) + 1
        return counts
    
    before_counts = count_by_type(boxes_before)
    after_counts = count_by_type(boxes_after)
    
    print("\nBy type comparison:")
    all_types = set(before_counts.keys()) | set(after_counts.keys())
    for box_type in sorted(all_types):
        before = before_counts.get(box_type, 0)
        after = after_counts.get(box_type, 0)
        print(f"  {box_type}: {before} → {after} (merged {before - after})")
    
    # Visualize before and after
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 14))
    
    # Before
    ax1.imshow(image)
    ax1.set_title(f"Before Overlap Resolution ({len(boxes_before)} boxes)")
    for box in boxes_before:
        if box.label == "TextRegion":
            rect = patches.Rectangle(
                (box.bbox[0], box.bbox[1]),
                box.bbox[2] - box.bbox[0],
                box.bbox[3] - box.bbox[1],
                linewidth=1,
                edgecolor='blue',
                facecolor='none',
                alpha=0.5
            )
            ax1.add_patch(rect)
    ax1.axis('off')
    
    # After
    ax2.imshow(image)
    ax2.set_title(f"After Overlap Resolution ({len(boxes_after)} boxes)")
    for box in boxes_after:
        if box.label == "TextRegion":
            rect = patches.Rectangle(
                (box.bbox[0], box.bbox[1]),
                box.bbox[2] - box.bbox[0],
                box.bbox[3] - box.bbox[1],
                linewidth=2,
                edgecolor='green',
                facecolor='none',
                alpha=0.7
            )
            ax2.add_patch(rect)
    ax2.axis('off')
    
    plt.tight_layout()
    plt.savefig("overlap_resolution_comparison.png", dpi=150, bbox_inches='tight')
    plt.close()
    
    print("\nVisualization saved to: overlap_resolution_comparison.png")
    
    # Check bottom area specifically
    bottom_y = image.height * 0.7
    bottom_before = [b for b in boxes_before if b.bbox[1] > bottom_y and b.label == "TextRegion"]
    bottom_after = [b for b in boxes_after if b.bbox[1] > bottom_y and b.label == "TextRegion"]
    
    print(f"\nBottom area (claims/disclaimers):")
    print(f"  TextRegions before: {len(bottom_before)}")
    print(f"  TextRegions after: {len(bottom_after)}")
    print(f"  Merged: {len(bottom_before) - len(bottom_after)} overlapping boxes")


if __name__ == "__main__":
    test_overlap_resolution()