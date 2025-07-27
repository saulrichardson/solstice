#!/usr/bin/env python3
"""Visualize with proper coordinate scaling"""

import json
from pdf2image import convert_from_path
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

# Load results
with open("layout_results.json", 'r') as f:
    results = json.load(f)

with open("improved_refinement_results.json", 'r') as f:
    refined = json.load(f)

# Convert at different DPIs to understand scaling
pdf_path = "Liu et al. (2024).pdf"
img_200dpi = convert_from_path(pdf_path, first_page=1, last_page=1, dpi=200)[0]
img_150dpi = convert_from_path(pdf_path, first_page=1, last_page=1, dpi=150)[0]

# Calculate scaling factors
scale_x = img_150dpi.size[0] / img_200dpi.size[0]  # 1241/1654 = 0.75
scale_y = img_150dpi.size[1] / img_200dpi.size[1]  # 1648/2197 = 0.75

print(f"Scaling factors: x={scale_x:.3f}, y={scale_y:.3f}")

# Create visualization with proper scaling
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 12))

# Left: Raw detection (scaled)
ax1.imshow(img_150dpi)
ax1.set_title(f"Raw Detection (properly scaled)\n{len(results[0]['elements'])} elements", fontsize=14)

for elem in results[0]['elements']:
    bbox = elem['bbox']
    # Scale coordinates to match 150 DPI image
    x1_scaled = bbox['x1'] * scale_x
    y1_scaled = bbox['y1'] * scale_y
    x2_scaled = bbox['x2'] * scale_x
    y2_scaled = bbox['y2'] * scale_y
    
    color = {'Text': '#FF6B6B', 'Title': '#4ECDC4', 'List': '#45B7D1'}.get(elem['type'], '#888')
    
    rect = patches.Rectangle(
        (x1_scaled, y1_scaled),
        x2_scaled - x1_scaled,
        y2_scaled - y1_scaled,
        linewidth=2,
        edgecolor=color,
        facecolor='none',
        alpha=0.8
    )
    ax1.add_patch(rect)

# Right: Improved refinement (scaled)
ax2.imshow(img_150dpi)
ax2.set_title(f"Improved Refinement (properly scaled)\n{refined['refined_count']} elements", fontsize=14)

colors = {
    "Text": "#2ECC71",
    "Title": "#E74C3C",
    "ListItem": "#3498DB",
}

for i, box in enumerate(refined['boxes']):
    bbox = box['bbox']
    # Scale coordinates
    x1_scaled = bbox[0] * scale_x
    y1_scaled = bbox[1] * scale_y
    x2_scaled = bbox[2] * scale_x
    y2_scaled = bbox[3] * scale_y
    
    color = colors.get(box['label'], '#888')
    
    rect = patches.Rectangle(
        (x1_scaled, y1_scaled),
        x2_scaled - x1_scaled,
        y2_scaled - y1_scaled,
        linewidth=2,
        edgecolor=color,
        facecolor='none',
        alpha=0.8
    )
    ax2.add_patch(rect)
    
    # Add labels for ListItems
    if box['label'] == 'ListItem':
        ax2.text(x1_scaled - 40, y1_scaled + 15, f"#{i+1}", 
                color=color, fontsize=9, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8))

# Remove axes
for ax in [ax1, ax2]:
    ax.set_xticks([])
    ax.set_yticks([])

# Add legend
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor=colors['Title'], label='Title'),
    Patch(facecolor=colors['Text'], label='Text'), 
    Patch(facecolor=colors['ListItem'], label='ListItem')
]
ax2.legend(handles=legend_elements, loc='lower right')

plt.suptitle("Properly Scaled Layout Detection Results", fontsize=16)
plt.tight_layout()
plt.savefig("properly_scaled_visualization.png", dpi=150, bbox_inches='tight')
plt.close()

print("Properly scaled visualization saved to properly_scaled_visualization.png")
print("\nNote: The model detects at 200 DPI but visualizations at 150 DPI need 0.75x scaling")