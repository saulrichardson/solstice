#!/usr/bin/env python3
"""Process all PDFs in the clinical_files directory through the ingestion pipeline."""

import os
from pathlib import Path
from src.injestion import ingest_pdf

def main():
    # Find all PDFs in clinical_files directory
    clinical_dir = Path("data/clinical_files")
    pdf_files = list(clinical_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("No PDF files found in data/clinical_files/")
        return
    
    print(f"Found {len(pdf_files)} PDFs to process:")
    for pdf in pdf_files:
        print(f"  - {pdf.name}")
    print()
    
    # Process each PDF
    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"\n{'='*60}")
        print(f"Processing [{i}/{len(pdf_files)}]: {pdf_path.name}")
        print(f"{'='*60}")
        
        try:
            # Run ingestion pipeline with default settings
            document = ingest_pdf(
                pdf_path=pdf_path,
                detection_dpi=300,  # High quality for clinical documents
                merge_overlapping=True,
                create_visualizations=True
            )
            
            print(f"✓ Successfully processed {pdf_path.name}")
            print(f"  - Total pages: {document.metadata['total_pages']}")
            print(f"  - Total blocks detected: {len(document.blocks)}")
            
        except Exception as e:
            print(f"✗ Error processing {pdf_path.name}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*60}")
    print("Processing complete!")
    print(f"Results saved in: data/cache/[document_id]/")

if __name__ == "__main__":
    main()