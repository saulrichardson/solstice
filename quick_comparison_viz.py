#!/usr/bin/env python3
"""Quick visualization comparing raw vs refined layouts using existing data"""

import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pdf2image import convert_from_path
import numpy as np

# Load existing results
with open("layout_results.json", 'r') as f:
    raw_results = json.load(f)

with open("single_page_refinement.json", 'r') as f:
    refinement_data = json.load(f)

# Convert first page to image
images = convert_from_path("Liu et al. (2024).pdf", first_page=1, last_page=1, dpi=150)
page_image = np.array(images[0])

# Create figure with 3 panels
fig = plt.figure(figsize=(30, 10))

# Panel 1: Raw detection with all elements
ax1 = plt.subplot(131)
ax1.imshow(page_image)
ax1.set_title(f"Raw Detection\n{raw_results[0]['page']} - {len(raw_results[0]['elements'])} elements", 
              fontsize=16, pad=20)

# Color map for raw
raw_colors = {
    "Text": "#FF6B6B",
    "Title": "#4ECDC4", 
    "List": "#45B7D1",
    "Table": "#FFA07A",
    "Figure": "#DDA0DD",
}

for i, elem in enumerate(raw_results[0]['elements']):
    bbox = elem['bbox']
    color = raw_colors.get(elem['type'], '#888888')
    
    rect = patches.Rectangle(
        (bbox['x1'], bbox['y1']),
        bbox['x2'] - bbox['x1'],
        bbox['y2'] - bbox['y1'],
        linewidth=2,
        edgecolor=color,
        facecolor='none',
        alpha=0.7
    )
    ax1.add_patch(rect)
    
    # Add small number
    ax1.text(bbox['x1'] + 2, bbox['y1'] + 15, str(i+1), 
            color='white', fontsize=8, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.2', facecolor=color, alpha=0.8))

# Panel 2: Highlight problems
ax2 = plt.subplot(132)
ax2.imshow(page_image)
ax2.set_title("Problems in Raw Detection\nOverlapping & Fragmented Elements", 
              fontsize=16, pad=20, color='red')

# Show overlapping elements in red
problem_areas = [
    {"x1": 600, "y1": 900, "x2": 1560, "y2": 1800, "label": "Multiple overlapping\nList/Text elements"},
    {"x1": 95, "y1": 1820, "x2": 1563, "y2": 2070, "label": "Fragmented text\nacross columns"}
]

for area in problem_areas:
    rect = patches.Rectangle(
        (area['x1'], area['y1']),
        area['x2'] - area['x1'],
        area['y2'] - area['y1'],
        linewidth=3,
        edgecolor='red',
        facecolor='red',
        alpha=0.2,
        linestyle='--'
    )
    ax2.add_patch(rect)
    ax2.text(area['x1'] + 10, area['y1'] + 50, area['label'],
            color='red', fontsize=12, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.8))

# Panel 3: Refined result
ax3 = plt.subplot(133)
ax3.imshow(page_image)
ax3.set_title(f"LLM Refined\n{refinement_data['refined_count']} elements with reading order", 
              fontsize=16, pad=20, color='green')

# Color map for refined
refined_colors = {
    "Text": "#2ECC71",
    "Title": "#E74C3C",
    "List": "#3498DB",
    "Table": "#F39C12",
    "Figure": "#9B59B6",
}

# Show refined boxes
for i, box in enumerate(refinement_data['refined_boxes']):
    bbox = box['bbox']
    color = refined_colors.get(box['label'], '#888888')
    
    rect = patches.Rectangle(
        (bbox[0], bbox[1]),
        bbox[2] - bbox[0],
        bbox[3] - bbox[1],
        linewidth=3,
        edgecolor=color,
        facecolor='none',
        alpha=0.8
    )
    ax3.add_patch(rect)
    
    # Add reading order
    ax3.text(bbox[0] + 5, bbox[1] + 20, f"#{i+1}", 
            color='white', fontsize=12, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor=color, alpha=0.9))
    
    # Add label
    ax3.text(bbox[0] + 5, bbox[1] - 10, box['label'], 
            color=color, fontsize=10, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8))

# Remove axes
for ax in [ax1, ax2, ax3]:
    ax.set_xticks([])
    ax.set_yticks([])

# Add summary text
summary = f"""
Key Improvements:
• Elements reduced: {refinement_data['raw_count']} → {refinement_data['refined_count']} (-{refinement_data['raw_count'] - refinement_data['refined_count']})
• Merged overlapping text/list fragments
• Established logical reading order
• Better semantic classification
"""

fig.text(0.5, 0.02, summary, ha='center', fontsize=14, 
         bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgray', alpha=0.8))

plt.suptitle("Layout Detection: Before & After LLM Refinement", fontsize=20, y=0.98)
plt.tight_layout()
plt.savefig("before_after_comparison.png", dpi=150, bbox_inches='tight')
plt.close()

print("Visualization saved to: before_after_comparison.png")

# Also create a simple stats comparison
print("\nDetailed Statistics:")
print("=" * 50)
print(f"Raw Detection:")
print(f"  Total elements: {refinement_data['raw_count']}")
element_types = {}
for elem in raw_results[0]['elements']:
    element_types[elem['type']] = element_types.get(elem['type'], 0) + 1
for elem_type, count in sorted(element_types.items()):
    print(f"  - {elem_type}: {count}")

print(f"\nRefined Detection:")
print(f"  Total elements: {refinement_data['refined_count']}")
refined_types = {}
for box in refinement_data['refined_boxes']:
    refined_types[box['label']] = refined_types.get(box['label'], 0) + 1
for elem_type, count in sorted(refined_types.items()):
    print(f"  - {elem_type}: {count}")

print(f"\nReduction: {refinement_data['raw_count'] - refinement_data['refined_count']} elements merged")
print(f"Reading order: Established for {refinement_data['refined_count']} elements")