#!/usr/bin/env python3
"""Analyze the green (good) boxes and their text extraction."""

import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image

# Load the content
with open("data/cache/FlublokOnePage/extracted/content.json", 'r') as f:
    data = json.load(f)

# Load image for visualization
img = Image.open("data/cache/FlublokOnePage/pages/page-000.png")

# Get reading order
reading_order = data['reading_order'][0]  # First page

# Create visualization
fig, ax = plt.subplots(1, 1, figsize=(20, 25))
ax.imshow(img)
ax.set_title("Green Boxes with Reading Order Numbers", fontsize=20)

# Create a mapping of block ID to reading order position
id_to_order = {block_id: i+1 for i, block_id in enumerate(reading_order)}

# Analyze green (wide) boxes
print("=== GREEN BOX ANALYSIS ===\n")
green_boxes = []

for block in data['blocks']:
    if block.get('role') == 'Text':
        bbox = block['bbox']
        width = bbox[2] - bbox[0]
        
        # Skip narrow boxes
        if width < 400:
            continue
            
        green_boxes.append(block)
        
        # Draw the box
        height = bbox[3] - bbox[1]
        rect = patches.Rectangle(
            (bbox[0], bbox[1]), width, height,
            linewidth=3, edgecolor='green', facecolor='green', alpha=0.1
        )
        ax.add_patch(rect)
        
        # Add reading order number
        order_num = id_to_order.get(block['id'], '?')
        ax.text(bbox[0] + width/2, bbox[1] + height/2, 
               f"{order_num}", 
               color='white', fontsize=24, weight='bold', ha='center', va='center',
               bbox=dict(boxstyle="circle,pad=0.3", facecolor='blue', alpha=0.8))
        
        # Print analysis
        text = block.get('text', 'NO TEXT')
        text_preview = text[:80] + '...' if len(text) > 80 else text
        print(f"Order #{order_num}: {text_preview}")
        print(f"  Width: {width:.0f}px, Position: ({bbox[0]:.0f}, {bbox[1]:.0f})")
        print()

ax.set_xlim(0, img.width)
ax.set_ylim(img.height, 0)
ax.axis('off')

plt.tight_layout()
plt.savefig("green_boxes_with_order.png", dpi=150, bbox_inches='tight')
print(f"\nTotal green boxes: {len(green_boxes)}")
print("Visualization saved as green_boxes_with_order.png")

# Also create a reading order flow diagram
fig2, ax2 = plt.subplots(1, 1, figsize=(20, 25))
ax2.imshow(img, alpha=0.3)
ax2.set_title("Reading Order Flow", fontsize=20)

# Draw arrows showing reading order
prev_center = None
for i, block_id in enumerate(reading_order):
    # Find the block
    block = next((b for b in data['blocks'] if b['id'] == block_id), None)
    if not block or block.get('role') != 'Text':
        continue
        
    bbox = block['bbox']
    center = ((bbox[0] + bbox[2])/2, (bbox[1] + bbox[3])/2)
    
    # Draw center point
    ax2.plot(center[0], center[1], 'ro', markersize=15)
    ax2.text(center[0], center[1], str(i+1), 
            color='white', fontsize=12, weight='bold', 
            ha='center', va='center')
    
    # Draw arrow from previous
    if prev_center:
        ax2.annotate('', xy=center, xytext=prev_center,
                    arrowprops=dict(arrowstyle='->', color='red', lw=2))
    
    prev_center = center

ax2.set_xlim(0, img.width)
ax2.set_ylim(img.height, 0)
ax2.axis('off')

plt.tight_layout()
plt.savefig("reading_order_flow.png", dpi=150, bbox_inches='tight')
print("Reading order flow saved as reading_order_flow.png")