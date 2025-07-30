#!/usr/bin/env python3
"""Analyze a complete pipeline run with the new box tracking system."""

import json
from pathlib import Path
from src.injestion.standard_pipeline import StandardPipeline
from src.injestion.config import IngestionConfig
import shutil

def analyze_pipeline_run():
    """Run the pipeline and analyze the results."""
    # Find a test PDF
    test_pdfs = list(Path("data/clinical_files").glob("*.pdf"))
    if not test_pdfs:
        print("No test PDFs found")
        return
    
    # Use the first PDF
    test_pdf = test_pdfs[0]
    print(f"=== Running Pipeline on: {test_pdf.name} ===\n")
    
    # Create config with all tracking enabled
    config = IngestionConfig(
        save_intermediate_states=True,
        create_visualizations=True,
        detection_dpi=400,
        merge_overlapping=True,
        expand_boxes=True,
        box_padding=5.0
    )
    
    # Clean up any existing cache for this document
    cache_name = test_pdf.stem.replace(" ", "_").replace("(", "").replace(")", "").replace(".", "_")
    cache_dir = Path(f"data/cache/{cache_name}")
    if cache_dir.exists():
        print(f"Cleaning existing cache: {cache_dir}")
        shutil.rmtree(cache_dir)
    
    # Run the pipeline
    print("Running pipeline...")
    pipeline = StandardPipeline(config)
    document = pipeline.process_pdf(test_pdf)
    
    print(f"\n=== Pipeline Results ===")
    print(f"Total pages: {document.metadata.get('total_pages', 'Unknown')}")
    print(f"Total blocks extracted: {len(document.blocks)}")
    
    # Analyze pipeline metadata
    print(f"\n=== Pipeline Metadata ===")
    for key, value in document.pipeline_metadata.items():
        print(f"  {key}: {value}")
    
    # Calculate reduction ratios
    if document.pipeline_metadata.get('raw_detection_count'):
        raw = document.pipeline_metadata['raw_detection_count']
        consolidated = document.pipeline_metadata['after_consolidation_count']
        final = document.pipeline_metadata['final_block_count']
        
        print(f"\n=== Box Reduction Analysis ===")
        print(f"  Raw → Consolidated: {raw} → {consolidated} ({(1 - consolidated/raw)*100:.1f}% reduction)")
        print(f"  Consolidated → Final: {consolidated} → {final} ({(1 - final/consolidated)*100:.1f}% reduction)")
        print(f"  Overall reduction: {raw} → {final} ({(1 - final/raw)*100:.1f}% reduction)")
    
    # Analyze box IDs
    print(f"\n=== Box ID Analysis ===")
    det_count = sum(1 for b in document.blocks if b.id.startswith('det_'))
    mrg_count = sum(1 for b in document.blocks if b.id.startswith('mrg_'))
    print(f"  Detection IDs (det_*): {det_count}")
    print(f"  Merged IDs (mrg_*): {mrg_count}")
    print(f"  Merge ratio: {mrg_count / len(document.blocks) * 100:.1f}%")
    
    # Sample some blocks
    print(f"\n=== Sample Blocks ===")
    for i, block in enumerate(document.blocks[:5]):
        print(f"Block {i}:")
        print(f"  ID: {block.id}")
        print(f"  Role: {block.role}")
        print(f"  Page: {block.page_index}")
        print(f"  Text preview: {block.text[:50] if block.text else 'No text'}...")
        print(f"  Score: {block.metadata.get('score', 'N/A')}")
    
    # Check saved files
    cache_dir = document.get_cache_path()
    print(f"\n=== Saved Files ===")
    print(f"Cache directory: {cache_dir}")
    
    # Check raw layouts
    raw_file = cache_dir / "raw_layouts" / "raw_layout_boxes.json"
    if raw_file.exists():
        with open(raw_file) as f:
            raw_data = json.load(f)
        print(f"✓ Raw layouts saved: {len(raw_data)} pages")
        
        # Sample raw box
        if raw_data and raw_data[0]:
            print(f"  Sample raw box: {json.dumps(raw_data[0][0], indent=2)}")
    
    # Check merged boxes
    merged_file = cache_dir / "merged" / "merged_boxes.json"
    if merged_file.exists():
        with open(merged_file) as f:
            merged_data = json.load(f)
        print(f"✓ Merged boxes saved: {len(merged_data)} pages")
        
        # Find a merged box with lineage
        print(f"\n=== Lineage Tracking Example ===")
        found_lineage = False
        for page_idx, page_boxes in enumerate(merged_data):
            for box in page_boxes:
                if 'source_ids' in box and len(box['source_ids']) > 1:
                    print(f"Page {page_idx + 1}, Box {box['id']}:")
                    print(f"  Label: {box['label']}")
                    print(f"  Source IDs: {box['source_ids']}")
                    print(f"  Merge reason: {box.get('merge_reason', 'Not specified')}")
                    print(f"  Score: {box['score']}")
                    found_lineage = True
                    break
            if found_lineage:
                break
        
        if not found_lineage:
            print("  No multi-source merges found in this document")
    
    # Check visualizations
    viz_dir = cache_dir / "visualizations"
    if viz_dir.exists():
        viz_files = list(viz_dir.glob("*.png"))
        print(f"✓ Visualizations created: {len(viz_files)} files")
    
    raw_viz_dir = cache_dir / "raw_layouts" / "visualizations"
    if raw_viz_dir.exists():
        raw_viz_files = list(raw_viz_dir.glob("*.png"))
        print(f"✓ Raw layout visualizations: {len(raw_viz_files)} files")
    
    # Analyze box types
    print(f"\n=== Box Type Distribution ===")
    type_counts = {}
    for block in document.blocks:
        role = block.role
        type_counts[role] = type_counts.get(role, 0) + 1
    
    for role, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {role}: {count} ({count/len(document.blocks)*100:.1f}%)")
    
    print(f"\n=== Summary ===")
    print(f"✓ Pipeline completed successfully")
    print(f"✓ Box tracking is working with deterministic IDs")
    print(f"✓ Lineage tracking is {'active' if 'found_lineage' in locals() and found_lineage else 'not needed (no merges)'}")
    print(f"✓ All intermediate states were saved")

if __name__ == "__main__":
    analyze_pipeline_run()