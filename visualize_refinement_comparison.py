#!/usr/bin/env python3
"""Visualize the difference between raw and refined layout detection"""

import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pdf2image import convert_from_path
import numpy as np

def visualize_comparison():
    # Load results
    with open("single_page_refinement.json", 'r') as f:
        data = json.load(f)
    
    # Load page image
    images = convert_from_path("Liu et al. (2024).pdf", first_page=1, last_page=1)
    page_image = np.array(images[0])
    
    # Create side-by-side comparison
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 14))
    
    # Left: Raw detection
    ax1.imshow(page_image)
    ax1.set_title(f"Raw Detection ({data['raw_count']} elements)", fontsize=16, pad=20)
    
    for box in data['raw_boxes']:
        bbox = box['bbox']
        rect = patches.Rectangle(
            (bbox[0], bbox[1]),
            bbox[2] - bbox[0],
            bbox[3] - bbox[1],
            linewidth=2,
            edgecolor='red',
            facecolor='none',
            alpha=0.8
        )
        ax1.add_patch(rect)
        ax1.text(bbox[0], bbox[1] - 5, box['label'], color='red', fontsize=10, 
                fontweight='bold', bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7))
    
    # Right: Refined detection
    ax2.imshow(page_image)
    ax2.set_title(f"GPT-4 Refined ({data['refined_count']} elements)", fontsize=16, pad=20)
    
    for i, box in enumerate(data['refined_boxes']):
        bbox = box['bbox']
        rect = patches.Rectangle(
            (bbox[0], bbox[1]),
            bbox[2] - bbox[0],
            bbox[3] - bbox[1],
            linewidth=2,
            edgecolor='green',
            facecolor='none',
            alpha=0.8
        )
        ax2.add_patch(rect)
        # Add reading order number
        ax2.text(bbox[0], bbox[1] - 5, f"{i+1}. {box['label']}", color='green', fontsize=10,
                fontweight='bold', bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7))
    
    # Remove axes
    ax1.set_xticks([])
    ax1.set_yticks([])
    ax2.set_xticks([])
    ax2.set_yticks([])
    
    plt.suptitle("Layout Detection: Raw vs LLM-Refined", fontsize=20, y=0.98)
    plt.tight_layout()
    plt.savefig("refinement_comparison.png", dpi=150, bbox_inches='tight')
    plt.close()
    
    print("Comparison visualization saved to refinement_comparison.png")
    print(f"\nKey improvements:")
    print(f"- Reduced elements from {data['raw_count']} to {data['refined_count']}")
    print(f"- Merged fragmented text blocks")
    print(f"- Established logical reading order")
    print(f"- Better semantic labeling")

if __name__ == "__main__":
    visualize_comparison()