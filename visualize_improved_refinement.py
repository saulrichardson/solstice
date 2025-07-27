#!/usr/bin/env python3
"""Visualize the improved refinement results"""

import json
from pdf2image import convert_from_path
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

# Load results
with open("improved_refinement_results.json", 'r') as f:
    improved = json.load(f)

with open("layout_results.json", 'r') as f:
    raw_results = json.load(f)

# Convert page
images = convert_from_path("Liu et al. (2024).pdf", first_page=1, last_page=1, dpi=150)
page_image = np.array(images[0])

# Create comparison figure
fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(24, 14))

# Panel 1: Original raw detection
ax1.imshow(page_image)
ax1.set_title(f"Raw Detection\n{raw_results[0]['page']} - {len(raw_results[0]['elements'])} elements", fontsize=14)

# Show the problematic list boxes
for elem in raw_results[0]['elements']:
    if elem['type'] == 'List':
        bbox = elem['bbox']
        rect = patches.Rectangle(
            (bbox['x1'], bbox['y1']),
            bbox['x2'] - bbox['x1'],
            bbox['y2'] - bbox['y1'],
            linewidth=2,
            edgecolor='blue',
            facecolor='blue',
            alpha=0.1
        )
        ax1.add_patch(rect)
        ax1.text(bbox['x1'], bbox['y1'] - 10, f"List ({elem['score']:.2f})", 
                color='blue', fontsize=10, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))

# Panel 2: Original refinement (problematic)
ax2.imshow(page_image)
ax2.set_title("Original Refinement\n(One large List box)", fontsize=14, color='red')

# Show the problematic merged list
with open("single_page_refinement.json", 'r') as f:
    original_refinement = json.load(f)

for box in original_refinement['refined_boxes']:
    if box['label'] == 'List':
        bbox = box['bbox']
        rect = patches.Rectangle(
            (bbox[0], bbox[1]),
            bbox[2] - bbox[0],
            bbox[3] - bbox[1],
            linewidth=3,
            edgecolor='red',
            facecolor='none',
            alpha=0.8
        )
        ax2.add_patch(rect)
        ax2.text(bbox[0] + 200, bbox[1] + 400, "PROBLEM:\nOne huge List box\ncovers entire region", 
                color='red', fontsize=14, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.9))

# Panel 3: Improved refinement
ax3.imshow(page_image)
ax3.set_title(f"Improved Refinement\n{improved['refined_count']} elements (6 ListItems)", 
              fontsize=14, color='green')

# Color scheme
colors = {
    "Text": "#2ECC71",
    "Title": "#E74C3C",
    "ListItem": "#3498DB",  # Blue for list items
}

# Show improved boxes
for i, box in enumerate(improved['boxes']):
    bbox = box['bbox']
    color = colors.get(box['label'], '#888888')
    
    rect = patches.Rectangle(
        (bbox[0], bbox[1]),
        bbox[2] - bbox[0],
        bbox[3] - bbox[1],
        linewidth=2,
        edgecolor=color,
        facecolor='none',
        alpha=0.8
    )
    ax3.add_patch(rect)
    
    # Add label for ListItems
    if box['label'] == 'ListItem':
        # Find position in reading order
        try:
            order_idx = improved['reading_order'].index(box['id']) + 1
            label = f"{order_idx}. ListItem"
        except:
            label = "ListItem"
        
        ax3.text(bbox[0] - 50, bbox[1] + 20, label, 
                color=color, fontsize=9, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8))

# Remove axes
for ax in [ax1, ax2, ax3]:
    ax.set_xticks([])
    ax.set_yticks([])

# Add legend
legend_elements = [
    patches.Patch(color=colors['Title'], label='Title'),
    patches.Patch(color=colors['Text'], label='Text'),
    patches.Patch(color=colors['ListItem'], label='ListItem')
]
ax3.legend(handles=legend_elements, loc='lower right', fontsize=12)

plt.suptitle("Layout Refinement Comparison: Fixing List Detection", fontsize=18, y=0.98)
plt.tight_layout()
plt.savefig("improved_refinement_comparison.png", dpi=150, bbox_inches='tight')
plt.close()

print("Visualization saved to improved_refinement_comparison.png")

# Print statistics
print("\nImprovement Summary:")
print(f"Original raw: {len(raw_results[0]['elements'])} elements (3 overlapping Lists)")
print(f"Original refinement: 6 elements (1 huge List box)")
print(f"Improved refinement: {improved['refined_count']} elements with proper structure:")
for label, count in improved['label_distribution'].items():
    print(f"  - {label}: {count}")