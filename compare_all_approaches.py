#!/usr/bin/env python3
"""Compare all approaches on the same page to see differences."""

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


def visualize_all_approaches(image, original_boxes, results_dict, output_path):
    """Create a comprehensive visualization of all approaches."""
    
    n_approaches = len(results_dict) + 1  # +1 for original
    fig, axes = plt.subplots(1, n_approaches, figsize=(6*n_approaches, 10))
    
    if n_approaches == 2:
        axes = [axes]
    
    # Color map for different types
    color_map = {
        'Text': 'blue',
        'Title': 'red', 
        'List': 'green',
        'Table': 'purple',
        'Figure': 'orange'
    }
    
    # Panel 1: Original
    ax = axes[0]
    ax.imshow(image)
    ax.set_title(f'Original\n({len(original_boxes)} boxes)', fontsize=12, weight='bold')
    ax.axis('off')
    
    for box in original_boxes:
        draw_box(ax, box, color_map)
    
    # Remaining panels: Different approaches
    for idx, (name, boxes) in enumerate(results_dict.items()):
        ax = axes[idx + 1]
        ax.imshow(image)
        
        # Count conflicts
        conflicts = analyze_cross_type_overlaps(boxes)
        conflict_text = f"\n{len(conflicts)} conflicts" if conflicts else "\nNo conflicts"
        
        ax.set_title(f'{name}\n({len(boxes)} boxes){conflict_text}', 
                     fontsize=12, weight='bold')
        ax.axis('off')
        
        for box in boxes:
            draw_box(ax, box, color_map)
            
        # Highlight conflicts if any
        if conflicts:
            for conf in conflicts:
                # Find boxes involved
                for box in boxes:
                    if box.id == conf['box1_id'] or box.id == conf['box2_id']:
                        x1, y1, x2, y2 = box.bbox
                        rect = Rectangle((x1, y1), x2-x1, y2-y1,
                                       linewidth=3, edgecolor='red',
                                       facecolor='none', alpha=1.0, linestyle='--')
                        ax.add_patch(rect)
    
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
    
    # Compact label
    ax.text(x1, y1-5, box.label[0],  # Just first letter
            fontsize=10, color=color, weight='bold',
            bbox=dict(boxstyle="round,pad=0.2", facecolor='white', alpha=0.8))


def compare_approaches():
    """Compare all merging approaches on the same page."""
    
    pdf_path = Path("Liu et al. (2024).pdf")
    if not pdf_path.exists():
        print(f"Error: {pdf_path} not found")
        return
    
    print("Comparing all approaches on the same page...")
    print("="*70)
    
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
    
    print(f"\nOriginal: {len(original_boxes)} boxes")
    
    # Test different approaches
    approaches = {
        "1. No Merging": {
            "merge": False,
            "resolve": False
        },
        "2. Simple Merge": {
            "merge": True,
            "resolve": False
        },
        "3. Merge + Priority": {
            "merge": True,
            "resolve": True,
            "strategy": "priority"
        },
        "4. Merge + Weighted": {
            "merge": True,
            "resolve": True,
            "strategy": "weighted"
        }
    }
    
    results = {}
    
    for name, config in approaches.items():
        if not config["merge"]:
            # No merging
            result_boxes = original_boxes
        else:
            # Apply merging/resolution
            refined = refine_page_layout_simple(
                page_index=0,
                raw_boxes=original_boxes,
                merge_strategy="simple",
                overlap_threshold=0.5,
                resolve_conflicts=config["resolve"],
                conflict_resolution=config.get("strategy", "priority")
            )
            result_boxes = refined.boxes
        
        # Analyze
        conflicts = analyze_cross_type_overlaps(result_boxes)
        
        print(f"\n{name}:")
        print(f"  Boxes: {len(result_boxes)}")
        print(f"  Cross-type conflicts: {len(conflicts)}")
        
        # Count by type
        type_counts = {}
        for box in result_boxes:
            type_counts[box.label] = type_counts.get(box.label, 0) + 1
        print(f"  Types: {dict(sorted(type_counts.items()))}")
        
        results[name] = result_boxes
    
    # Create comparison visualization
    output_dir = Path("approach_comparison")
    output_dir.mkdir(exist_ok=True)
    
    visualize_all_approaches(
        page_image,
        original_boxes,
        results,
        output_dir / "all_approaches_comparison.png"
    )
    
    # Create detailed analysis
    analysis = {
        "original": {
            "total_boxes": len(original_boxes),
            "types": {label: sum(1 for b in original_boxes if b.label == label) 
                     for label in set(b.label for b in original_boxes)}
        },
        "approaches": {}
    }
    
    for name, boxes in results.items():
        conflicts = analyze_cross_type_overlaps(boxes)
        analysis["approaches"][name] = {
            "total_boxes": len(boxes),
            "types": {label: sum(1 for b in boxes if b.label == label) 
                     for label in set(b.label for b in boxes)},
            "conflicts": len(conflicts),
            "conflict_details": [
                f"{c['box1_label']} vs {c['box2_label']}" 
                for c in conflicts[:3]
            ] if conflicts else []
        }
    
    with open(output_dir / "approach_analysis.json", "w") as f:
        json.dump(analysis, f, indent=2)
    
    # Print summary
    print("\n" + "="*70)
    print("SUMMARY:")
    print("="*70)
    print("1. No Merging: Shows all original detections")
    print("2. Simple Merge: Merges same-type overlaps but creates List-Text conflict")
    print("3. Priority Resolution: List wins over Text (type hierarchy)")
    print("4. Weighted Resolution: Considers both confidence and area")
    
    print(f"\nVisualization saved to {output_dir}/all_approaches_comparison.png")


if __name__ == "__main__":
    compare_approaches()