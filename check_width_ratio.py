#!/usr/bin/env python3
"""Check image extraction at different DPIs."""

from pathlib import Path
from src.injestion.processing.text_extractors import PyMuPDFExtractor

pdf_path = Path("data/clinical_files/FlublokPI.pdf")
extractor = PyMuPDFExtractor()

# Extract same region at different DPIs
bbox = (100, 100, 300, 200)
img_300 = extractor.extract_figure_image(pdf_path, 0, bbox, dpi=300)
img_400 = extractor.extract_figure_image(pdf_path, 0, bbox, dpi=400)

print(f"300 DPI image size: {img_300.size}")
print(f"400 DPI image size: {img_400.size}")

width_ratio = img_400.width / img_300.width
height_ratio = img_400.height / img_300.height

print(f"Width ratio: {width_ratio:.3f}")
print(f"Height ratio: {height_ratio:.3f}")
print(f"Expected ratio: {400/300:.3f}")

# The issue might be that bbox coordinates are fixed, not scaled
# When we render at different DPIs, the page size changes but bbox doesn't