"""Visualization utilities for layout detection results."""

from __future__ import annotations

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Rectangle
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from PIL import Image

from .document import Document, Block
from .storage import pages_dir, stage_dir


# Color map for different element types
COLOR_MAP = {
    'Text': 'blue',
    'Title': 'red', 
    'List': 'green',
    'Table': 'purple',
    'Figure': 'orange',
    'Unknown': 'gray'
}


def visualize_page_layout(
    page_image: Image.Image,
    blocks: List[Block],
    reading_order: Optional[List[str]] = None,
    title: str = "Layout Detection Results",
    save_path: Optional[Path] = None,
    show_labels: bool = True,
    show_reading_order: bool = True,
    dpi: int = 150
) -> None:
    """Visualize bounding boxes on a single page.
    
    Args:
        page_image: PIL Image of the page
        blocks: List of Block objects to visualize
        reading_order: Optional list of block IDs in reading order
        title: Title for the plot
        save_path: Optional path to save the visualization
        show_labels: Whether to show element type labels
        show_reading_order: Whether to show reading order numbers
        dpi: DPI for saving the figure
    """
    fig, ax = plt.subplots(1, 1, figsize=(12, 16))
    
    # Display the page image
    ax.imshow(page_image)
    ax.set_title(title, fontsize=16)
    ax.axis('off')
    
    # Create reading order map if provided
    reading_order_map = {}
    if reading_order and show_reading_order:
        reading_order_map = {block_id: idx + 1 for idx, block_id in enumerate(reading_order)}
    
    # Draw bounding boxes
    for block in blocks:
        x1, y1, x2, y2 = block.bbox
        width = x2 - x1
        height = y2 - y1
        
        # Get color based on element type
        color = COLOR_MAP.get(block.role, 'gray')
        
        # Draw rectangle
        rect = Rectangle(
            (x1, y1), width, height,
            linewidth=2,
            edgecolor=color,
            facecolor='none',
            alpha=0.8
        )
        ax.add_patch(rect)
        
        # Add label if requested
        if show_labels:
            label_text = block.role
            if block.id in reading_order_map and show_reading_order:
                label_text = f"{reading_order_map[block.id]}. {label_text}"
            
            # Add label with background
            ax.text(
                x1 + 5, y1 + 5, label_text,
                fontsize=10,
                color='white',
                bbox=dict(boxstyle="round,pad=0.3", facecolor=color, alpha=0.7),
                verticalalignment='top'
            )
    
    # Add statistics
    stats_text = f"Total elements: {len(blocks)}"
    if reading_order:
        stats_text += f"\nReading order: {len(reading_order)} elements"
    
    ax.text(
        0.02, 0.98, stats_text,
        transform=ax.transAxes,
        verticalalignment='top',
        fontsize=12,
        bbox=dict(boxstyle='round', facecolor='white', alpha=0.8)
    )
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=dpi, bbox_inches='tight')
        plt.close()
    else:
        plt.show()


def visualize_document(
    document: Document,
    pdf_path: Path | str,
    output_dir: Optional[Path] = None,
    pages_to_show: Optional[List[int]] = None,
    show_labels: bool = True,
    show_reading_order: bool = True
) -> List[Path]:
    """Visualize all pages of a document with bounding boxes.
    
    Args:
        document: Document object with blocks and reading order
        pdf_path: Path to the original PDF (for loading images)
        output_dir: Directory to save visualizations (if None, uses viz stage dir)
        pages_to_show: List of page indices to visualize (if None, shows all)
        show_labels: Whether to show element type labels
        show_reading_order: Whether to show reading order numbers
        
    Returns:
        List of paths to saved visualization files
    """
    # Determine output directory
    if output_dir is None:
        output_dir = stage_dir("visualizations", pdf_path)
    else:
        output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load page images
    page_images_dir = pages_dir(pdf_path)
    page_images = sorted(page_images_dir.glob("page-*.png"))
    
    if not page_images:
        raise FileNotFoundError(f"No page images found in {page_images_dir}")
    
    # Determine which pages to visualize
    total_pages = len(page_images)
    if pages_to_show is None:
        pages_to_show = list(range(total_pages))
    
    saved_paths = []
    
    for page_idx in pages_to_show:
        if page_idx >= total_pages:
            continue
            
        # Load page image
        page_image = Image.open(page_images[page_idx])
        
        # Get blocks for this page
        page_blocks = [b for b in document.blocks if b.page_index == page_idx]
        
        # Get reading order for this page
        page_reading_order = None
        if document.reading_order and page_idx < len(document.reading_order):
            page_reading_order = document.reading_order[page_idx]
        
        # Create visualization
        save_path = output_dir / f"page_{page_idx + 1:03d}_layout.png"
        visualize_page_layout(
            page_image,
            page_blocks,
            page_reading_order,
            title=f"Page {page_idx + 1} - Layout Detection",
            save_path=save_path,
            show_labels=show_labels,
            show_reading_order=show_reading_order
        )
        
        saved_paths.append(save_path)
    
    # Create summary visualization showing all pages in a grid
    if len(saved_paths) > 1:
        create_summary_grid(saved_paths, output_dir / "all_pages_summary.png")
        saved_paths.append(output_dir / "all_pages_summary.png")
    
    return saved_paths


def create_summary_grid(
    image_paths: List[Path],
    output_path: Path,
    max_cols: int = 3,
    thumbnail_size: Tuple[int, int] = (400, 500)
) -> None:
    """Create a grid view of multiple page visualizations."""
    n_images = len(image_paths)
    n_cols = min(n_images, max_cols)
    n_rows = (n_images + n_cols - 1) // n_cols
    
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(n_cols * 4, n_rows * 5))
    
    # Ensure axes is always a 2D array
    if n_rows == 1:
        axes = axes.reshape(1, -1)
    elif n_cols == 1:
        axes = axes.reshape(-1, 1)
    
    for idx, img_path in enumerate(image_paths):
        row = idx // n_cols
        col = idx % n_cols
        
        # Load and display image
        img = Image.open(img_path)
        img.thumbnail(thumbnail_size)
        
        axes[row, col].imshow(img)
        axes[row, col].set_title(f"Page {idx + 1}", fontsize=12)
        axes[row, col].axis('off')
    
    # Hide empty subplots
    for idx in range(n_images, n_rows * n_cols):
        row = idx // n_cols
        col = idx % n_cols
        axes[row, col].axis('off')
    
    plt.suptitle("Document Layout Overview", fontsize=16)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()


# Convenience function to visualize from pipeline
def visualize_pipeline_results(
    pdf_path: Path | str,
    pages_to_show: Optional[List[int]] = None,
    show_labels: bool = True,
    show_reading_order: bool = True
) -> List[Path]:
    """Visualize results from the pipeline for a processed PDF.
    
    Args:
        pdf_path: Path to the PDF that was processed
        pages_to_show: List of page indices to visualize (if None, shows all)
        show_labels: Whether to show element type labels
        show_reading_order: Whether to show reading order numbers
        
    Returns:
        List of paths to saved visualization files
    """
    from .storage import final_doc_path
    from .document import Document
    
    # Load the processed document
    doc_path = final_doc_path(pdf_path)
    if not doc_path.exists():
        raise FileNotFoundError(f"No processed document found for {pdf_path}")
    
    document = Document.load(doc_path)
    
    # Create visualizations
    return visualize_document(
        document,
        pdf_path,
        pages_to_show=pages_to_show,
        show_labels=show_labels,
        show_reading_order=show_reading_order
    )