#!/usr/bin/env python3
"""Test the advanced merging with cross-type conflict resolution."""

import json
import uuid
from pathlib import Path
from pdf2image import convert_from_path
from src.injestion.layout_pipeline import LayoutDetectionPipeline
from src.injestion.agent.refine_layout import Box
from src.injestion.agent.refine_layout_simple import refine_page_layout_simple
from src.injestion.agent.merge_boxes_advanced import analyze_cross_type_overlaps
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Rectangle
import numpy as np


def visualize_conflict_resolution(image, original_boxes, simple_merged, resolved_boxes, output_path):
    """Create a 3-panel visualization showing the conflict resolution process."""
    
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(24, 8))
    
    # Color map for different types
    color_map = {
        'Text': 'blue',
        'Title': 'red', 
        'List': 'green',
        'Table': 'purple',
        'Figure': 'orange'
    }
    
    # Panel 1: Original
    ax1.imshow(image)
    ax1.set_title(f'1. Original Detection\n({len(original_boxes)} boxes)', fontsize=12)
    ax1.axis('off')
    
    for box in original_boxes:
        draw_box(ax1, box, color_map)
    
    # Panel 2: After simple merging (showing conflicts)
    ax2.imshow(image)
    ax2.set_title(f'2. After Same-Type Merging\n({len(simple_merged)} boxes)', fontsize=12)
    ax2.axis('off')
    
    # Draw boxes and highlight conflicts
    overlaps = analyze_cross_type_overlaps(simple_merged)
    overlap_pairs = {(o['box1_id'], o['box2_id']) for o in overlaps}
    
    for box in simple_merged:
        draw_box(ax2, box, color_map)
        
        # Highlight boxes involved in conflicts
        box_in_conflict = any(box.id in pair for pair in overlap_pairs)
        if box_in_conflict:
            x1, y1, x2, y2 = box.bbox
            rect = Rectangle((x1, y1), x2-x1, y2-y1,
                           linewidth=3, edgecolor='red',
                           facecolor='none', alpha=1.0, linestyle='--')
            ax2.add_patch(rect)
    
    # Add conflict annotations
    if overlaps:
        ax2.text(0.5, 0.02, f'{len(overlaps)} cross-type conflicts detected!',
                transform=ax2.transAxes, color='red', weight='bold',
                ha='center', bbox=dict(boxstyle="round,pad=0.3", facecolor='yellow'))
    
    # Panel 3: After conflict resolution
    ax3.imshow(image)
    ax3.set_title(f'3. After Conflict Resolution\n({len(resolved_boxes)} boxes)', fontsize=12)
    ax3.axis('off')
    
    for box in resolved_boxes:
        draw_box(ax3, box, color_map)
    
    final_overlaps = analyze_cross_type_overlaps(resolved_boxes)
    if not final_overlaps:
        ax3.text(0.5, 0.02, 'All conflicts resolved!',
                transform=ax3.transAxes, color='green', weight='bold',
                ha='center', bbox=dict(boxstyle="round,pad=0.3", facecolor='lightgreen'))
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()


def draw_box(ax, box, color_map):
    """Helper to draw a box with label."""
    x1, y1, x2, y2 = box.bbox
    width = x2 - x1
    height = y2 - y1
    color = color_map.get(box.label, 'gray')
    
    rect = Rectangle((x1, y1), width, height,
                    linewidth=2, edgecolor=color,
                    facecolor='none', alpha=0.7)
    ax.add_patch(rect)
    
    # Add label
    ax.text(x1, y1-5, f"{box.label}",
            fontsize=8, color=color, weight='bold',
            bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.7))


def test_conflict_resolution():
    """Test different conflict resolution strategies."""
    
    pdf_path = Path("Liu et al. (2024).pdf")
    if not pdf_path.exists():
        print(f"Error: {pdf_path} not found")
        return
    
    print("Testing conflict resolution strategies...")
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
    
    print(f"Original boxes: {len(original_boxes)}")
    
    # First, get simple merged boxes to see the problem
    simple_result = refine_page_layout_simple(
        page_index=0,
        raw_boxes=original_boxes,
        merge_strategy="simple",
        overlap_threshold=0.5,
        resolve_conflicts=False  # Disable conflict resolution
    )
    
    # Analyze conflicts
    conflicts = analyze_cross_type_overlaps(simple_result.boxes)
    print(f"\nAfter simple merging: {len(simple_result.boxes)} boxes")
    print(f"Cross-type conflicts: {len(conflicts)}")
    
    if conflicts:
        print("\nConflict details:")
        for i, conflict in enumerate(conflicts[:3]):  # Show top 3
            print(f"  {i+1}. {conflict['box1_label']} vs {conflict['box2_label']}: "
                  f"{conflict['overlap_pct_box2']:.1%} of {conflict['box2_label']} covered")
    
    # Test different resolution strategies
    strategies = ["priority", "larger", "confident", "split"]
    results = {}
    
    print("\n" + "="*60)
    print("Testing resolution strategies:")
    print("="*60)
    
    for strategy in strategies:
        print(f"\nStrategy: {strategy}")
        
        refined = refine_page_layout_simple(
            page_index=0,
            raw_boxes=original_boxes,
            merge_strategy="simple",
            overlap_threshold=0.5,
            resolve_conflicts=True,
            conflict_resolution=strategy
        )
        
        final_conflicts = analyze_cross_type_overlaps(refined.boxes)
        
        print(f"  Final boxes: {len(refined.boxes)}")
        print(f"  Remaining conflicts: {len(final_conflicts)}")
        
        # Count by type
        type_counts = {}
        for box in refined.boxes:
            type_counts[box.label] = type_counts.get(box.label, 0) + 1
        print(f"  Types: {dict(sorted(type_counts.items()))}")
        
        results[strategy] = refined
    
    # Create visualizations
    output_dir = Path("conflict_resolution_results")
    output_dir.mkdir(exist_ok=True)
    
    # Use priority strategy for main visualization
    best_strategy = "priority"
    best_result = results[best_strategy]
    
    visualize_conflict_resolution(
        page_image,
        original_boxes,
        simple_result.boxes,
        best_result.boxes,
        output_dir / "conflict_resolution_process.png"
    )
    
    # Save detailed results
    analysis = {
        "original_boxes": len(original_boxes),
        "simple_merge_boxes": len(simple_result.boxes),
        "conflicts_after_merge": len(conflicts),
        "resolution_results": {
            strategy: {
                "final_boxes": len(result.boxes),
                "remaining_conflicts": len(analyze_cross_type_overlaps(result.boxes)),
                "type_distribution": {
                    label: sum(1 for b in result.boxes if b.label == label)
                    for label in set(b.label for b in result.boxes)
                }
            }
            for strategy, result in results.items()
        },
        "conflict_examples": [
            {
                "type1": c['box1_label'],
                "type2": c['box2_label'],
                "overlap_area": c['overlap_area'],
                "overlap_pct_box2": c['overlap_pct_box2']
            }
            for c in conflicts[:5]
        ]
    }
    
    with open(output_dir / "conflict_analysis.json", "w") as f:
        json.dump(analysis, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"Results saved to {output_dir}/")
    print("\nRecommendation: Use 'priority' strategy for most documents.")
    print("This preserves important elements (Title, Table, Figure) over Text/List.")


if __name__ == "__main__":
    test_conflict_resolution()