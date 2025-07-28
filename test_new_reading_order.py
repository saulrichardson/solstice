#!/usr/bin/env python3
"""Test the new reading order on page 3 of Arunachalam paper."""

import sys
sys.path.insert(0, '/Users/saul/projects/solstice/solstice/src')

from injestion.models.box import Box
from injestion.processing.reading_order import determine_reading_order_simple

# Page 3 (index 2) boxes from the Arunachalam paper
# Using the actual bbox values from earlier analysis
boxes = [
    Box(id="fab1ac32", bbox=[144.93, 1248.27, 1185.81, 3070.94], page_index=2, label="Text"),
    Box(id="5fa0ac31", bbox=[384.33, 234.76, 2111.42, 1025.18], page_index=2, label="Figure"),
    Box(id="5283ce44", bbox=[1257.37, 1241.07, 2288.50, 2515.88], page_index=2, label="Text"),
    Box(id="3b2440d7", bbox=[1253.57, 2681.99, 2292.54, 3066.76], page_index=2, label="Text"),
    Box(id="c5febf1e", bbox=[1240.04, 2593.24, 2300.42, 2678.68], page_index=2, label="Title"),
    Box(id="a583e2de", bbox=[144.04, 1097.66, 2289.45, 1214.10], page_index=2, label="Text"),
]

# Page dimensions from earlier
page_width = 2481
page_height = 3296

print(f"Page dimensions: {page_width} x {page_height}")
print(f"Midpoint: {page_width/2}")
print(f"Bottom threshold (80%): {page_height * 0.8}")
print(f"Width threshold (75%): {page_width * 0.75}")

# Run the new algorithm
reading_order = determine_reading_order_simple(boxes, page_width)

print("\nReading order:")
for i, box_id in enumerate(reading_order, 1):
    box = next(b for b in boxes if b.id == box_id)
    width = box.bbox[2] - box.bbox[0]
    width_pct = (width / page_width) * 100
    y_pct = (box.bbox[1] / page_height) * 100
    
    # Check if it would be classified as full-width bottom
    is_full_width = width >= page_width * 0.75
    is_bottom = box.bbox[1] >= page_height * 0.8
    
    print(f"{i}. {box_id:10} - {box.label:6} (width: {width_pct:3.0f}%, y: {y_pct:3.0f}%) {'[BOTTOM]' if is_full_width and is_bottom else ''}")

# Check if the title ordering is fixed
try:
    title_pos = reading_order.index("c5febf1e") + 1
    text5_pos = reading_order.index("5283ce44") + 1
    text6_pos = reading_order.index("3b2440d7") + 1
    
    print(f"\nTitle position: {title_pos}")
    print(f"Text #5 position: {text5_pos}")
    print(f"Text #6 position: {text6_pos}")
    
    if text5_pos < title_pos < text6_pos:
        print("✓ Title is correctly placed between text #5 and #6!")
    else:
        print("✗ Title ordering issue not fixed")
except ValueError as e:
    print(f"Error finding element: {e}")