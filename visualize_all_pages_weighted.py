#!/usr/bin/env python3
"""Visualize weighted merge results for ALL pages of the PDF."""

import json
from pathlib import Path
from pdf2image import convert_from_path
from src.injestion.pipeline_simple import ingest_pdf_simple
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Rectangle
from matplotlib.backends.backend_pdf import PdfPages


def visualize_page(page_image, boxes, page_num, ax):
    """Visualize results for a single page on given axis."""
    
    # Color map for different types
    color_map = {
        'Text': 'blue',
        'Title': 'red', 
        'List': 'green',
        'Table': 'purple',
        'Figure': 'orange'
    }
    
    ax.imshow(page_image)
    ax.set_title(f'Page {page_num} ({len(boxes)} boxes)', fontsize=12)
    ax.axis('off')
    
    # Draw boxes
    for box in boxes:
        x1, y1, x2, y2 = box.bbox
        width = x2 - x1
        height = y2 - y1
        color = color_map.get(box.label, 'gray')
        
        rect = Rectangle((x1, y1), width, height,
                        linewidth=2, edgecolor=color,
                        facecolor='none', alpha=0.7)
        ax.add_patch(rect)
        
        # Add compact label (just first letter)
        ax.text(x1, y1-5, box.label[0],
                fontsize=8, color=color, weight='bold',
                bbox=dict(boxstyle="round,pad=0.2", facecolor='white', alpha=0.7))


def create_all_visualizations():
    """Create visualizations for all pages."""
    
    pdf_path = Path("Liu et al. (2024).pdf")
    if not pdf_path.exists():
        print(f"Error: {pdf_path} not found")
        return
    
    print("Creating visualizations for ALL pages...")
    print("="*50)
    
    # Process with weighted merge
    pages = ingest_pdf_simple(pdf_path)
    
    # Get all page images
    print("Converting PDF pages to images...")
    images = convert_from_path(pdf_path, dpi=200)
    
    # Create output directory
    output_dir = Path("all_pages_weighted_visualization")
    output_dir.mkdir(exist_ok=True)
    
    print(f"Processing {len(pages)} pages...")
    
    # Create individual page visualizations
    for page_idx, (page, page_image) in enumerate(zip(pages, images)):
        page_num = page_idx + 1
        
        fig, ax = plt.subplots(1, 1, figsize=(8.5, 11))
        visualize_page(page_image, page.boxes, page_num, ax)
        
        output_path = output_dir / f"page_{page_num:02d}.png"
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"  Page {page_num}: {len(page.boxes)} boxes - saved to {output_path.name}")
    
    # Create a multi-page PDF with all visualizations
    print("\nCreating combined PDF...")
    pdf_path = output_dir / "all_pages_visualization.pdf"
    
    with PdfPages(pdf_path) as pdf:
        for page_idx, (page, page_image) in enumerate(zip(pages, images)):
            fig, ax = plt.subplots(1, 1, figsize=(8.5, 11))
            visualize_page(page_image, page.boxes, page_idx + 1, ax)
            plt.tight_layout()
            pdf.savefig(fig, bbox_inches='tight')
            plt.close()
    
    print(f"\nCombined PDF saved to: {pdf_path}")
    
    # Create a grid overview showing all pages at once
    print("\nCreating grid overview...")
    n_pages = len(pages)
    cols = 4
    rows = (n_pages + cols - 1) // cols
    
    fig, axes = plt.subplots(rows, cols, figsize=(20, rows * 5))
    axes = axes.flatten() if n_pages > cols else [axes]
    
    for idx, (page, page_image) in enumerate(zip(pages, images)):
        if idx < len(axes):
            visualize_page(page_image, page.boxes, idx + 1, axes[idx])
    
    # Hide empty subplots
    for idx in range(n_pages, len(axes)):
        axes[idx].set_visible(False)
    
    plt.suptitle('All Pages - Weighted Merge Results', fontsize=16)
    plt.tight_layout()
    plt.savefig(output_dir / "all_pages_grid.png", dpi=100, bbox_inches='tight')
    plt.close()
    
    # Create summary statistics
    summary = {
        "total_pages": len(pages),
        "pages": []
    }
    
    for page_idx, page in enumerate(pages):
        type_counts = {}
        for box in page.boxes:
            type_counts[box.label] = type_counts.get(box.label, 0) + 1
        
        summary["pages"].append({
            "page": page_idx + 1,
            "total_boxes": len(page.boxes),
            "types": type_counts
        })
    
    with open(output_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n✓ All visualizations saved to {output_dir}/")
    print(f"✓ Individual PNGs: page_01.png through page_{len(pages):02d}.png")
    print(f"✓ Combined PDF: all_pages_visualization.pdf")
    print(f"✓ Grid overview: all_pages_grid.png")


if __name__ == "__main__":
    create_all_visualizations()