#!/usr/bin/env python3
"""Create a clear visualization showing all boxes and their text."""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image
import json

# Load the page image
img = Image.open("data/cache/FlublokOnePage/pages/page-000.png")

# Load the content
with open("data/cache/FlublokOnePage/extracted/content.json", 'r') as f:
    data = json.load(f)

# Create figure
fig, ax = plt.subplots(1, 1, figsize=(16, 20))
ax.imshow(img)
ax.set_title("ALL Text Boxes - Red = Narrow/Garbled, Green = Normal", fontsize=20)

# Draw ALL text boxes with labels
for i, block in enumerate(data['blocks']):
    if block.get('role') == 'Text':
        bbox = block['bbox']
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        
        # Determine color based on width and text quality
        text = block.get('text', '')
        if width < 400 and any(word in text for word in ['(q )', 'kis produced', 'nsect cells']):
            color = 'red'
            label = f"GARBLED (W={width:.0f})"
        else:
            color = 'green'
            label = f"OK (W={width:.0f})"
        
        # Draw rectangle
        rect = patches.Rectangle(
            (bbox[0], bbox[1]), width, height,
            linewidth=2, edgecolor=color, facecolor=color, alpha=0.2
        )
        ax.add_patch(rect)
        
        # Add label
        ax.text(bbox[0], bbox[1]-10, label, 
               color=color, fontsize=10, weight='bold',
               bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.9))
        
        # For garbled boxes, show the text
        if color == 'red':
            text_preview = text[:40] + '...' if len(text) > 40 else text
            ax.text(bbox[2]+10, bbox[1]+height/2, 
                   f"Text: '{text_preview}'", 
                   color='red', fontsize=8,
                   bbox=dict(boxstyle="round,pad=0.3", facecolor='yellow', alpha=0.9))

ax.set_xlim(0, img.width)
ax.set_ylim(img.height, 0)

plt.tight_layout()
plt.savefig("all_boxes_labeled.png", dpi=150, bbox_inches='tight')
print("Saved all_boxes_labeled.png")

# Also print text from all narrow boxes
print("\n=== NARROW BOXES AND THEIR TEXT ===")
for block in data['blocks']:
    if block.get('role') == 'Text':
        bbox = block['bbox']
        width = bbox[2] - bbox[0]
        if width < 400:
            print(f"\nBox at ({bbox[0]:.0f}, {bbox[1]:.0f}), Width: {width:.0f}px")
            print(f"Text: '{block.get('text', 'NO TEXT')}'")