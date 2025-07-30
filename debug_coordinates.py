"""Debug coordinate mismatches between visualization and HTML viewer."""

import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def debug_coordinates():
    # Load data
    doc_name = "FlublokPI"
    cache_dir = Path("data/cache") / doc_name
    
    # Load page image
    page_img = Image.open(cache_dir / "pages" / "page-000.png")
    print(f"Page image size: {page_img.size}")
    
    # Load final content
    with open(cache_dir / "extracted" / "content.json") as f:
        content = json.load(f)
    
    # Create visualization
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 12))
    
    # Left: Show page image with content.json boxes
    ax1.imshow(page_img)
    ax1.set_title("Content.json boxes on page image")
    ax1.axis('off')
    
    # Right: Show just the boxes
    ax2.set_xlim(0, page_img.width)
    ax2.set_ylim(page_img.height, 0)  # Invert Y axis to match image coordinates
    ax2.set_aspect('equal')
    ax2.set_title("Boxes only (coordinate check)")
    
    # Color map for different roles
    colors = {
        'Text': 'blue',
        'Title': 'red',
        'List': 'green',
        'Table': 'orange',
        'Figure': 'purple'
    }
    
    # Draw boxes from content.json
    page_0_blocks = [b for b in content['blocks'] if b['page_index'] == 0]
    
    for i, block in enumerate(page_0_blocks[:20]):  # First 20 blocks
        bbox = block['bbox']
        x1, y1, x2, y2 = bbox
        width = x2 - x1
        height = y2 - y1
        
        color = colors.get(block['role'], 'gray')
        
        # Draw on image
        rect1 = patches.Rectangle((x1, y1), width, height,
                                 linewidth=2, edgecolor=color,
                                 facecolor='none', alpha=0.7)
        ax1.add_patch(rect1)
        
        # Draw on coordinate plot
        rect2 = patches.Rectangle((x1, y1), width, height,
                                 linewidth=2, edgecolor=color,
                                 facecolor=color, alpha=0.3)
        ax2.add_patch(rect2)
        
        # Add block ID
        ax1.text(x1, y1-5, block['id'][-3:], fontsize=8, color=color)
        ax2.text(x1, y1-5, f"{block['id'][-3:]}: {block['role']}", fontsize=8)
    
    # Add grid to coordinate plot
    ax2.grid(True, alpha=0.3)
    ax2.set_xlabel("X coordinate")
    ax2.set_ylabel("Y coordinate")
    
    # Check if boxes are within image bounds
    out_of_bounds = []
    for block in page_0_blocks:
        bbox = block['bbox']
        if bbox[0] < 0 or bbox[1] < 0 or bbox[2] > page_img.width or bbox[3] > page_img.height:
            out_of_bounds.append(block['id'])
    
    if out_of_bounds:
        print(f"\\nWARNING: {len(out_of_bounds)} boxes out of image bounds!")
    else:
        print("\\nAll boxes within image bounds.")
    
    # Save the debug visualization
    plt.tight_layout()
    plt.savefig("debug_coordinates.png", dpi=150, bbox_inches='tight')
    print(f"\\nDebug visualization saved to debug_coordinates.png")
    
    # Now let's check the reading order
    if 'reading_order' in content and len(content['reading_order']) > 0:
        reading_order = content['reading_order'][0]
        print(f"\\nReading order for page 0: {len(reading_order)} items")
        
        # Create a mapping of block IDs to blocks
        blocks_by_id = {b['id']: b for b in page_0_blocks}
        
        # Check if all reading order IDs exist
        missing = [rid for rid in reading_order if rid not in blocks_by_id]
        if missing:
            print(f"Missing blocks in reading order: {missing}")
        else:
            print("All reading order IDs found in blocks.")
            
            # Show first few blocks in reading order
            print("\\nFirst 5 blocks in reading order:")
            for i, block_id in enumerate(reading_order[:5]):
                block = blocks_by_id[block_id]
                print(f"  {i+1}. {block_id}: {block['role']} at {block['bbox']}")

if __name__ == "__main__":
    debug_coordinates()