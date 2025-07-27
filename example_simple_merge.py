#!/usr/bin/env python3
"""Example of using simple box merging in your workflow."""

from pathlib import Path
from src.injestion.pipeline_simple import ingest_pdf_simple
from src.injestion.pipeline import ingest_pdf


def example_usage():
    """Show different ways to use simple merging."""
    
    pdf_path = Path("Liu et al. (2024).pdf")
    
    # Method 1: Use simple merging pipeline directly
    print("Method 1: Simple geometric merging")
    print("-" * 40)
    simple_pages = ingest_pdf_simple(
        pdf_path,
        merge_strategy="simple",  # or "iou"
        overlap_threshold=0.5     # Adjust as needed
    )
    
    print(f"Processed {len(simple_pages)} pages")
    for i, page in enumerate(simple_pages):
        print(f"  Page {i}: {len(page.boxes)} boxes")
    
    # Method 2: Use original pipeline with LLM (for comparison)
    print("\nMethod 2: LLM-based refinement")
    print("-" * 40)
    llm_pages = ingest_pdf(pdf_path)
    
    print(f"Processed {len(llm_pages)} pages")
    for i, page in enumerate(llm_pages):
        print(f"  Page {i}: {len(page.boxes)} boxes")
    
    # Method 3: Use the hybrid approach
    print("\nMethod 3: Hybrid approach (merge first, then optionally LLM)")
    print("-" * 40)
    from src.injestion.agent.refine_layout_simple import refine_page_layout_hybrid
    from src.injestion.layout_pipeline import LayoutDetectionPipeline
    import uuid
    
    # Get raw detections
    detector = LayoutDetectionPipeline()
    layouts = detector.process_pdf(pdf_path)
    
    # Process first page with hybrid approach
    page_layout = layouts[0]
    from src.injestion.agent.refine_layout import Box
    
    boxes = [
        Box(
            id=str(uuid.uuid4())[:8],
            bbox=(
                layout.block.x_1,
                layout.block.y_1,
                layout.block.x_2,
                layout.block.y_2,
            ),
            label=str(layout.type) if layout.type else "Unknown",
            score=float(layout.score or 0.0),
        )
        for layout in page_layout
    ]
    
    # First merge geometrically, but don't use LLM
    hybrid_result = refine_page_layout_hybrid(
        page_index=0,
        raw_boxes=boxes,
        pre_merge=True,      # Apply geometric merging
        merge_strategy="simple",
        overlap_threshold=0.5,
        use_llm=False        # Skip LLM refinement
    )
    
    print(f"Hybrid result: {len(boxes)} → {len(hybrid_result.boxes)} boxes")
    
    # Show the benefits
    print("\n" + "="*50)
    print("Benefits of simple merging:")
    print("="*50)
    print("✓ Fast - no API calls needed")
    print("✓ Deterministic - same input always gives same output")
    print("✓ Free - no OpenAI API costs")
    print("✓ Works offline")
    print("✓ Handles basic overlapping text boxes well")
    
    print("\nWhen to use each approach:")
    print("- Simple merging: Good for most documents with overlapping detections")
    print("- LLM refinement: Better for complex layouts, reading order, semantic grouping")
    print("- Hybrid: Pre-merge obvious overlaps, then use LLM for fine-tuning")


if __name__ == "__main__":
    example_usage()