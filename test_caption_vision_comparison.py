#!/usr/bin/env python3
"""Compare heuristic vs vision-based caption association approaches."""

import json
from pathlib import Path
from pdf2image import convert_from_path
from src.injestion.pipeline_simple import ingest_pdf_simple
from src.injestion.agent.caption_association import (
    associate_captions_with_figures,
    create_extraction_ready_groups
)
from src.injestion.agent.caption_association_vision import (
    associate_captions_with_vision,
    create_extraction_ready_groups_vision
)
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Rectangle
import matplotlib.lines as mlines


def visualize_comparison(page_image, heuristic_groups, vision_groups, page_num, output_path):
    """Visualize both approaches side by side."""
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 14))
    
    # Color map
    color_map = {
        'Text': 'blue',
        'Title': 'red', 
        'List': 'green',
        'Table': 'purple',
        'Figure': 'orange'
    }
    
    # Plot heuristic approach
    ax1.imshow(page_image)
    ax1.set_title(f'Heuristic Approach - Page {page_num}', fontsize=14)
    ax1.axis('off')
    
    for group in heuristic_groups:
        primary = group.primary_element
        x1, y1, x2, y2 = primary.bbox
        width = x2 - x1
        height = y2 - y1
        color = color_map.get(primary.label, 'gray')
        
        linewidth = 3 if group.caption else 2
        
        rect = Rectangle((x1, y1), width, height,
                        linewidth=linewidth, edgecolor=color,
                        facecolor='none', alpha=0.8)
        ax1.add_patch(rect)
        
        label_text = f"{primary.label}"
        if group.caption:
            label_text += " [+C]"
        
        ax1.text(x1, y1-8, label_text,
                fontsize=10, color=color, weight='bold',
                bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))
        
        if group.caption:
            cx1, cy1, cx2, cy2 = group.caption.bbox
            cwidth = cx2 - cx1
            cheight = cy2 - cy1
            
            caption_rect = Rectangle((cx1, cy1), cwidth, cheight,
                                   linewidth=2, edgecolor=color,
                                   facecolor='none', alpha=0.6,
                                   linestyle='--')
            ax1.add_patch(caption_rect)
            
            fig_center_x = (x1 + x2) / 2
            fig_bottom = y2
            caption_center_x = (cx1 + cx2) / 2
            caption_top = cy1
            
            ax1.plot([fig_center_x, caption_center_x], 
                   [fig_bottom, caption_top],
                   color=color, linewidth=1, alpha=0.5, linestyle=':')
            
            ax1.text(cx2 + 5, cy1, f"{group.confidence:.2f}",
                   fontsize=8, color=color, style='italic')
    
    # Plot vision approach
    ax2.imshow(page_image)
    ax2.set_title(f'Vision-Based Approach - Page {page_num}', fontsize=14)
    ax2.axis('off')
    
    for group in vision_groups:
        primary = group.primary_element
        x1, y1, x2, y2 = primary.bbox
        width = x2 - x1
        height = y2 - y1
        color = color_map.get(primary.label, 'gray')
        
        linewidth = 3 if group.caption else 2
        
        rect = Rectangle((x1, y1), width, height,
                        linewidth=linewidth, edgecolor=color,
                        facecolor='none', alpha=0.8)
        ax2.add_patch(rect)
        
        label_text = f"{primary.label}"
        if group.caption:
            label_text += " [+C]"
        
        ax2.text(x1, y1-8, label_text,
                fontsize=10, color=color, weight='bold',
                bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))
        
        if group.caption:
            cx1, cy1, cx2, cy2 = group.caption.bbox
            cwidth = cx2 - cx1
            cheight = cy2 - cy1
            
            caption_rect = Rectangle((cx1, cy1), cwidth, cheight,
                                   linewidth=2, edgecolor=color,
                                   facecolor='none', alpha=0.6,
                                   linestyle='--')
            ax2.add_patch(caption_rect)
            
            fig_center_x = (x1 + x2) / 2
            fig_bottom = y2
            caption_center_x = (cx1 + cx2) / 2
            caption_top = cy1
            
            ax2.plot([fig_center_x, caption_center_x], 
                   [fig_bottom, caption_top],
                   color=color, linewidth=1, alpha=0.5, linestyle=':')
            
            ax2.text(cx2 + 5, cy1, f"{group.confidence:.2f}",
                   fontsize=8, color=color, style='italic')
    
    # Add legend
    legend_elements = [
        mlines.Line2D([0], [0], color='orange', lw=3, label='Figure'),
        mlines.Line2D([0], [0], color='purple', lw=3, label='Table'),
        mlines.Line2D([0], [0], color='gray', lw=2, linestyle='--', label='Caption'),
        mlines.Line2D([0], [0], color='gray', lw=1, linestyle=':', label='Association')
    ]
    ax2.legend(handles=legend_elements, loc='upper right', fontsize=10)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()


def compare_approaches():
    """Compare heuristic and vision-based caption association."""
    
    pdf_path = Path("Liu et al. (2024).pdf")
    if not pdf_path.exists():
        print(f"Error: {pdf_path} not found")
        return
    
    print("Comparing Caption Association Approaches")
    print("="*70)
    
    # Process PDF
    pages = ingest_pdf_simple(pdf_path)
    
    # Get page images
    images = convert_from_path(pdf_path, dpi=200)
    
    # Create output directory
    output_dir = Path("caption_vision_comparison")
    output_dir.mkdir(exist_ok=True)
    
    # Compare results
    comparison_results = {
        "pages": [],
        "summary": {
            "heuristic": {
                "total_figures": 0,
                "figures_with_captions": 0,
                "total_tables": 0,
                "tables_with_captions": 0
            },
            "vision": {
                "total_figures": 0,
                "figures_with_captions": 0,
                "total_tables": 0,
                "tables_with_captions": 0
            }
        }
    }
    
    # Process pages with figures/tables
    for page_idx, (page, page_image) in enumerate(zip(pages, images)):
        page_num = page_idx + 1
        
        # Count figures and tables
        n_figures = sum(1 for b in page.boxes if b.label == "Figure")
        n_tables = sum(1 for b in page.boxes if b.label == "Table")
        
        if n_figures > 0 or n_tables > 0:
            print(f"\nPage {page_num}: {n_figures} figures, {n_tables} tables")
            
            # Heuristic approach
            heuristic_groups = associate_captions_with_figures(page.boxes)
            heuristic_organized = create_extraction_ready_groups(page.boxes, page.reading_order)
            
            h_figs_with_captions = sum(1 for g in heuristic_organized["figure_groups"] if g.caption)
            h_tables_with_captions = sum(1 for g in heuristic_organized["table_groups"] if g.caption)
            
            print(f"  Heuristic: {h_figs_with_captions}/{n_figures} figures, "
                  f"{h_tables_with_captions}/{n_tables} tables with captions")
            
            # Vision approach
            try:
                vision_groups = associate_captions_with_vision(
                    page_image, page.boxes, debug=False
                )
                vision_organized = create_extraction_ready_groups_vision(
                    page_image, page.boxes, page.reading_order, debug=False
                )
                
                v_figs_with_captions = sum(1 for g in vision_organized["figure_groups"] if g.caption)
                v_tables_with_captions = sum(1 for g in vision_organized["table_groups"] if g.caption)
                
                print(f"  Vision:    {v_figs_with_captions}/{n_figures} figures, "
                      f"{v_tables_with_captions}/{n_tables} tables with captions")
                
            except Exception as e:
                print(f"  Vision approach failed: {e}")
                vision_groups = heuristic_groups
                v_figs_with_captions = h_figs_with_captions
                v_tables_with_captions = h_tables_with_captions
            
            # Update summaries
            comparison_results["summary"]["heuristic"]["total_figures"] += n_figures
            comparison_results["summary"]["heuristic"]["total_tables"] += n_tables
            comparison_results["summary"]["heuristic"]["figures_with_captions"] += h_figs_with_captions
            comparison_results["summary"]["heuristic"]["tables_with_captions"] += h_tables_with_captions
            
            comparison_results["summary"]["vision"]["total_figures"] += n_figures
            comparison_results["summary"]["vision"]["total_tables"] += n_tables
            comparison_results["summary"]["vision"]["figures_with_captions"] += v_figs_with_captions
            comparison_results["summary"]["vision"]["tables_with_captions"] += v_tables_with_captions
            
            # Store page results
            page_result = {
                "page": page_num,
                "figures": n_figures,
                "tables": n_tables,
                "heuristic": {
                    "figures_with_captions": h_figs_with_captions,
                    "tables_with_captions": h_tables_with_captions
                },
                "vision": {
                    "figures_with_captions": v_figs_with_captions,
                    "tables_with_captions": v_tables_with_captions
                }
            }
            comparison_results["pages"].append(page_result)
            
            # Create comparison visualization
            print(f"  Creating comparison visualization...")
            visualize_comparison(
                page_image,
                heuristic_groups,
                vision_groups,
                page_num,
                output_dir / f"page_{page_num:02d}_comparison.png"
            )
    
    # Save results
    with open(output_dir / "comparison_results.json", "w") as f:
        json.dump(comparison_results, f, indent=2)
    
    # Print summary
    print("\n" + "="*70)
    print("COMPARISON SUMMARY:")
    print("="*70)
    
    h_summary = comparison_results["summary"]["heuristic"]
    v_summary = comparison_results["summary"]["vision"]
    
    print("\nHeuristic Approach:")
    print(f"  Figures: {h_summary['figures_with_captions']}/{h_summary['total_figures']} "
          f"({h_summary['figures_with_captions']/h_summary['total_figures']*100:.1f}%)")
    print(f"  Tables:  {h_summary['tables_with_captions']}/{h_summary['total_tables']} "
          f"({h_summary['tables_with_captions']/max(h_summary['total_tables'],1)*100:.1f}%)")
    
    print("\nVision-Based Approach:")
    print(f"  Figures: {v_summary['figures_with_captions']}/{v_summary['total_figures']} "
          f"({v_summary['figures_with_captions']/v_summary['total_figures']*100:.1f}%)")
    print(f"  Tables:  {v_summary['tables_with_captions']}/{v_summary['total_tables']} "
          f"({v_summary['tables_with_captions']/max(v_summary['total_tables'],1)*100:.1f}%)")
    
    print(f"\nResults saved to {output_dir}/")


if __name__ == "__main__":
    compare_approaches()