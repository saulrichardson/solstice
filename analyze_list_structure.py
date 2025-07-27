#!/usr/bin/env python3
"""Analyze the actual structure of the list region"""

import json
from pdf2image import convert_from_path
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

# Load results
with open("layout_results.json", 'r') as f:
    raw_results = json.load(f)

# Convert page with higher DPI for better detail
images = convert_from_path("Liu et al. (2024).pdf", first_page=1, last_page=1, dpi=200)
page_image = np.array(images[0])

# Create figure
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 14))

# Left: Show ALL elements in the list region
ax1.imshow(page_image)
ax1.set_title("All Elements in List Region (x=600-1560, y=720-1763)", fontsize=14)

# Define the problematic list region
list_region_x1, list_region_x2 = 600, 1560
list_region_y1, list_region_y2 = 720, 1763

# Highlight the list region
list_rect = patches.Rectangle(
    (list_region_x1, list_region_y1),
    list_region_x2 - list_region_x1,
    list_region_y2 - list_region_y1,
    linewidth=3,
    edgecolor='blue',
    facecolor='blue',
    alpha=0.1,
    label='List Region'
)
ax1.add_patch(list_rect)

# Show all elements within this region
elements_in_region = []
for elem in raw_results[0]['elements']:
    bbox = elem['bbox']
    # Check if element is within or overlaps with list region
    if (bbox['x1'] < list_region_x2 and bbox['x2'] > list_region_x1 and
        bbox['y1'] < list_region_y2 and bbox['y2'] > list_region_y1):
        elements_in_region.append(elem)
        
        color = 'red' if elem['type'] == 'Text' else 'green' if elem['type'] == 'List' else 'orange'
        rect = patches.Rectangle(
            (bbox['x1'], bbox['y1']),
            bbox['x2'] - bbox['x1'],
            bbox['y2'] - bbox['y1'],
            linewidth=2,
            edgecolor=color,
            facecolor='none',
            alpha=0.8
        )
        ax1.add_patch(rect)
        
        # Label
        ax1.text(bbox['x1'], bbox['y1'] - 5, elem['type'], 
                color=color, fontsize=8, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7))

# Right: Zoom into the list region
ax2.imshow(page_image[list_region_y1:list_region_y2, list_region_x1:list_region_x2])
ax2.set_title("Zoomed List Region - Understanding the Layout", fontsize=14)

# Remove axes ticks
for ax in [ax1, ax2]:
    ax.set_xticks([])
    ax.set_yticks([])

plt.tight_layout()
plt.savefig("list_structure_analysis.png", dpi=150, bbox_inches='tight')
plt.close()

# Print analysis
print(f"Analysis of List Region ({list_region_x1}-{list_region_x2}, {list_region_y1}-{list_region_y2}):")
print(f"Found {len(elements_in_region)} elements in this region:")
print("-" * 60)

# Sort by y-coordinate to understand vertical layout
elements_in_region.sort(key=lambda e: e['bbox']['y1'])

for i, elem in enumerate(elements_in_region):
    bbox = elem['bbox']
    print(f"{i+1}. {elem['type']} at y={bbox['y1']:.0f}-{bbox['y2']:.0f}, x={bbox['x1']:.0f}-{bbox['x2']:.0f}")
    print(f"   Confidence: {elem['score']:.3f}")

print("\nPROBLEM IDENTIFIED:")
print("The 'List' detection is covering a large region but doesn't properly")
print("identify individual list items. The Text elements within are the actual")
print("list items that should be properly structured.")
print("\nThe LLM refinement should have:")
print("1. Identified these Text elements as list items")
print("2. Created proper bounding boxes for each item")
print("3. Maintained the list structure with proper hierarchy")

# Save detailed analysis
analysis = {
    "problem": "List bounding box is too large and doesn't properly encapsulate individual items",
    "list_region": {
        "x1": list_region_x1, "y1": list_region_y1,
        "x2": list_region_x2, "y2": list_region_y2
    },
    "elements_in_region": len(elements_in_region),
    "element_types": {}
}

for elem in elements_in_region:
    elem_type = elem['type']
    analysis['element_types'][elem_type] = analysis['element_types'].get(elem_type, 0) + 1

with open("list_structure_problem.json", "w") as f:
    json.dump(analysis, f, indent=2)

print("\nAnalysis saved to list_structure_analysis.png and list_structure_problem.json")