#!/usr/bin/env python3
"""Simple check to see if overlaps are being resolved"""

from pathlib import Path
from pdf2image import convert_from_path
import layoutparser as lp

# Run detection
pdf_path = Path("data/marketing_slide/FlublokOnePage.pdf")
images = convert_from_path(str(pdf_path), dpi=400)
image = images[0]

model = lp.Detectron2LayoutModel(
    "lp://PrimaLayout/mask_rcnn_R_50_FPN_3x/config",
    extra_config=[
        "MODEL.ROI_HEADS.SCORE_THRESH_TEST", 0.1,
        "MODEL.ROI_HEADS.NMS_THRESH_TEST", 0.3,
    ],
    label_map={
        1: "TextRegion",
        2: "ImageRegion", 
        3: "TableRegion",
        4: "MathsRegion",
        5: "SeparatorRegion",
        6: "OtherRegion"
    }
)

layout = model.detect(image)

print("Raw PrimaLayout Detection")
print("=" * 40)
print(f"Total regions: {len(layout)}")

# Count TextRegions
text_regions = [elem for elem in layout if str(elem.type) == "TextRegion"]
print(f"TextRegions: {len(text_regions)}")

# Check for overlaps in bottom area
bottom_y = image.height * 0.7
bottom_texts = [elem for elem in text_regions if elem.block.y_1 > bottom_y]
print(f"TextRegions in bottom area: {len(bottom_texts)}")

print("\nThe marketing pipeline SHOULD:")
print("1. Take these {len(layout)} raw detections")
print("2. Apply overlap resolution via no_overlap_pipeline") 
print("3. Reduce overlapping boxes (especially in footer)")
print("\nBUT we need to verify this is actually happening!")

# Quick overlap check
print("\nChecking for significant overlaps...")
overlap_count = 0
for i, elem1 in enumerate(text_regions):
    for elem2 in text_regions[i+1:]:
        # Simple overlap check
        x_overlap = min(elem1.block.x_2, elem2.block.x_2) - max(elem1.block.x_1, elem2.block.x_1)
        y_overlap = min(elem1.block.y_2, elem2.block.y_2) - max(elem1.block.y_1, elem2.block.y_1)
        
        if x_overlap > 50 and y_overlap > 20:  # Significant overlap
            overlap_count += 1

print(f"Found {overlap_count} significant overlaps")
print("\nThese overlaps SHOULD be resolved by the pipeline!")