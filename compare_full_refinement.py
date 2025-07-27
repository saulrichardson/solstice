#!/usr/bin/env python3
"""Compare full PDF layout detection before and after refinement"""

import json
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import ConnectionPatch
from pdf2image import convert_from_path
import numpy as np
from src.injestion.pipeline import ingest_pdf
from src.injestion.layout_pipeline import LayoutDetectionPipeline

# Color schemes
RAW_COLORS = {
    "Text": "#FF6B6B",      # Red
    "Title": "#4ECDC4",     # Teal
    "List": "#45B7D1",      # Light Blue
    "Table": "#FFA07A",     # Light Salmon
    "Figure": "#DDA0DD",    # Plum
}

REFINED_COLORS = {
    "Text": "#2ECC71",      # Green
    "Title": "#E74C3C",     # Darker Red
    "List": "#3498DB",      # Blue
    "Table": "#F39C12",     # Orange
    "Figure": "#9B59B6",    # Purple
}

def process_and_compare(pdf_path: Path, page_num: int = 1):
    """Process a page and return both raw and refined results"""
    
    print(f"Processing page {page_num} of {pdf_path.name}...")
    
    # Get raw detections
    pipeline = LayoutDetectionPipeline()
    raw_layouts = pipeline.process_pdf(pdf_path)
    
    # Get refined detections
    print("Running LLM refinement...")
    refined_pages = ingest_pdf(pdf_path)
    
    # Convert page to image
    images = convert_from_path(pdf_path, first_page=page_num, last_page=page_num)
    page_image = images[0]
    
    # Extract data for the specific page
    raw_layout = raw_layouts[page_num - 1]
    refined_page = refined_pages[page_num - 1]
    
    return {
        "image": page_image,
        "raw": raw_layout,
        "refined": refined_page,
        "page_num": page_num
    }

def create_detailed_comparison(data, output_path="detailed_refinement_comparison.png"):
    """Create a detailed side-by-side comparison with annotations"""
    
    fig = plt.figure(figsize=(24, 16))
    
    # Create grid layout
    gs = fig.add_gridspec(3, 3, height_ratios=[10, 1, 1], width_ratios=[1, 1, 0.3])
    
    # Main comparison plots
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    
    # Statistics
    ax_stats = fig.add_subplot(gs[0, 2])
    
    # Legends
    ax_legend1 = fig.add_subplot(gs[1, :])
    ax_legend2 = fig.add_subplot(gs[2, :])
    
    page_image = np.array(data["image"])
    
    # Plot raw detection
    ax1.imshow(page_image)
    ax1.set_title(f"Raw Detection ({len(data['raw'])} elements)", fontsize=18, pad=20, fontweight='bold')
    
    raw_counts = {}
    for i, elem in enumerate(data['raw']):
        elem_type = str(elem.type) if elem.type else "Unknown"
        bbox = elem.block
        
        # Count types
        raw_counts[elem_type] = raw_counts.get(elem_type, 0) + 1
        
        # Draw bounding box
        rect = patches.Rectangle(
            (bbox.x_1, bbox.y_1),
            bbox.x_2 - bbox.x_1,
            bbox.y_2 - bbox.y_1,
            linewidth=2,
            edgecolor=RAW_COLORS.get(elem_type, '#888888'),
            facecolor='none',
            alpha=0.7
        )
        ax1.add_patch(rect)
        
        # Add number label
        ax1.text(bbox.x_1 + 5, bbox.y_1 + 20, str(i+1), 
                color='white', fontsize=10, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.3', facecolor=RAW_COLORS.get(elem_type, '#888888'), alpha=0.8))
    
    # Plot refined detection
    ax2.imshow(page_image)
    ax2.set_title(f"LLM Refined ({len(data['refined'].boxes)} elements)", fontsize=18, pad=20, fontweight='bold')
    
    refined_counts = {}
    for i, box in enumerate(data['refined'].boxes):
        bbox = box.bbox
        elem_type = box.label
        
        # Count types
        refined_counts[elem_type] = refined_counts.get(elem_type, 0) + 1
        
        # Draw bounding box
        rect = patches.Rectangle(
            (bbox[0], bbox[1]),
            bbox[2] - bbox[0],
            bbox[3] - bbox[1],
            linewidth=3,
            edgecolor=REFINED_COLORS.get(elem_type, '#888888'),
            facecolor='none',
            alpha=0.8
        )
        ax2.add_patch(rect)
        
        # Add reading order number
        reading_order_idx = data['refined'].reading_order.index(box.id) + 1 if box.id in data['refined'].reading_order else 0
        ax2.text(bbox[0] + 5, bbox[1] + 20, str(reading_order_idx), 
                color='white', fontsize=12, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.3', facecolor=REFINED_COLORS.get(elem_type, '#888888'), alpha=0.9))
    
    # Remove axes
    for ax in [ax1, ax2]:
        ax.set_xticks([])
        ax.set_yticks([])
    
    # Add statistics panel
    ax_stats.axis('off')
    stats_text = f"**Refinement Statistics**\n\n"
    stats_text += f"Total Elements:\n  Raw: {len(data['raw'])}\n  Refined: {len(data['refined'].boxes)}\n"
    stats_text += f"  Reduction: {len(data['raw']) - len(data['refined'].boxes)} ({(1 - len(data['refined'].boxes)/len(data['raw']))*100:.1f}%)\n\n"
    
    stats_text += "Element Types:\n"
    all_types = set(list(raw_counts.keys()) + list(refined_counts.keys()))
    for elem_type in sorted(all_types):
        raw_count = raw_counts.get(elem_type, 0)
        refined_count = refined_counts.get(elem_type, 0)
        stats_text += f"  {elem_type}:\n"
        stats_text += f"    Raw: {raw_count}\n"
        stats_text += f"    Refined: {refined_count}\n"
    
    stats_text += f"\nReading Order:\n  {'✓ Established' if data['refined'].reading_order else '✗ Not set'}"
    
    ax_stats.text(0.1, 0.9, stats_text, transform=ax_stats.transAxes,
                 fontsize=12, verticalalignment='top', fontfamily='monospace',
                 bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgray', alpha=0.8))
    
    # Add legends
    ax_legend1.axis('off')
    ax_legend2.axis('off')
    
    # Raw legend
    legend_items = []
    for elem_type, color in RAW_COLORS.items():
        legend_items.append(patches.Patch(color=color, label=elem_type))
    legend1 = ax_legend1.legend(handles=legend_items, loc='center', ncol=len(RAW_COLORS),
                               title="Raw Detection Colors", fontsize=12, title_fontsize=14)
    
    # Refined legend  
    legend_items = []
    for elem_type, color in REFINED_COLORS.items():
        legend_items.append(patches.Patch(color=color, label=elem_type))
    legend2 = ax_legend2.legend(handles=legend_items, loc='center', ncol=len(REFINED_COLORS),
                               title="Refined Detection Colors (numbers show reading order)", 
                               fontsize=12, title_fontsize=14)
    
    plt.suptitle(f"Layout Detection Refinement - Page {data['page_num']}", fontsize=22, y=0.98)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Detailed comparison saved to {output_path}")

def create_animation_frames(data, output_dir="refinement_frames"):
    """Create frames showing the refinement process step by step"""
    
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    page_image = np.array(data["image"])
    
    # Frame 1: Original image
    fig, ax = plt.subplots(figsize=(10, 14))
    ax.imshow(page_image)
    ax.set_title("Original PDF Page", fontsize=16)
    ax.axis('off')
    plt.tight_layout()
    plt.savefig(output_dir / "frame_1_original.png", dpi=150, bbox_inches='tight')
    plt.close()
    
    # Frame 2: Raw detection
    fig, ax = plt.subplots(figsize=(10, 14))
    ax.imshow(page_image)
    
    for elem in data['raw']:
        bbox = elem.block
        elem_type = str(elem.type) if elem.type else "Unknown"
        rect = patches.Rectangle(
            (bbox.x_1, bbox.y_1),
            bbox.x_2 - bbox.x_1,
            bbox.y_2 - bbox.y_1,
            linewidth=2,
            edgecolor=RAW_COLORS.get(elem_type, '#888888'),
            facecolor='none',
            alpha=0.7
        )
        ax.add_patch(rect)
    
    ax.set_title(f"Raw Detection: {len(data['raw'])} elements", fontsize=16)
    ax.axis('off')
    plt.tight_layout()
    plt.savefig(output_dir / "frame_2_raw.png", dpi=150, bbox_inches='tight')
    plt.close()
    
    # Frame 3: Refined detection
    fig, ax = plt.subplots(figsize=(10, 14))
    ax.imshow(page_image)
    
    for i, box in enumerate(data['refined'].boxes):
        bbox = box.bbox
        elem_type = box.label
        rect = patches.Rectangle(
            (bbox[0], bbox[1]),
            bbox[2] - bbox[0],
            bbox[3] - bbox[1],
            linewidth=3,
            edgecolor=REFINED_COLORS.get(elem_type, '#888888'),
            facecolor='none',
            alpha=0.8
        )
        ax.add_patch(rect)
        
        # Add reading order
        reading_order_idx = data['refined'].reading_order.index(box.id) + 1 if box.id in data['refined'].reading_order else 0
        ax.text(bbox[0] + 5, bbox[1] + 20, str(reading_order_idx), 
                color='white', fontsize=12, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.3', facecolor=REFINED_COLORS.get(elem_type, '#888888'), alpha=0.9))
    
    ax.set_title(f"LLM Refined: {len(data['refined'].boxes)} elements with reading order", fontsize=16)
    ax.axis('off')
    plt.tight_layout()
    plt.savefig(output_dir / "frame_3_refined.png", dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Animation frames saved to {output_dir}/")

def save_comparison_data(data, output_path="refinement_comparison_data.json"):
    """Save the comparison data for further analysis"""
    
    comparison = {
        "page_num": data["page_num"],
        "raw": {
            "count": len(data["raw"]),
            "elements": [
                {
                    "type": str(elem.type) if elem.type else "Unknown",
                    "bbox": [elem.block.x_1, elem.block.y_1, elem.block.x_2, elem.block.y_2],
                    "score": float(elem.score) if elem.score else 0.0
                }
                for elem in data["raw"]
            ]
        },
        "refined": {
            "count": len(data["refined"].boxes),
            "elements": [
                {
                    "id": box.id,
                    "type": box.label,
                    "bbox": list(box.bbox),
                    "score": float(box.score) if box.score else 1.0
                }
                for box in data["refined"].boxes
            ],
            "reading_order": data["refined"].reading_order
        },
        "improvements": {
            "element_reduction": len(data["raw"]) - len(data["refined"].boxes),
            "reduction_percentage": (1 - len(data["refined"].boxes) / len(data["raw"])) * 100,
            "has_reading_order": bool(data["refined"].reading_order)
        }
    }
    
    with open(output_path, 'w') as f:
        json.dump(comparison, f, indent=2)
    
    print(f"Comparison data saved to {output_path}")

def main():
    pdf_path = Path("Liu et al. (2024).pdf")
    
    # Process first page (or specify different page)
    data = process_and_compare(pdf_path, page_num=1)
    
    # Create visualizations
    create_detailed_comparison(data)
    create_animation_frames(data)
    save_comparison_data(data)
    
    print("\nRefinement complete! Check the generated files:")
    print("- detailed_refinement_comparison.png: Side-by-side comparison")
    print("- refinement_frames/: Step-by-step animation frames")
    print("- refinement_comparison_data.json: Raw data for analysis")

if __name__ == "__main__":
    main()