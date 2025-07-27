#!/usr/bin/env python3
"""
Visualize layout detection results on PDF pages
"""
import json
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pdf2image import convert_from_path
from PIL import Image
import numpy as np

# Color scheme for different layout elements
ELEMENT_COLORS = {
    "Text": "#3498db",      # Blue
    "Title": "#e74c3c",     # Red
    "List": "#2ecc71",      # Green
    "Table": "#f39c12",     # Orange
    "Figure": "#9b59b6",    # Purple
}

def load_results(json_path: Path) -> dict:
    """Load layout detection results from JSON"""
    with open(json_path, 'r') as f:
        return json.load(f)

def visualize_page(page_image: Image.Image, elements: list, page_num: int, output_path: Path):
    """Visualize layout elements on a single page"""
    # Convert PIL image to numpy array
    img_array = np.array(page_image)
    
    # Create figure and axis
    fig, ax = plt.subplots(figsize=(12, 16))
    ax.imshow(img_array)
    
    # Add bounding boxes for each element
    for elem in elements:
        bbox = elem['bbox']
        label = elem['type']
        score = elem['score']
        
        # Create rectangle
        rect = patches.Rectangle(
            (bbox['x1'], bbox['y1']),
            bbox['x2'] - bbox['x1'],
            bbox['y2'] - bbox['y1'],
            linewidth=2,
            edgecolor=ELEMENT_COLORS.get(label, '#95a5a6'),
            facecolor='none',
            alpha=0.8
        )
        ax.add_patch(rect)
        
        # Add label with confidence score
        label_text = f"{label} ({score:.2f})"
        ax.text(
            bbox['x1'], 
            bbox['y1'] - 5,
            label_text,
            color=ELEMENT_COLORS.get(label, '#95a5a6'),
            fontsize=10,
            fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7)
        )
    
    # Remove axis ticks
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(f"Page {page_num} - {len(elements)} elements detected", fontsize=14, pad=20)
    
    # Save figure
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Saved visualization for page {page_num} to {output_path}")

def create_summary_visualization(results: list, output_path: Path):
    """Create a summary visualization showing element distribution"""
    # Count elements by type
    element_counts = {}
    for page in results:
        for elem in page['elements']:
            label = elem['type']
            element_counts[label] = element_counts.get(label, 0) + 1
    
    # Create bar chart
    fig, ax = plt.subplots(figsize=(10, 6))
    labels = list(element_counts.keys())
    counts = list(element_counts.values())
    colors = [ELEMENT_COLORS.get(label, '#95a5a6') for label in labels]
    
    bars = ax.bar(labels, counts, color=colors, alpha=0.8)
    
    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}',
                ha='center', va='bottom')
    
    ax.set_xlabel('Element Type', fontsize=12)
    ax.set_ylabel('Count', fontsize=12)
    ax.set_title('Distribution of Detected Elements', fontsize=14)
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Saved summary visualization to {output_path}")

def main():
    # Load results
    results_path = Path("layout_results.json")
    if not results_path.exists():
        print("Error: layout_results.json not found. Run test_layout_parser.py first.")
        return
    
    results = load_results(results_path)
    
    # Convert PDF to images
    pdf_path = Path("Liu et al. (2024).pdf")
    if not pdf_path.exists():
        print(f"Error: PDF file {pdf_path} not found")
        return
    
    print("Converting PDF to images...")
    # Use default DPI to match layout detection pipeline
    images = convert_from_path(pdf_path)
    
    # Create output directory
    output_dir = Path("layout_visualizations")
    output_dir.mkdir(exist_ok=True)
    
    # Visualize each page
    for i, (page_data, page_image) in enumerate(zip(results, images)):
        page_num = page_data['page']
        output_path = output_dir / f"page_{page_num:02d}.png"
        visualize_page(page_image, page_data['elements'], page_num, output_path)
    
    # Create summary visualization
    summary_path = output_dir / "summary.png"
    create_summary_visualization(results, summary_path)
    
    print(f"\nVisualization complete! Check the '{output_dir}' directory for results.")
    print(f"- Individual page visualizations: page_01.png through page_{len(images):02d}.png")
    print("- Summary statistics: summary.png")

if __name__ == "__main__":
    main()