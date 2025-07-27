#!/usr/bin/env python3
"""Test layout detection with LLM refinement and visualize results."""

import json
from pathlib import Path
from pdf2image import convert_from_path
from src.injestion.pipeline import ingest_pdf
from visualize_layout import visualize_page, create_summary_visualization
import matplotlib.pyplot as plt

def test_refined_detection():
    """Test the full pipeline with LLM refinement."""
    pdf_path = Path("Liu et al. (2024).pdf")
    
    print("Running full ingestion pipeline with LLM refinement...")
    print("This will use the gateway to refine bounding boxes using GPT-4...")
    
    try:
        # Process with refinement
        pages = ingest_pdf(pdf_path)
        
        # Convert refined results to visualization format
        results = []
        for page in pages:
            page_data = {
                "page": page.page_index + 1,
                "elements": []
            }
            
            for box in page.boxes:
                elem_data = {
                    "type": box.label,
                    "bbox": {
                        "x1": float(box.bbox[0]),
                        "y1": float(box.bbox[1]),
                        "x2": float(box.bbox[2]),
                        "y2": float(box.bbox[3])
                    },
                    "score": float(box.score) if box.score else 1.0
                }
                page_data["elements"].append(elem_data)
            
            results.append(page_data)
        
        # Save refined results
        refined_path = Path("layout_results_refined.json")
        with open(refined_path, "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\nRefined results saved to {refined_path}")
        
        # Create visualizations
        output_dir = Path("layout_visualizations_refined")
        output_dir.mkdir(exist_ok=True)
        
        print("\nGenerating refined visualizations...")
        images = convert_from_path(pdf_path)
        
        for i, (page_data, page_image) in enumerate(zip(results, images)):
            page_num = page_data['page']
            output_path = output_dir / f"page_{page_num:02d}_refined.png"
            visualize_page(page_image, page_data['elements'], page_num, output_path)
        
        # Create comparison visualization for first page
        create_comparison_visualization(results[0], output_dir / "comparison.png")
        
        print(f"\nRefined visualizations saved to {output_dir}/")
        print("\nRefinement complete! The LLM has adjusted bounding boxes for better accuracy.")
        
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        print("\nMake sure the gateway is running with: make up")
        print("And that your OpenAI API key is configured in .env")
        print("Gateway should be running on port 8000")
        import traceback
        traceback.print_exc()

def create_comparison_visualization(refined_page, output_path):
    """Create a side-by-side comparison of original vs refined detection."""
    # Load original results
    with open("layout_results.json", 'r') as f:
        original_results = json.load(f)
    
    original_page = original_results[0]  # First page
    
    # Create comparison chart
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Count elements by type
    def count_by_type(elements):
        counts = {}
        for elem in elements:
            elem_type = elem['type']
            counts[elem_type] = counts.get(elem_type, 0) + 1
        return counts
    
    original_counts = count_by_type(original_page['elements'])
    refined_counts = count_by_type(refined_page['elements'])
    
    # All element types
    all_types = sorted(set(list(original_counts.keys()) + list(refined_counts.keys())))
    
    # Plot original
    ax1.bar(all_types, [original_counts.get(t, 0) for t in all_types], alpha=0.7)
    ax1.set_title('Original Detection', fontsize=14)
    ax1.set_xlabel('Element Type')
    ax1.set_ylabel('Count')
    ax1.grid(axis='y', alpha=0.3)
    
    # Plot refined
    ax2.bar(all_types, [refined_counts.get(t, 0) for t in all_types], alpha=0.7, color='green')
    ax2.set_title('Refined Detection (LLM)', fontsize=14)
    ax2.set_xlabel('Element Type')
    ax2.set_ylabel('Count')
    ax2.grid(axis='y', alpha=0.3)
    
    plt.suptitle('Detection Comparison: Original vs LLM-Refined', fontsize=16)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Saved comparison to {output_path}")

if __name__ == "__main__":
    test_refined_detection()