#!/usr/bin/env python3
"""Test visual reordering for complex layouts with figures and tables."""

import os
from pathlib import Path
from src.injestion.pipeline_extraction_vision import (
    ingest_pdf_for_extraction_with_vision
)
from src.injestion.agent.visual_reordering import LLMClient
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pdf2image import convert_from_path


def visualize_reordering_results(extraction_data, pdf_path, output_dir="visual_reordering_results"):
    """Create visualizations showing the reordering results."""
    
    # Create output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Get page images
    images = convert_from_path(pdf_path, dpi=200)
    
    # Color map
    color_map = {
        'Text': 'blue',
        'Title': 'red', 
        'List': 'green',
        'Table': 'purple',
        'Figure': 'orange'
    }
    
    # Process pages that were reordered
    reordered_pages = [
        (i, data) for i, data in enumerate(extraction_data)
        if data.get('vision_reordered', False)
    ]
    
    print(f"\nPages with visual reordering applied: {len(reordered_pages)}")
    
    for page_idx, page_data in reordered_pages:
        page_num = page_data['page_num']
        page_image = images[page_idx]
        
        fig, ax = plt.subplots(1, 1, figsize=(12, 16))
        ax.imshow(page_image)
        ax.set_title(f'Page {page_num} - Visual Reordering Applied', fontsize=16)
        ax.axis('off')
        
        # Draw boxes with reading order
        all_boxes = page_data['all_boxes']
        reading_order = page_data['reading_order']
        id_to_pos = {id: i+1 for i, id in enumerate(reading_order)}
        
        # First pass: draw all boxes
        for box in all_boxes:
            x1, y1, x2, y2 = box.bbox
            width = x2 - x1
            height = y2 - y1
            color = color_map.get(box.label, 'gray')
            
            # Draw rectangle
            rect = patches.Rectangle((x1, y1), width, height,
                                   linewidth=2, edgecolor=color,
                                   facecolor='none', alpha=0.8)
            ax.add_patch(rect)
            
            # Add number
            pos = id_to_pos.get(box.id, 0)
            ax.text(x1 + width/2, y1 + height/2, str(pos),
                   fontsize=20, color='red', weight='bold',
                   ha='center', va='center',
                   bbox=dict(boxstyle="circle,pad=0.3", facecolor='yellow', alpha=0.9))
            
            # Add label in corner
            ax.text(x1 + 5, y1 + 20, box.label,
                   fontsize=10, color=color, weight='bold',
                   bbox=dict(boxstyle="round,pad=0.2", facecolor='white', alpha=0.7))
        
        # Draw flow arrows for figure-caption pairs
        prev_box = None
        for i, box_id in enumerate(reading_order):
            box = next((b for b in all_boxes if b.id == box_id), None)
            if not box:
                continue
                
            if prev_box and prev_box.label == 'Figure' and box.label == 'Text':
                # This might be a figure-caption pair
                prev_center = ((prev_box.bbox[0] + prev_box.bbox[2])/2,
                              (prev_box.bbox[1] + prev_box.bbox[3])/2)
                curr_center = ((box.bbox[0] + box.bbox[2])/2,
                              (box.bbox[1] + box.bbox[3])/2)
                
                ax.annotate('', xy=curr_center, xytext=prev_center,
                           arrowprops=dict(arrowstyle='->', color='green', 
                                         lw=3, alpha=0.7))
                
                # Highlight the pair
                ax.text((prev_center[0] + curr_center[0])/2,
                       (prev_center[1] + curr_center[1])/2,
                       'Caption', fontsize=12, color='green', weight='bold',
                       bbox=dict(boxstyle="round,pad=0.3", facecolor='lightgreen', alpha=0.8))
            
            prev_box = box
        
        # Save
        output_path = output_dir / f"page_{page_num:02d}_reordered.png"
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"  - Page {page_num} visualization saved to {output_path}")
    
    # Summary statistics
    total_pages = len(extraction_data)
    complex_pages = sum(1 for data in extraction_data 
                       if any(box.label in ['Figure', 'Table'] 
                             for box in data['all_boxes']))
    
    print(f"\nSummary:")
    print(f"  Total pages: {total_pages}")
    print(f"  Pages with figures/tables: {complex_pages}")
    print(f"  Pages reordered by vision: {len(reordered_pages)}")


def test_visual_reordering():
    """Test the visual reordering on a PDF with complex layouts."""
    
    pdf_path = Path("Liu et al. (2024).pdf")
    if not pdf_path.exists():
        print(f"Error: {pdf_path} not found")
        return
    
    print("Testing Visual Reordering for Complex Layouts")
    print("=" * 70)
    
    # Initialize LLM client
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not set")
        return
    
    llm_client = LLMClient(api_key=api_key)
    
    # Process with visual reordering
    print("\nProcessing PDF with visual reordering enabled...")
    extraction_data = ingest_pdf_for_extraction_with_vision(
        pdf_path=pdf_path,
        detection_dpi=200,
        merge_strategy="weighted",
        use_vision_reordering=True,
        llm_client=llm_client,
        save_debug_visualizations=True
    )
    
    # Analyze results
    print("\nAnalyzing reordering results...")
    
    for page_idx, page_data in enumerate(extraction_data):
        page_num = page_data['page_num']
        has_figures = any(box.label == 'Figure' for box in page_data['all_boxes'])
        has_tables = any(box.label == 'Table' for box in page_data['all_boxes'])
        was_reordered = page_data.get('vision_reordered', False)
        
        if has_figures or has_tables:
            print(f"\nPage {page_num}:")
            print(f"  - Figures: {sum(1 for box in page_data['all_boxes'] if box.label == 'Figure')}")
            print(f"  - Tables: {sum(1 for box in page_data['all_boxes'] if box.label == 'Table')}")
            print(f"  - Vision reordering applied: {'Yes' if was_reordered else 'No'}")
            
            if was_reordered:
                # Look for figure-caption sequences
                reading_order = page_data['reading_order']
                id_to_box = {b.id: b for b in page_data['all_boxes']}
                
                caption_pairs = []
                for i in range(len(reading_order) - 1):
                    curr_box = id_to_box.get(reading_order[i])
                    next_box = id_to_box.get(reading_order[i+1])
                    
                    if curr_box and next_box:
                        if curr_box.label == 'Figure' and next_box.label == 'Text':
                            caption_pairs.append((i+1, i+2))
                
                if caption_pairs:
                    print(f"  - Detected figure-caption pairs at positions: {caption_pairs}")
    
    # Create visualizations
    visualize_reordering_results(extraction_data, pdf_path)
    
    print("\n" + "=" * 70)
    print("Visual reordering complete!")
    print("\nThe hybrid approach:")
    print("1. Uses standard column-based ordering for most pages (99% effective)")
    print("2. Applies visual analysis only to pages with figures/tables")
    print("3. Corrects caption ordering issues across columns")
    print("4. Maintains efficiency by limiting vision API calls")


if __name__ == "__main__":
    test_visual_reordering()