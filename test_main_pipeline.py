#!/usr/bin/env python3
"""Test the main ingestion pipeline with column detection and reading order."""

import json
import logging
from pathlib import Path
from pprint import pprint

from src.injestion.pipeline import ingest_pdf
from src.injestion.storage import doc_id, stage_dir

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def display_results(pdf_path: Path):
    """Display the results from all intermediate stages."""
    
    document_id = doc_id(pdf_path)
    print(f"\nDocument ID: {document_id}")
    print("="*80)
    
    # Load and display pipeline summary
    summary_path = stage_dir("summary", pdf_path) / "pipeline_summary.json"
    if summary_path.exists():
        with open(summary_path) as f:
            summary = json.load(f)
        
        print("\n📋 PIPELINE SUMMARY")
        print("-"*40)
        print(f"Total pages: {summary['total_pages']}")
        print(f"Total blocks: {summary['total_blocks']}")
        print(f"Processing stages: {', '.join(summary['processing_stages'])}")
        print("\nSettings:")
        for key, value in summary['settings'].items():
            print(f"  {key}: {value}")
    
    # Load and display merged layout
    merged_path = stage_dir("merged", pdf_path) / "merged_boxes.json"
    if merged_path.exists():
        with open(merged_path) as f:
            merged_data = json.load(f)
        
        print("\n📦 MERGED LAYOUT (First 2 pages)")
        print("-"*40)
        for page_idx in range(min(2, len(merged_data))):
            page_boxes = merged_data[page_idx]
            print(f"\nPage {page_idx + 1}: {len(page_boxes)} boxes")
            
            # Count by type
            type_counts = {}
            for box in page_boxes:
                label = box['label']
                type_counts[label] = type_counts.get(label, 0) + 1
            
            for label, count in sorted(type_counts.items()):
                print(f"  {label}: {count}")
    
    # Load and display column detection
    columns_path = stage_dir("columns", pdf_path) / "column_detection.json"
    if columns_path.exists():
        with open(columns_path) as f:
            columns_data = json.load(f)
        
        print("\n📊 COLUMN DETECTION")
        print("-"*40)
        for page_data in columns_data[:3]:  # First 3 pages
            page_num = page_data['page'] + 1
            num_cols = page_data['num_columns']
            print(f"\nPage {page_num}: {num_cols} column(s)")
            
            if num_cols > 1:
                for col_idx, col_elements in enumerate(page_data['columns']):
                    if col_idx == 0 and num_cols > 2:
                        print(f"  Spanning elements: {len(col_elements)} items")
                    else:
                        print(f"  Column {col_idx}: {len(col_elements)} items")
    
    # Load and display reading order
    order_path = stage_dir("reading_order", pdf_path) / "reading_order.json"
    if order_path.exists():
        with open(order_path) as f:
            order_data = json.load(f)
        
        print("\n📖 READING ORDER")
        print("-"*40)
        for page_info in order_data['pages'][:2]:  # First 2 pages
            page_num = page_info['page'] + 1
            num_elements = page_info['num_elements']
            order = page_info['reading_order']
            
            print(f"\nPage {page_num}: {num_elements} elements")
            print(f"  Order preview: {order[:5]}..." if len(order) > 5 else f"  Order: {order}")


def main():
    """Run the main pipeline on a test PDF."""
    
    # Find a clinical PDF to test
    clinical_dir = Path("input/Clinical Files")
    pdf_files = list(clinical_dir.glob("*.pdf"))
    
    if not pdf_files:
        # Try Liu et al PDF
        liu_pdf = Path("Liu et al. (2024).pdf")
        if liu_pdf.exists():
            pdf_files = [liu_pdf]
        else:
            print("No PDF files found to test")
            return
    
    # Use first available PDF
    test_pdf = pdf_files[0]
    print(f"\n🚀 TESTING MAIN PIPELINE")
    print(f"PDF: {test_pdf.name}")
    print("="*80)
    
    try:
        # Run the pipeline
        print("\nRunning ingestion pipeline...")
        document = ingest_pdf(
            test_pdf,
            detection_dpi=200,
            merge_overlapping=True,
            merge_threshold=0.1,
            confidence_weight=0.7,
            area_weight=0.3
        )
        
        print("✅ Pipeline completed successfully!")
        
        # Display all intermediate results
        display_results(test_pdf)
        
        # Show final document stats
        print("\n📄 FINAL DOCUMENT")
        print("-"*40)
        print(f"Total blocks: {len(document.blocks)}")
        print(f"Total pages: {document.metadata['total_pages']}")
        
        # Show sample blocks from first page
        page_1_blocks = [b for b in document.blocks if b.page_index == 0]
        print(f"\nPage 1 sample blocks ({len(page_1_blocks)} total):")
        for block in page_1_blocks[:3]:
            print(f"  - {block.role}: bbox={block.bbox}, score={block.metadata.get('score', 0):.3f}")
        
        # Show reading order for first page
        if document.reading_order and len(document.reading_order) > 0:
            print(f"\nPage 1 reading order: {len(document.reading_order[0])} elements")
            print(f"  First 5: {document.reading_order[0][:5]}")
        
        # Output paths
        doc_id_str = doc_id(test_pdf)
        print(f"\n📁 OUTPUT LOCATIONS")
        print("-"*40)
        print(f"Document ID: {doc_id_str}")
        print(f"Data directory: data/cache/{doc_id_str}/")
        print(f"Final document: data/docs/{doc_id_str}.json")
        
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()