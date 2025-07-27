#!/usr/bin/env python3
"""Debug the coordinate system to understand the layout issue"""

import json
from pdf2image import convert_from_path
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

# Load the refined results
with open("single_page_refinement.json", 'r') as f:
    data = json.load(f)

# Convert page
images = convert_from_path("Liu et al. (2024).pdf", first_page=1, last_page=1)
page_image = np.array(images[0])

print(f"Image dimensions: {page_image.shape}")
print(f"Width: {page_image.shape[1]}, Height: {page_image.shape[0]}")

# Create a detailed view
fig, ax = plt.subplots(figsize=(12, 16))
ax.imshow(page_image)

# Focus on the List element that seems problematic
print("\nAnalyzing List element coordinates:")
for box in data['refined_boxes']:
    if box['label'] == 'List':
        bbox = box['bbox']
        print(f"List bbox: x1={bbox[0]:.1f}, y1={bbox[1]:.1f}, x2={bbox[2]:.1f}, y2={bbox[3]:.1f}")
        print(f"Width: {bbox[2] - bbox[0]:.1f}, Height: {bbox[3] - bbox[1]:.1f}")
        
        # Draw the box
        rect = patches.Rectangle(
            (bbox[0], bbox[1]),
            bbox[2] - bbox[0],
            bbox[3] - bbox[1],
            linewidth=3,
            edgecolor='blue',
            facecolor='none',
            alpha=0.8
        )
        ax.add_patch(rect)
        
        # Add coordinate labels
        ax.text(bbox[0], bbox[1] - 20, f"({bbox[0]:.0f}, {bbox[1]:.0f})", 
                color='blue', fontsize=10, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white'))
        ax.text(bbox[2], bbox[3] + 10, f"({bbox[2]:.0f}, {bbox[3]:.0f})", 
                color='blue', fontsize=10, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white'))

# Also show the original List detections
print("\nOriginal List elements from raw detection:")
with open("layout_results.json", 'r') as f:
    raw_results = json.load(f)

for elem in raw_results[0]['elements']:
    if elem['type'] == 'List':
        bbox = elem['bbox']
        print(f"Raw List: x1={bbox['x1']:.1f}, y1={bbox['y1']:.1f}, x2={bbox['x2']:.1f}, y2={bbox['y2']:.1f}")
        
        # Draw with dashed line
        rect = patches.Rectangle(
            (bbox['x1'], bbox['y1']),
            bbox['x2'] - bbox['x1'],
            bbox['y2'] - bbox['y1'],
            linewidth=2,
            edgecolor='red',
            facecolor='none',
            alpha=0.5,
            linestyle='--'
        )
        ax.add_patch(rect)

# Draw grid lines at key coordinates
ax.axvline(x=600, color='gray', linestyle=':', alpha=0.5)
ax.axvline(x=1557, color='gray', linestyle=':', alpha=0.5)
ax.axhline(y=924, color='gray', linestyle=':', alpha=0.5)
ax.axhline(y=1763, color='gray', linestyle=':', alpha=0.5)

ax.set_title("Coordinate Debug View - Blue=Refined List, Red Dashed=Original Lists", fontsize=14)
ax.set_xlabel("X coordinate")
ax.set_ylabel("Y coordinate")

plt.tight_layout()
plt.savefig("coordinate_debug.png", dpi=150, bbox_inches='tight')
plt.close()

print("\nDebug visualization saved to coordinate_debug.png")

# Let's also check what text might be in that region by looking at nearby Text elements
print("\nNearby Text elements in the same vertical region (y=900-1800):")
for elem in raw_results[0]['elements']:
    if elem['type'] == 'Text':
        bbox = elem['bbox']
        if 900 < bbox['y1'] < 1800:
            print(f"Text at ({bbox['x1']:.0f}, {bbox['y1']:.0f}): width={bbox['x2']-bbox['x1']:.0f}, height={bbox['y2']-bbox['y1']:.0f}")