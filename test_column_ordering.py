#!/usr/bin/env python3
"""Test column-aware reading order."""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Rectangle, FancyBboxPatch
from pathlib import Path
from pdf2image import convert_from_path
from src.injestion.pipeline_extraction import (
    ingest_pdf_for_extraction,
    detect_columns
)


def visualize_column_detection(page_image, page_data, output_path):
    """Visualize column detection and reading order."""
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 14))
    
    # Color map
    color_map = {
        'Text': 'blue',
        'Title': 'red', 
        'List': 'green',
        'Table': 'purple',
        'Figure': 'orange'
    }
    
    # Left plot: Column detection
    ax1.imshow(page_image)
    ax1.set_title('Column Detection', fontsize=14)
    ax1.axis('off')
    
    # Detect columns
    all_boxes = page_data['all_boxes']
    columns = detect_columns(all_boxes)
    
    # Draw column regions
    column_colors = ['yellow', 'lightblue', 'lightgreen']
    
    for col_idx, column_boxes in enumerate(columns):
        if not column_boxes:
            continue
            
        # Find bounding box of column
        if col_idx == 0 and len(columns) > 1:
            # Spanning elements
            label = "Spanning"
            alpha = 0.2
        else:
            label = f"Column {col_idx}"
            alpha = 0.1
            
        for box in column_boxes:
            x1, y1, x2, y2 = box.bbox
            width = x2 - x1
            height = y2 - y1
            
            # Column background
            rect = Rectangle((x1-5, y1-5), width+10, height+10,
                           facecolor=column_colors[col_idx % 3],
                           alpha=alpha)
            ax1.add_patch(rect)
            
            # Box outline
            rect = Rectangle((x1, y1), width, height,
                           linewidth=2, edgecolor=color_map.get(box.label, 'gray'),
                           facecolor='none')
            ax1.add_patch(rect)
    
    # Add column labels
    ax1.text(0.02, 0.98, f"Detected {len(columns)} column(s)", 
            transform=ax1.transAxes, verticalalignment='top', fontsize=12,
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # Right plot: Reading order
    ax2.imshow(page_image)
    ax2.set_title('Reading Order (Column-Aware)', fontsize=14)
    ax2.axis('off')
    
    # Draw reading order
    reading_order = page_data['reading_order']
    id_to_pos = {id: i+1 for i, id in enumerate(reading_order)}
    
    # Draw arrows showing reading flow
    prev_box = None
    for i, box_id in enumerate(reading_order):
        box = next((b for b in all_boxes if b.id == box_id), None)
        if not box:
            continue
            
        x1, y1, x2, y2 = box.bbox
        width = x2 - x1
        height = y2 - y1
        color = color_map.get(box.label, 'gray')
        
        # Draw rectangle
        rect = Rectangle((x1, y1), width, height,
                        linewidth=2, edgecolor=color,
                        facecolor='none', alpha=0.8)
        ax2.add_patch(rect)
        
        # Add number
        pos = id_to_pos.get(box.id, 0)
        ax2.text(x1 + width/2, y1 + height/2, str(pos),
                fontsize=16, color='red', weight='bold',
                ha='center', va='center',
                bbox=dict(boxstyle="circle,pad=0.3", facecolor='yellow', alpha=0.9))
        
        # Draw arrow from previous box
        if prev_box and i > 0:
            prev_center = ((prev_box.bbox[0] + prev_box.bbox[2])/2,
                          (prev_box.bbox[1] + prev_box.bbox[3])/2)
            curr_center = ((x1 + x2)/2, (y1 + y2)/2)
            
            ax2.annotate('', xy=curr_center, xytext=prev_center,
                        arrowprops=dict(arrowstyle='->', color='green', 
                                      lw=1.5, alpha=0.6))
        
        prev_box = box
    
    # Add statistics
    stats_text = f"Total elements: {len(all_boxes)}\nReading order: {len(reading_order)} elements"
    ax2.text(0.02, 0.98, stats_text, transform=ax2.transAxes,
            verticalalignment='top', fontsize=12,
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()


def test_column_ordering():
    """Test column-aware ordering on pages."""
    
    pdf_path = Path("Liu et al. (2024).pdf")
    if not pdf_path.exists():
        print(f"Error: {pdf_path} not found")
        return
    
    print("Testing Column-Aware Reading Order")
    print("="*70)
    
    # Get extraction data
    extraction_data = ingest_pdf_for_extraction(pdf_path)
    
    # Get page images
    images = convert_from_path(pdf_path, dpi=200)
    
    # Test on multiple pages
    test_pages = [1, 3, 4]  # Pages 2, 4, 5 (0-indexed)
    
    for page_idx in test_pages:
        if page_idx >= len(extraction_data) or page_idx >= len(images):
            continue
            
        page_data = extraction_data[page_idx]
        page_image = images[page_idx]
        page_num = page_idx + 1
        
        print(f"\nPage {page_num}:")
        
        # Detect columns
        columns = detect_columns(page_data['all_boxes'])
        print(f"  Columns detected: {len(columns)}")
        
        if len(columns) > 1:
            print(f"  - Spanning elements: {len(columns[0])}")
            for i in range(1, len(columns)):
                print(f"  - Column {i}: {len(columns[i])} elements")
        
        # Analyze reading order
        reading_order = page_data['reading_order']
        print(f"  Reading order: {len(reading_order)} elements")
        
        # Check for figure-caption pairs
        all_boxes = page_data['all_boxes']
        id_to_box = {b.id: b for b in all_boxes}
        
        for i in range(len(reading_order) - 1):
            curr_box = id_to_box.get(reading_order[i])
            next_box = id_to_box.get(reading_order[i+1])
            
            if curr_box and next_box:
                if curr_box.label == 'Figure' and next_box.label == 'Text':
                    print(f"  ✓ Potential figure-caption pair at positions {i+1}-{i+2}")
        
        # Create visualization
        output_path = f"column_ordering_page{page_num:02d}.png"
        visualize_column_detection(page_image, page_data, output_path)
        print(f"  Saved: {output_path}")
    
    print("\n" + "="*70)
    print("Column detection improves reading order by:")
    print("- Reading top-to-bottom within each column")
    print("- Processing spanning elements (titles, figures) first")
    print("- Maintaining left-to-right order between columns")


if __name__ == "__main__":
    test_column_ordering()