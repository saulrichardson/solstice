#!/usr/bin/env python3
"""Test the weighted conflict resolution approach."""

import json
import uuid
from pathlib import Path
from pdf2image import convert_from_path
from src.injestion.layout_pipeline import LayoutDetectionPipeline
from src.injestion.agent.refine_layout import Box
from src.injestion.agent.refine_layout_simple import refine_page_layout_simple
from src.injestion.agent.merge_boxes_weighted import analyze_conflict_weights, calculate_box_weight
from src.injestion.agent.merge_boxes_advanced import get_box_area
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Rectangle


def visualize_weighted_analysis(image, boxes, conflicts, output_path):
    """Visualize boxes with weight information."""
    
    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    
    # Color map for different types
    color_map = {
        'Text': 'blue',
        'Title': 'red', 
        'List': 'green',
        'Table': 'purple',
        'Figure': 'orange'
    }
    
    ax.imshow(image)
    ax.set_title('Box Analysis with Weights', fontsize=14)
    ax.axis('off')
    
    # Draw all boxes with weight information
    for box in boxes:
        x1, y1, x2, y2 = box.bbox
        width = x2 - x1
        height = y2 - y1
        area = get_box_area(box.bbox)
        weight = calculate_box_weight(box)
        
        color = color_map.get(box.label, 'gray')
        
        # Draw box
        rect = Rectangle((x1, y1), width, height,
                        linewidth=2, edgecolor=color,
                        facecolor='none', alpha=0.7)
        ax.add_patch(rect)
        
        # Add detailed label
        label_text = (f"{box.label}\n"
                     f"conf: {box.score:.2f}\n"
                     f"area: {int(area)}\n"
                     f"weight: {weight:.3f}")
        
        ax.text(x1 + 5, y1 + 30, label_text,
                fontsize=8, color='white', weight='bold',
                bbox=dict(boxstyle="round,pad=0.3", facecolor=color, alpha=0.8))
    
    # Highlight conflicts
    if conflicts:
        conflict_text = "Conflicts:\n"
        for i, conf in enumerate(conflicts[:3]):
            b1 = conf['box1']
            b2 = conf['box2']
            conflict_text += (f"{i+1}. {b1['label']} (w:{b1['weight']:.2f}) vs "
                            f"{b2['label']} (w:{b2['weight']:.2f}) → {conf['winner']} wins\n")
        
        ax.text(0.02, 0.98, conflict_text,
                transform=ax.transAxes, color='black', weight='bold',
                va='top', fontsize=10,
                bbox=dict(boxstyle="round,pad=0.5", facecolor='yellow', alpha=0.8))
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()


def test_weighted_resolution():
    """Test weighted resolution on the abstract/list issue."""
    
    pdf_path = Path("Liu et al. (2024).pdf")
    if not pdf_path.exists():
        print(f"Error: {pdf_path} not found")
        return
    
    print("Testing weighted conflict resolution...")
    print("="*60)
    
    # Get raw detections
    pipeline = LayoutDetectionPipeline()
    layouts = pipeline.process_pdf(pdf_path)
    
    # Convert first page
    images = convert_from_path(pdf_path, first_page=1, last_page=1, dpi=200)
    page_image = images[0]
    
    # Convert to Box format
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
    
    # Analyze the boxes to understand the abstract/list issue
    print("\nAnalyzing boxes in abstract area...")
    abstract_area_boxes = []
    for box in original_boxes:
        # Look for boxes in the typical abstract area (top of page, wide)
        if box.bbox[1] < 800 and (box.bbox[2] - box.bbox[0]) > 1000:
            area = get_box_area(box.bbox)
            weight = calculate_box_weight(box)
            abstract_area_boxes.append((box, area, weight))
            print(f"  {box.label}: conf={box.score:.3f}, area={int(area)}, weight={weight:.3f}")
    
    # Test different approaches
    print("\n" + "="*60)
    print("Comparing resolution strategies:")
    print("="*60)
    
    strategies = [
        ("priority", "Type-based priority"),
        ("confident", "Confidence-based"),
        ("larger", "Area-based"),
        ("weighted", "Weighted (conf + area)")
    ]
    
    results = {}
    
    for strategy, description in strategies:
        print(f"\n{description} ({strategy}):")
        
        refined = refine_page_layout_simple(
            page_index=0,
            raw_boxes=original_boxes,
            merge_strategy="simple",
            overlap_threshold=0.5,
            resolve_conflicts=True,
            conflict_resolution=strategy
        )
        
        # Check what happened in the abstract area
        abstract_survivors = []
        for box in refined.boxes:
            if box.bbox[1] < 800 and (box.bbox[2] - box.bbox[0]) > 1000:
                abstract_survivors.append(box)
        
        print(f"  Total boxes: {len(refined.boxes)}")
        print(f"  Abstract area survivors: {[b.label for b in abstract_survivors]}")
        
        results[strategy] = refined
    
    # Analyze weight-based conflicts
    print("\n" + "="*60)
    print("Weight analysis of conflicts:")
    print("="*60)
    
    conflict_analysis = analyze_conflict_weights(original_boxes)
    for conf in conflict_analysis[:3]:
        b1 = conf['box1']
        b2 = conf['box2']
        print(f"\n{b1['label']} vs {b2['label']}:")
        print(f"  {b1['label']}: score={b1['score']:.3f}, area={int(b1['area'])}, weight={b1['weight']:.3f}")
        print(f"  {b2['label']}: score={b2['score']:.3f}, area={int(b2['area'])}, weight={b2['weight']:.3f}")
        print(f"  Weight ratio: {conf['weight_ratio']:.3f}")
        print(f"  Winner: {conf['winner']}")
    
    # Create visualizations
    output_dir = Path("weighted_resolution_results")
    output_dir.mkdir(exist_ok=True)
    
    # Visualize the weighted analysis
    visualize_weighted_analysis(
        page_image,
        original_boxes,
        conflict_analysis[:3],
        output_dir / "weighted_analysis.png"
    )
    
    # Save detailed results
    analysis_data = {
        "abstract_area_analysis": [
            {
                "label": box.label,
                "score": box.score,
                "area": int(area),
                "weight": float(weight),
                "bbox": list(box.bbox)
            }
            for box, area, weight in abstract_area_boxes
        ],
        "strategy_results": {
            strategy: {
                "total_boxes": len(result.boxes),
                "abstract_survivors": [b.label for b in result.boxes 
                                     if b.bbox[1] < 800 and (b.bbox[2] - b.bbox[0]) > 1000]
            }
            for strategy, result in results.items()
        },
        "weight_conflicts": [
            {
                "box1": conf['box1']['label'],
                "box2": conf['box2']['label'],
                "weights": {
                    conf['box1']['label']: conf['box1']['weight'],
                    conf['box2']['label']: conf['box2']['weight']
                },
                "winner": conf['winner'],
                "weight_ratio": conf['weight_ratio']
            }
            for conf in conflict_analysis[:5]
        ]
    }
    
    with open(output_dir / "weighted_analysis.json", "w") as f:
        json.dump(analysis_data, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"Results saved to {output_dir}/")
    print("\nKey insight: The weighted approach considers both confidence")
    print("and area, which should better handle abstract vs list conflicts.")


if __name__ == "__main__":
    test_weighted_resolution()