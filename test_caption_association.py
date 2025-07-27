#!/usr/bin/env python3
"""Test caption association with figures and tables."""

import json
from pathlib import Path
from pdf2image import convert_from_path
from src.injestion.pipeline_simple import ingest_pdf_simple
from src.injestion.agent.caption_association import (
    associate_captions_with_figures,
    create_extraction_ready_groups,
    format_groups_for_extraction
)
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Rectangle, FancyBboxPatch
import matplotlib.lines as mlines


def visualize_semantic_groups(page_image, semantic_groups, page_num, output_path):
    """Visualize semantic groups with caption associations."""
    
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
    ax.set_title(f'Page {page_num}: Semantic Groups (Figure/Table + Caption)', fontsize=14)
    ax.axis('off')
    
    # Draw semantic groups
    for group in semantic_groups:
        # Draw primary element
        primary = group.primary_element
        x1, y1, x2, y2 = primary.bbox
        width = x2 - x1
        height = y2 - y1
        color = color_map.get(primary.label, 'gray')
        
        # Draw with thicker border if it has a caption
        linewidth = 3 if group.caption else 2
        
        rect = Rectangle((x1, y1), width, height,
                        linewidth=linewidth, edgecolor=color,
                        facecolor='none', alpha=0.8)
        ax.add_patch(rect)
        
        # Label
        label_text = f"{primary.label}"
        if group.caption:
            label_text += " [+C]"  # Has caption
        
        ax.text(x1, y1-8, label_text,
                fontsize=10, color=color, weight='bold',
                bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))
        
        # Draw caption if exists
        if group.caption:
            cx1, cy1, cx2, cy2 = group.caption.bbox
            cwidth = cx2 - cx1
            cheight = cy2 - cy1
            
            # Draw caption box with dashed line
            caption_rect = Rectangle((cx1, cy1), cwidth, cheight,
                                   linewidth=2, edgecolor=color,
                                   facecolor='none', alpha=0.6,
                                   linestyle='--')
            ax.add_patch(caption_rect)
            
            # Draw connection line between figure and caption
            fig_center_x = (x1 + x2) / 2
            fig_bottom = y2
            caption_center_x = (cx1 + cx2) / 2
            caption_top = cy1
            
            ax.plot([fig_center_x, caption_center_x], 
                   [fig_bottom, caption_top],
                   color=color, linewidth=1, alpha=0.5, linestyle=':')
            
            # Add confidence score
            ax.text(cx2 + 5, cy1, f"{group.confidence:.2f}",
                   fontsize=8, color=color, style='italic')
    
    # Add legend
    legend_elements = [
        mlines.Line2D([0], [0], color='orange', lw=3, label='Figure'),
        mlines.Line2D([0], [0], color='purple', lw=3, label='Table'),
        mlines.Line2D([0], [0], color='blue', lw=2, label='Text'),
        mlines.Line2D([0], [0], color='gray', lw=2, linestyle='--', label='Caption'),
        mlines.Line2D([0], [0], color='gray', lw=1, linestyle=':', label='Association')
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=10)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()


def test_caption_association():
    """Test caption association on pages with figures."""
    
    pdf_path = Path("Liu et al. (2024).pdf")
    if not pdf_path.exists():
        print(f"Error: {pdf_path} not found")
        return
    
    print("Testing caption association...")
    print("="*70)
    
    # Process PDF
    pages = ingest_pdf_simple(pdf_path)
    
    # Get page images
    images = convert_from_path(pdf_path, dpi=200)
    
    # Create output directory
    output_dir = Path("caption_association_results")
    output_dir.mkdir(exist_ok=True)
    
    # Analyze pages with figures/tables
    all_results = {
        "pages": [],
        "summary": {
            "total_figures": 0,
            "total_tables": 0,
            "figures_with_captions": 0,
            "tables_with_captions": 0
        }
    }
    
    for page_idx, (page, page_image) in enumerate(zip(pages, images)):
        page_num = page_idx + 1
        
        # Count figures and tables
        n_figures = sum(1 for b in page.boxes if b.label == "Figure")
        n_tables = sum(1 for b in page.boxes if b.label == "Table")
        
        if n_figures > 0 or n_tables > 0:
            print(f"\nPage {page_num}:")
            print(f"  Figures: {n_figures}, Tables: {n_tables}")
            
            # Associate captions
            semantic_groups = associate_captions_with_figures(page.boxes)
            
            # Create extraction-ready groups
            organized = create_extraction_ready_groups(page.boxes, page.reading_order)
            
            # Count associations
            figs_with_captions = sum(1 for g in organized["figure_groups"] if g.caption)
            tables_with_captions = sum(1 for g in organized["table_groups"] if g.caption)
            
            print(f"  Figures with captions: {figs_with_captions}/{n_figures}")
            print(f"  Tables with captions: {tables_with_captions}/{n_tables}")
            
            # Update summary
            all_results["summary"]["total_figures"] += n_figures
            all_results["summary"]["total_tables"] += n_tables
            all_results["summary"]["figures_with_captions"] += figs_with_captions
            all_results["summary"]["tables_with_captions"] += tables_with_captions
            
            # Format for extraction
            extraction_data = format_groups_for_extraction(organized)
            
            # Store page results
            page_results = {
                "page": page_num,
                "figures": n_figures,
                "tables": n_tables,
                "semantic_groups": len(semantic_groups),
                "extraction_data": extraction_data
            }
            all_results["pages"].append(page_results)
            
            # Visualize this page
            if n_figures > 0 or n_tables > 0:
                print(f"  Creating visualization...")
                visualize_semantic_groups(
                    page_image,
                    semantic_groups,
                    page_num,
                    output_dir / f"page_{page_num:02d}_groups.png"
                )
    
    # Save results
    with open(output_dir / "caption_analysis.json", "w") as f:
        json.dump(all_results, f, indent=2)
    
    # Print summary
    print("\n" + "="*70)
    print("SUMMARY:")
    print("="*70)
    summary = all_results["summary"]
    
    print(f"Total figures: {summary['total_figures']}")
    print(f"Figures with captions: {summary['figures_with_captions']}")
    
    if summary['total_figures'] > 0:
        caption_rate = summary['figures_with_captions'] / summary['total_figures'] * 100
        print(f"Caption association rate: {caption_rate:.1f}%")
    
    print(f"\nTotal tables: {summary['total_tables']}")
    print(f"Tables with captions: {summary['tables_with_captions']}")
    
    print(f"\nResults saved to {output_dir}/")
    
    # Show example extraction data for first figure found
    for page_data in all_results["pages"]:
        if page_data["extraction_data"]["figures"]:
            print("\nExample extraction data for first figure:")
            fig_data = page_data["extraction_data"]["figures"][0]
            print(json.dumps(fig_data, indent=2))
            break


if __name__ == "__main__":
    test_caption_association()