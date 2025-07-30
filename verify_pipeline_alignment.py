#!/usr/bin/env python3
"""Verify that PDF pipeline visualizations align with extraction boxes."""

import json
from pathlib import Path
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

def analyze_pipeline_alignment(cache_dir: str):
    """Analyze a cached document to verify pipeline alignment."""
    cache_path = Path(cache_dir)
    
    print(f"\n{'='*60}")
    print(f"Analyzing: {cache_path.name}")
    print(f"{'='*60}")
    
    # Load all pipeline stages
    raw_boxes_path = cache_path / "raw_layouts/raw_layout_boxes.json"
    merged_boxes_path = cache_path / "merged/merged_boxes.json"
    content_path = cache_path / "extracted/content.json"
    
    if not all(p.exists() for p in [raw_boxes_path, merged_boxes_path, content_path]):
        print(f"⚠️  Missing required files in {cache_path}")
        return
    
    with open(raw_boxes_path) as f:
        raw_boxes = json.load(f)
    with open(merged_boxes_path) as f:
        merged_boxes = json.load(f)
    with open(content_path) as f:
        content = json.load(f)
    
    # Analyze first page
    page_idx = 0
    print(f"\nPage {page_idx + 1} Analysis:")
    print(f"- Raw boxes detected: {len(raw_boxes[page_idx])}")
    print(f"- Merged boxes: {len(merged_boxes[page_idx])}")
    
    # Count content blocks for this page
    page_blocks = [b for b in content['blocks'] if b['page_index'] == page_idx]
    print(f"- Final content blocks: {len(page_blocks)}")
    
    # Check coordinate consistency
    print("\nCoordinate Alignment Check:")
    
    # Map merged boxes to content blocks
    merged_map = {box['id']: box for box in merged_boxes[page_idx]}
    content_map = {block['id']: block for block in page_blocks}
    
    # Find common IDs
    common_ids = set(merged_map.keys()) & set(content_map.keys())
    
    if common_ids:
        print(f"- Found {len(common_ids)} matching block IDs")
        
        # Check a sample
        sample_id = list(common_ids)[0]
        merged_bbox = merged_map[sample_id]['bbox']
        content_bbox = content_map[sample_id]['bbox']
        
        print(f"\nSample block '{sample_id}':")
        print(f"  - Merged bbox: {merged_bbox}")
        print(f"  - Content bbox: {content_bbox}")
        print(f"  - Match: {merged_bbox == content_bbox}")
    else:
        print("⚠️  No matching IDs between merged and content stages")
    
    # Check text extraction
    print("\nText Extraction Check:")
    text_blocks = [b for b in page_blocks if b.get('text')]
    print(f"- Blocks with text: {len(text_blocks)}/{len(page_blocks)}")
    
    if text_blocks:
        sample_block = text_blocks[0]
        print(f"\nSample text block '{sample_block['id']}':")
        print(f"  - Role: {sample_block['role']}")
        print(f"  - Text length: {len(sample_block.get('text', ''))}")
        print(f"  - Extraction confidence: {sample_block.get('metadata', {}).get('extraction_confidence', 'N/A')}")
    
    # Check visualization alignment
    viz_path = cache_path / "visualizations" / f"page_{page_idx + 1:03d}_layout.png"
    if viz_path.exists():
        print(f"\n✓ Visualization found: {viz_path.name}")
        
        # Load page image to get dimensions
        page_img_path = cache_path / "pages" / f"page-{page_idx:03d}.png"
        if page_img_path.exists():
            img = Image.open(page_img_path)
            print(f"  - Page dimensions: {img.width} x {img.height}")
            
            # Check if any boxes exceed image bounds
            out_of_bounds = []
            for block in page_blocks:
                x1, y1, x2, y2 = block['bbox']
                if x2 > img.width or y2 > img.height:
                    out_of_bounds.append(block['id'])
            
            if out_of_bounds:
                print(f"  ⚠️  {len(out_of_bounds)} boxes exceed image bounds!")
            else:
                print(f"  ✓ All boxes within image bounds")
    
    # Check figures extraction
    figures_dir = cache_path / "extracted/figures"
    if figures_dir.exists():
        figures = list(figures_dir.glob("*.png"))
        print(f"\nFigures extracted: {len(figures)}")
        
        figure_blocks = [b for b in page_blocks if b['role'] in ['Figure', 'Table']]
        print(f"Figure/Table blocks: {len(figure_blocks)}")
        
        if len(figures) != sum(1 for b in content['blocks'] if b['role'] in ['Figure', 'Table']):
            print("  ⚠️  Mismatch between figure blocks and extracted images!")

def main():
    """Analyze all scientific paper caches."""
    cache_base = Path("data/cache")
    
    # Scientific paper patterns to check
    scientific_patterns = [
        "*_et_al.__*",  # Standard scientific paper naming
        "CDC_*",        # CDC documents
        "Treanor*",     # Other patterns
        "Zimmerman*",
        "Liu*",
        "Hsiao*",
        "Grohskopf*"
    ]
    
    found_any = False
    for pattern in scientific_patterns:
        for cache_dir in cache_base.glob(pattern):
            if cache_dir.is_dir():
                found_any = True
                analyze_pipeline_alignment(cache_dir)
    
    if not found_any:
        print("No scientific paper caches found!")
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print("\nPipeline Flow:")
    print("1. PDF → Images (at detection DPI)")
    print("2. Images → Layout Detection (raw boxes)")
    print("3. Raw boxes → Consolidation (merged boxes)")
    print("4. Merged boxes → Text Extraction (content)")
    print("5. Content + Images → Visualization")
    
    print("\nKey Alignment Points:")
    print("- Box coordinates must match between merged and content stages")
    print("- Visualizations should show the final merged boxes")
    print("- Text extraction uses the same coordinates as visualization")
    print("- Figure extraction creates separate image files")

if __name__ == "__main__":
    main()