"""Simple layout viewer that shows the final merged and ordered layout."""

import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from pdf2image import convert_from_path
from typing import Optional, List


def create_simple_layout_view(
    catalog_dir: Path,
    pdf_path: Path,
    output_dir: Optional[Path] = None,
    pages: Optional[List[int]] = None
):
    """Create simple visualization of final layout after merging and ordering.
    
    Args:
        catalog_dir: Directory containing the catalog
        pdf_path: Path to original PDF
        output_dir: Output directory (defaults to catalog_dir/layout_view)
        pages: Specific pages to visualize (None = all)
    """
    # Setup output
    if output_dir is None:
        output_dir = catalog_dir / "layout_view"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load catalog
    with open(catalog_dir / "catalog.json") as f:
        catalog = json.load(f)
    
    # Determine pages
    if pages is None:
        total_pages = catalog['metadata']['total_pages']
        pages = list(range(1, total_pages + 1))
    
    # Element type colors
    colors = {
        'text': '#3498db',      # Blue
        'title': '#e74c3c',     # Red  
        'list': '#9b59b6',      # Purple
        'figure': '#2ecc71',    # Green
        'table': '#f39c12',     # Orange
    }
    
    # Try to load font
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
        order_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
    except:
        font = ImageFont.load_default()
        order_font = font
    
    print(f"Creating simple layout views for {len(pages)} pages...")
    
    for page_num in pages:
        # Convert PDF page to image
        images = convert_from_path(
            pdf_path,
            first_page=page_num,
            last_page=page_num,
            dpi=200
        )
        
        if not images:
            continue
            
        page_image = images[0]
        draw = ImageDraw.Draw(page_image)
        
        # Get elements for this page
        page_elements = [
            e for e in catalog['elements']
            if e['page_num'] == page_num
        ]
        
        # Sort by reading order
        page_elements.sort(key=lambda x: x['reading_order'])
        
        # Draw each element
        scale_factor = 200 / 72.0  # DPI to points conversion
        
        for elem in page_elements:
            # Get bbox and convert to pixels
            bbox = elem['bbox']
            pixel_bbox = [
                int(bbox[0] * scale_factor),
                int(bbox[1] * scale_factor),
                int(bbox[2] * scale_factor),
                int(bbox[3] * scale_factor)
            ]
            
            # Get color
            elem_type = elem.get('element_type', elem.get('type', 'unknown'))
            color = colors.get(elem_type, '#95a5a6')
            
            # Draw rectangle with thicker line for text elements
            width = 4 if elem.get('content') else 3
            draw.rectangle(pixel_bbox, outline=color, width=width)
            
            # Draw reading order number in center
            order_num = str(elem['reading_order'])
            center_x = (pixel_bbox[0] + pixel_bbox[2]) // 2
            center_y = (pixel_bbox[1] + pixel_bbox[3]) // 2
            
            # Get text size
            bbox_obj = draw.textbbox((0, 0), order_num, font=order_font)
            text_width = bbox_obj[2] - bbox_obj[0]
            text_height = bbox_obj[3] - bbox_obj[1]
            
            # White background circle
            radius = max(text_width, text_height) // 2 + 10
            draw.ellipse(
                [center_x - radius, center_y - radius,
                 center_x + radius, center_y + radius],
                fill='white',
                outline=color,
                width=3
            )
            
            # Draw number
            draw.text(
                (center_x - text_width // 2, center_y - text_height // 2),
                order_num,
                fill=color,
                font=order_font
            )
        
        # Add page info
        info_text = f"Page {page_num} - {len(page_elements)} elements"
        draw.text((20, 20), info_text, fill='black', font=font)
        
        # Count by type
        type_counts = {}
        for elem in page_elements:
            elem_type = elem.get('element_type', elem.get('type', 'unknown'))
            type_counts[elem_type] = type_counts.get(elem_type, 0) + 1
        
        # Show counts
        y_offset = 60
        for elem_type, count in sorted(type_counts.items()):
            color = colors.get(elem_type, '#95a5a6')
            draw.rectangle([20, y_offset, 40, y_offset + 20], fill=color)
            draw.text((50, y_offset), f"{elem_type}: {count}", fill='black', font=font)
            y_offset += 30
        
        # Save
        output_path = output_dir / f"page_{page_num:02d}_layout.png"
        page_image.save(output_path)
        print(f"  Saved: {output_path}")
    
    print(f"\nLayout views saved to: {output_dir}")
    return output_dir