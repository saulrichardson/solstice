#!/usr/bin/env python3
"""Test simple geometric merging of overlapping boxes."""

import json
import uuid
from pathlib import Path
from pdf2image import convert_from_path
from src.injestion.layout_pipeline import LayoutDetectionPipeline
from src.injestion.agent.refine_layout import Box
from src.injestion.agent.refine_layout_simple import refine_page_layout_simple
from src.injestion.agent.merge_boxes import calculate_iou
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Rectangle


def visualize_before_after(image, original_boxes, merged_boxes, output_path):
    """Create side-by-side visualization of original and merged boxes."""
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))
    
    # Original boxes
    ax1.imshow(image)
    ax1.set_title(f'Original Detection ({len(original_boxes)} boxes)', fontsize=14)
    ax1.axis('off')
    
    # Color map for different types
    color_map = {
        'Text': 'blue',
        'Title': 'red',
        'List': 'green',
        'Table': 'purple',
        'Figure': 'orange'
    }
    
    for box in original_boxes:
        x1, y1, x2, y2 = box.bbox
        width = x2 - x1
        height = y2 - y1
        color = color_map.get(box.label, 'gray')
        
        rect = Rectangle((x1, y1), width, height,
                        linewidth=2, edgecolor=color,
                        facecolor='none', alpha=0.7)
        ax1.add_patch(rect)
        
        # Add label
        ax1.text(x1, y1-5, f"{box.label} ({box.score:.2f})",
                fontsize=8, color=color, weight='bold',
                bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.7))
    
    # Merged boxes
    ax2.imshow(image)
    ax2.set_title(f'After Merging ({len(merged_boxes)} boxes)', fontsize=14)
    ax2.axis('off')
    
    for box in merged_boxes:
        x1, y1, x2, y2 = box.bbox
        width = x2 - x1
        height = y2 - y1
        color = color_map.get(box.label, 'gray')
        
        rect = Rectangle((x1, y1), width, height,
                        linewidth=2, edgecolor=color,
                        facecolor='none', alpha=0.7)
        ax2.add_patch(rect)
        
        # Add label
        ax2.text(x1, y1-5, f"{box.label} ({box.score:.2f})",
                fontsize=8, color=color, weight='bold',
                bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.7))
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved visualization to {output_path}")


def analyze_overlaps(boxes):
    """Analyze overlapping boxes of the same type."""
    overlaps = []
    
    for i, box1 in enumerate(boxes):
        for j, box2 in enumerate(boxes):
            if i >= j:  # Skip self and already checked pairs
                continue
                
            if box1.label == box2.label:
                iou = calculate_iou(box1.bbox, box2.bbox)
                if iou > 0:
                    overlaps.append({
                        'box1_id': box1.id,
                        'box2_id': box2.id,
                        'label': box1.label,
                        'iou': iou,
                        'box1_bbox': box1.bbox,
                        'box2_bbox': box2.bbox
                    })
    
    return sorted(overlaps, key=lambda x: x['iou'], reverse=True)


def test_simple_merging():
    """Test simple box merging on a PDF."""
    
    pdf_path = Path("Liu et al. (2024).pdf")
    if not pdf_path.exists():
        print(f"Error: {pdf_path} not found")
        return
    
    print(f"Processing {pdf_path}...")
    
    # Get raw detections
    pipeline = LayoutDetectionPipeline()
    layouts = pipeline.process_pdf(pdf_path)
    
    # Convert first page to image
    images = convert_from_path(pdf_path, first_page=1, last_page=1, dpi=200)
    page_image = images[0]
    
    # Convert layout to Box format
    page_layout = layouts[0]
    original_boxes = [
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
    
    print(f"\nOriginal boxes: {len(original_boxes)}")
    
    # Analyze overlaps
    overlaps = analyze_overlaps(original_boxes)
    print(f"\nFound {len(overlaps)} overlapping box pairs of the same type")
    
    if overlaps:
        print("\nTop 5 overlapping pairs:")
        for i, overlap in enumerate(overlaps[:5]):
            print(f"  {i+1}. {overlap['label']} boxes with IoU={overlap['iou']:.3f}")
    
    # Test different merging strategies
    print("\n" + "="*50)
    print("Testing different merging strategies:")
    print("="*50)
    
    # Strategy 1: IoU-based merging with low threshold
    print("\n1. IoU-based merging (threshold=0.1):")
    refined_iou = refine_page_layout_simple(
        page_index=0,
        raw_boxes=original_boxes,
        merge_strategy="iou",
        iou_threshold=0.1
    )
    print(f"   Merged to {len(refined_iou.boxes)} boxes")
    
    # Strategy 2: Simple overlap-based merging
    print("\n2. Simple overlap merging (threshold=0.5):")
    refined_simple = refine_page_layout_simple(
        page_index=0,
        raw_boxes=original_boxes,
        merge_strategy="simple",
        overlap_threshold=0.5
    )
    print(f"   Merged to {len(refined_simple.boxes)} boxes")
    
    # Strategy 3: Aggressive merging
    print("\n3. Aggressive merging (overlap threshold=0.3):")
    refined_aggressive = refine_page_layout_simple(
        page_index=0,
        raw_boxes=original_boxes,
        merge_strategy="simple",
        overlap_threshold=0.3
    )
    print(f"   Merged to {len(refined_aggressive.boxes)} boxes")
    
    # Count by type for best strategy
    best_refined = refined_simple
    type_counts_before = {}
    type_counts_after = {}
    
    for box in original_boxes:
        type_counts_before[box.label] = type_counts_before.get(box.label, 0) + 1
        
    for box in best_refined.boxes:
        type_counts_after[box.label] = type_counts_after.get(box.label, 0) + 1
    
    print("\n" + "="*50)
    print("Box counts by type (before → after):")
    print("="*50)
    all_types = set(type_counts_before.keys()) | set(type_counts_after.keys())
    for label in sorted(all_types):
        before = type_counts_before.get(label, 0)
        after = type_counts_after.get(label, 0)
        reduction = before - after
        print(f"{label:10} {before:3d} → {after:3d} (merged {reduction})")
    
    # Save results
    output_dir = Path("simple_merging_results")
    output_dir.mkdir(exist_ok=True)
    
    # Save JSON results
    results = {
        "original_count": len(original_boxes),
        "merged_count": len(best_refined.boxes),
        "type_counts_before": type_counts_before,
        "type_counts_after": type_counts_after,
        "overlaps_found": len(overlaps),
        "reading_order": best_refined.reading_order,
        "merged_boxes": [
            {
                "id": box.id,
                "label": box.label,
                "bbox": list(box.bbox),
                "score": box.score
            }
            for box in best_refined.boxes
        ]
    }
    
    with open(output_dir / "merging_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    # Create visualization
    visualize_before_after(
        page_image,
        original_boxes,
        best_refined.boxes,
        output_dir / "before_after_merging.png"
    )
    
    print(f"\nResults saved to {output_dir}/")
    print("\nSimple merging complete!")


if __name__ == "__main__":
    test_simple_merging()