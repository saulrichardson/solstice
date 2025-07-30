#!/usr/bin/env python3
"""Test and visualize the clustering-based reading order."""

import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image
from matplotlib.patches import FancyBboxPatch

# Load the content
with open("data/cache/FlublokOnePage/extracted/content.json", 'r') as f:
    data = json.load(f)

# Load image
img = Image.open("data/cache/FlublokOnePage/pages/page-000.png")

# Get reading order
reading_order = data['reading_order'][0]
id_to_block = {b['id']: b for b in data['blocks']}

# Create visualization
fig, ax = plt.subplots(1, 1, figsize=(16, 20))
ax.imshow(img, alpha=0.5)
ax.set_title("Clustering-Based Reading Order", fontsize=24)

# Define colors for visual feature boxes (based on marketing slide design)
feature_colors = {
    'exact_strain': '#4ECDC4',  # Turquoise
    'antigen_3x': '#FFB6C1',    # Light pink
    'mutations': '#87CEEB',     # Sky blue  
    'cross_protection': '#F0E68C',  # Khaki
    'title': '#DDA0DD',         # Plum
    'footer': '#E0E0E0'         # Gray
}

# Manually identify feature boxes based on content
cluster_assignments = {}
for i, block_id in enumerate(reading_order):
    if block_id not in id_to_block:
        continue
    
    block = id_to_block[block_id]
    text = block.get('text', '').lower()
    
    # Assign feature based on content
    if i == 0:  # First block is title
        color = feature_colors['title']
    elif 'exact strain' in text:
        color = feature_colors['exact_strain']
    elif '3x' in text or 'antigen' in text or 'hemagglutinin' in text:
        color = feature_colors['antigen_3x']
    elif 'mutation' in text:
        color = feature_colors['mutations']
    elif 'cross' in text and 'protection' in text:
        color = feature_colors['cross_protection']
    elif block['bbox'][1] > 2400:  # Footer area
        color = feature_colors['footer']
    else:
        # Assign based on position in feature boxes
        y_center = (block['bbox'][1] + block['bbox'][3]) / 2
        x_center = (block['bbox'][0] + block['bbox'][2]) / 2
        
        if y_center < 1100 and x_center < 1500:
            color = feature_colors['exact_strain']
        elif y_center < 1100 and x_center > 2000:
            color = feature_colors['antigen_3x']
        elif y_center > 1200 and y_center < 1700 and x_center < 1500:
            color = feature_colors['cross_protection']
        elif y_center > 1700 and y_center < 2300 and x_center < 1500:
            color = feature_colors['mutations']
        else:
            color = '#CCCCCC'  # Default gray
    
    cluster_assignments[block_id] = color

# Draw boxes and numbers
for i, block_id in enumerate(reading_order):
    if block_id not in id_to_block:
        continue
    
    block = id_to_block[block_id]
    bbox = block['bbox']
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    
    # Get cluster color
    color = cluster_assignments.get(block_id, '#CCCCCC')
    
    # Draw fancy box
    fancy_box = FancyBboxPatch(
        (bbox[0], bbox[1]), width, height,
        boxstyle="round,pad=10",
        facecolor=color,
        edgecolor='black',
        alpha=0.3,
        linewidth=2
    )
    ax.add_patch(fancy_box)
    
    # Add reading order number
    center = ((bbox[0] + bbox[2])/2, (bbox[1] + bbox[3])/2)
    ax.text(center[0], center[1], str(i+1), 
           color='white', fontsize=20, weight='bold',
           ha='center', va='center',
           bbox=dict(boxstyle="circle,pad=0.3", facecolor='black', alpha=0.8))
    
    # Add text preview for debugging
    if block.get('text'):
        text_preview = block['text'][:30] + '...' if len(block['text']) > 30 else block['text']
        ax.text(bbox[0], bbox[1] - 20, f"#{i+1}: {text_preview}",
               fontsize=8, color='black', weight='bold',
               bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.9))

ax.set_xlim(0, img.width)
ax.set_ylim(img.height, 0)
ax.axis('off')

plt.tight_layout()
plt.savefig("clustering_reading_order.png", dpi=150, bbox_inches='tight')
print("Saved clustering_reading_order.png")

# Print the reading order sequence
print("\n=== READING ORDER SEQUENCE ===")
for i, block_id in enumerate(reading_order):
    if block_id in id_to_block:
        block = id_to_block[block_id]
        role = block.get('role', 'Unknown')
        text_preview = ''
        if block.get('text'):
            text_preview = block['text'][:60] + '...' if len(block['text']) > 60 else block['text']
        print(f"{i+1}. [{role}] {text_preview}")