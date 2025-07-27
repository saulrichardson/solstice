#!/usr/bin/env python3
"""Visualize the extraction pipeline results."""

import json
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Rectangle
from pdf2image import convert_from_path
from src.injestion.pipeline_extraction import ingest_pdf_for_extraction


def visualize_extraction_organization(page_image, page_data, output_path):
    """Visualize how elements are organized for extraction."""
    
    fig, ax = plt.subplots(1, 1, figsize=(10, 14))
    
    # Color map for different types
    color_map = {
        'Text': 'blue',
        'Title': 'red', 
        'List': 'green',
        'Table': 'purple',
        'Figure': 'orange'
    }
    
    ax.imshow(page_image)
    ax.set_title(f'Page {page_data["page_num"]}: Elements Organized for Extraction', fontsize=14)
    ax.axis('off')
    
    # Draw all boxes with their types
    all_boxes = page_data['all_boxes']
    reading_order = page_data['reading_order']
    
    # Create ID to position mapping
    id_to_pos = {id: i+1 for i, id in enumerate(reading_order)}
    
    for box in all_boxes:
        x1, y1, x2, y2 = box.bbox
        width = x2 - x1
        height = y2 - y1
        color = color_map.get(box.label, 'gray')
        
        # Draw rectangle
        rect = Rectangle((x1, y1), width, height,
                        linewidth=2, edgecolor=color,
                        facecolor='none', alpha=0.8)
        ax.add_patch(rect)
        
        # Add label with reading order position
        pos = id_to_pos.get(box.id, 0)
        label_text = f"{pos}. {box.label}"
        
        ax.text(x1, y1-8, label_text,
                fontsize=10, color=color, weight='bold',
                bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))
    
    # Add statistics
    organized = page_data['organized_elements']
    stats_text = (
        f"Text: {len(organized['text'])}\n"
        f"Figures: {len(organized['figures'])}\n"
        f"Tables: {len(organized['tables'])}"
    )
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
            verticalalignment='top', fontsize=12,
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    # Add legend
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color='blue', lw=3, label='Text'),
        Line2D([0], [0], color='orange', lw=3, label='Figure'),
        Line2D([0], [0], color='purple', lw=3, label='Table'),
        Line2D([0], [0], color='red', lw=3, label='Title'),
        Line2D([0], [0], color='green', lw=3, label='List')
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=10)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()


def create_extraction_flow_diagram():
    """Create a diagram showing the extraction pipeline flow."""
    
    fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8)
    ax.axis('off')
    
    # Title
    ax.text(5, 7.5, 'PDF Extraction Pipeline', fontsize=18, weight='bold', ha='center')
    
    # Pipeline stages
    stages = [
        (2, 6.5, 'PDF Input'),
        (2, 5.5, '1. Layout Detection'),
        (2, 4.5, '2. Box Refinement\n& Merging'),
        (2, 3.5, '3. Semantic Ordering'),
        (2, 2.5, '4. Type-based Routing'),
    ]
    
    for x, y, text in stages:
        rect = patches.FancyBboxPatch((x-0.8, y-0.3), 1.6, 0.6,
                                     boxstyle="round,pad=0.1",
                                     facecolor='lightblue',
                                     edgecolor='black')
        ax.add_patch(rect)
        ax.text(x, y, text, ha='center', va='center', fontsize=12)
    
    # Arrows between stages
    for i in range(len(stages)-1):
        ax.arrow(2, stages[i][1]-0.35, 0, -0.5, head_width=0.1, head_length=0.1, fc='black', ec='black')
    
    # Extractors
    extractors = [
        (6, 3, 'Text\nExtractor', 'lightgreen'),
        (6, 2, 'Table\nExtractor', 'lightcoral'),
        (6, 1, 'Figure\nExtractor', 'lightyellow'),
    ]
    
    for x, y, text, color in extractors:
        rect = patches.FancyBboxPatch((x-0.7, y-0.3), 1.4, 0.6,
                                     boxstyle="round,pad=0.1",
                                     facecolor=color,
                                     edgecolor='black')
        ax.add_patch(rect)
        ax.text(x, y, text, ha='center', va='center', fontsize=11)
    
    # Arrows to extractors
    ax.arrow(2.8, 2.5, 2.5, 0.3, head_width=0.1, head_length=0.1, fc='gray', ec='gray')
    ax.arrow(2.8, 2.5, 2.5, -0.3, head_width=0.1, head_length=0.1, fc='gray', ec='gray')
    ax.arrow(2.8, 2.5, 2.5, -0.9, head_width=0.1, head_length=0.1, fc='gray', ec='gray')
    
    # Output
    rect = patches.FancyBboxPatch((7.5, 1.7), 2, 0.8,
                                 boxstyle="round,pad=0.1",
                                 facecolor='gold',
                                 edgecolor='black',
                                 linewidth=2)
    ax.add_patch(rect)
    ax.text(8.5, 2.1, 'Semantic\nDocument', ha='center', va='center', fontsize=12, weight='bold')
    
    # Notes
    notes = [
        "• Elements organized by type",
        "• Reading order preserved",
        "• Figure-caption pairs identified",
        "• Ready for specialized extraction"
    ]
    
    for i, note in enumerate(notes):
        ax.text(0.5, 0.5 - i*0.15, note, fontsize=10)
    
    plt.tight_layout()
    plt.savefig('extraction_pipeline_flow.png', dpi=150, bbox_inches='tight')
    plt.close()


def main():
    """Generate visualizations for the extraction pipeline."""
    
    # Create flow diagram
    print("Creating pipeline flow diagram...")
    create_extraction_flow_diagram()
    print("Saved: extraction_pipeline_flow.png")
    
    # Visualize a sample page
    pdf_path = Path("Liu et al. (2024).pdf")
    if pdf_path.exists():
        print("\nVisualizing extraction organization...")
        
        # Get extraction data
        extraction_data = ingest_pdf_for_extraction(pdf_path)
        
        # Get page images
        images = convert_from_path(pdf_path, dpi=200)
        
        # Visualize page 2 (has a figure)
        page_idx = 1
        if page_idx < len(extraction_data) and page_idx < len(images):
            visualize_extraction_organization(
                images[page_idx],
                extraction_data[page_idx],
                'extraction_organization_page2.png'
            )
            print("Saved: extraction_organization_page2.png")


if __name__ == "__main__":
    main()