#!/usr/bin/env python3
"""Compare coordinates between different visualization approaches"""

import json
from pdf2image import convert_from_path
from src.injestion.layout_pipeline import LayoutDetectionPipeline
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

# Load saved results
with open("layout_results.json", 'r') as f:
    saved_results = json.load(f)

# Get fresh detection results
pipeline = LayoutDetectionPipeline()
pdf_path = "Liu et al. (2024).pdf"
layouts = pipeline.process_pdf(pdf_path)

# Convert page at same DPI as original visualize_layout.py
images_default = convert_from_path(pdf_path, first_page=1, last_page=1)
images_150 = convert_from_path(pdf_path, first_page=1, last_page=1, dpi=150)
images_200 = convert_from_path(pdf_path, first_page=1, last_page=1, dpi=200)

print("Image dimensions comparison:")
print(f"Default DPI: {images_default[0].size}")
print(f"150 DPI: {images_150[0].size}")
print(f"200 DPI: {images_200[0].size}")

# Compare coordinates
print("\nCoordinate comparison (first element):")
saved_elem = saved_results[0]['elements'][0]
fresh_elem = layouts[0][0]

print(f"\nSaved JSON:")
print(f"  Type: {saved_elem['type']}")
print(f"  Bbox: x1={saved_elem['bbox']['x1']:.1f}, y1={saved_elem['bbox']['y1']:.1f}")
print(f"  Bbox: x2={saved_elem['bbox']['x2']:.1f}, y2={saved_elem['bbox']['y2']:.1f}")

print(f"\nFresh detection:")
print(f"  Type: {fresh_elem.type}")
print(f"  Bbox: x1={fresh_elem.block.x_1:.1f}, y1={fresh_elem.block.y_1:.1f}")
print(f"  Bbox: x2={fresh_elem.block.x_2:.1f}, y2={fresh_elem.block.y_2:.1f}")

# Check if pdf2image returns coordinates matching the model
print("\n" + "="*60)
print("Creating test visualization with DEFAULT DPI...")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 10))

# Left: Using saved JSON coordinates
ax1.imshow(images_default[0])
ax1.set_title("Using saved JSON coordinates", fontsize=14)

for elem in saved_results[0]['elements'][:3]:  # First 3 elements
    bbox = elem['bbox']
    rect = patches.Rectangle(
        (bbox['x1'], bbox['y1']),
        bbox['x2'] - bbox['x1'],
        bbox['y2'] - bbox['y1'],
        linewidth=2,
        edgecolor='red',
        facecolor='none'
    )
    ax1.add_patch(rect)
    ax1.text(bbox['x1'], bbox['y1']-10, elem['type'], color='red', fontsize=10)

# Right: Using fresh detection
ax2.imshow(images_default[0])
ax2.set_title("Using fresh detection coordinates", fontsize=14)

for i, elem in enumerate(layouts[0][:3]):  # First 3 elements
    bbox = elem.block
    rect = patches.Rectangle(
        (bbox.x_1, bbox.y_1),
        bbox.x_2 - bbox.x_1,
        bbox.y_2 - bbox.y_1,
        linewidth=2,
        edgecolor='blue',
        facecolor='none'
    )
    ax2.add_patch(rect)
    ax2.text(bbox.x_1, bbox.y_1-10, str(elem.type), color='blue', fontsize=10)

for ax in [ax1, ax2]:
    ax.set_xticks([])
    ax.set_yticks([])

plt.tight_layout()
plt.savefig("coordinate_comparison_test.png", dpi=150)
plt.close()

print("Test visualization saved to coordinate_comparison_test.png")
print("\nThe coordinates should match if everything is consistent.")