#!/usr/bin/env python3
"""Simple test of vision-based caption association on a single page."""

import json
from pathlib import Path
from pdf2image import convert_from_path
from src.injestion.pipeline_simple import ingest_pdf_simple
from src.injestion.agent.caption_association_vision import associate_captions_with_vision
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Rectangle


def test_single_page_vision():
    """Test vision caption association on a single page with figures."""
    
    pdf_path = Path("Liu et al. (2024).pdf")
    if not pdf_path.exists():
        print(f"Error: {pdf_path} not found")
        return
    
    print("Testing Vision-Based Caption Association")
    print("="*70)
    
    # Process PDF to get boxes
    print("\nExtracting layout boxes...")
    pages = ingest_pdf_simple(pdf_path)
    
    # Get page images
    print("Converting to images...")
    images = convert_from_path(pdf_path, dpi=200)
    
    # Test on page 4 which has a figure
    page_idx = 3  # 0-indexed
    page = pages[page_idx]
    page_image = images[page_idx]
    
    # Count elements
    n_figures = sum(1 for b in page.boxes if b.label == "Figure")
    n_tables = sum(1 for b in page.boxes if b.label == "Table")
    n_text = sum(1 for b in page.boxes if b.label == "Text")
    
    print(f"\nPage 4 contains:")
    print(f"  - {n_figures} figures")
    print(f"  - {n_tables} tables")
    print(f"  - {n_text} text boxes")
    
    # Test vision association
    print("\nTesting vision-based caption association...")
    try:
        semantic_groups = associate_captions_with_vision(
            page_image=page_image,
            boxes=page.boxes,
            debug=True  # This will save debug_vision_annotated.png
        )
        
        print(f"\nCreated {len(semantic_groups)} semantic groups")
        
        # Analyze results
        figure_groups = [g for g in semantic_groups if g.primary_element.label == "Figure"]
        figures_with_captions = [g for g in figure_groups if g.caption is not None]
        
        print(f"\nFigure analysis:")
        print(f"  - Total figures: {len(figure_groups)}")
        print(f"  - Figures with captions: {len(figures_with_captions)}")
        
        # Show details of figure associations
        for i, group in enumerate(figure_groups):
            print(f"\nFigure {i+1}:")
            print(f"  - Bounding box: {group.primary_element.bbox}")
            print(f"  - Has caption: {group.caption is not None}")
            if group.caption:
                print(f"  - Caption box: {group.caption.bbox}")
                print(f"  - Association confidence: {group.confidence:.2f}")
        
        # Create visualization
        visualize_vision_results(page_image, semantic_groups, "vision_caption_result.png")
        print("\nVisualization saved to vision_caption_result.png")
        print("Debug annotated image saved to debug_vision_annotated.png")
        
    except Exception as e:
        print(f"\nError during vision processing: {e}")
        import traceback
        traceback.print_exc()


def visualize_vision_results(page_image, semantic_groups, output_path):
    """Visualize vision-based semantic groups."""
    
    fig, ax = plt.subplots(1, 1, figsize=(10, 14))
    
    # Color map
    color_map = {
        'Text': 'blue',
        'Title': 'red', 
        'List': 'green',
        'Table': 'purple',
        'Figure': 'orange'
    }
    
    ax.imshow(page_image)
    ax.set_title('Vision-Based Caption Association Results', fontsize=14)
    ax.axis('off')
    
    # Draw semantic groups
    for group in semantic_groups:
        primary = group.primary_element
        x1, y1, x2, y2 = primary.bbox
        width = x2 - x1
        height = y2 - y1
        color = color_map.get(primary.label, 'gray')
        
        # Thicker border if it has a caption
        linewidth = 4 if group.caption else 2
        
        rect = Rectangle((x1, y1), width, height,
                        linewidth=linewidth, edgecolor=color,
                        facecolor='none', alpha=0.8)
        ax.add_patch(rect)
        
        # Label
        label_text = f"{primary.label}"
        if group.caption:
            label_text += " ✓"  # Check mark for caption
        
        ax.text(x1, y1-10, label_text,
                fontsize=12, color=color, weight='bold',
                bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.9))
        
        # Draw caption if exists
        if group.caption:
            cx1, cy1, cx2, cy2 = group.caption.bbox
            cwidth = cx2 - cx1
            cheight = cy2 - cy1
            
            # Draw caption box with dashed line
            caption_rect = Rectangle((cx1, cy1), cwidth, cheight,
                                   linewidth=3, edgecolor=color,
                                   facecolor='none', alpha=0.7,
                                   linestyle='--')
            ax.add_patch(caption_rect)
            
            # Draw connection arrow
            fig_center_x = (x1 + x2) / 2
            fig_bottom = y2
            caption_center_x = (cx1 + cx2) / 2
            caption_top = cy1
            
            ax.annotate('', xy=(caption_center_x, caption_top),
                       xytext=(fig_center_x, fig_bottom),
                       arrowprops=dict(arrowstyle='->', color=color, lw=2, alpha=0.7))
            
            # Add confidence score
            ax.text(cx2 + 10, cy1 + cheight/2, f"Conf: {group.confidence:.2f}",
                   fontsize=10, color=color, weight='bold',
                   va='center', bbox=dict(boxstyle="round,pad=0.2", 
                                         facecolor='yellow', alpha=0.7))
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()


if __name__ == "__main__":
    test_single_page_vision()