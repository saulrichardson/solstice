#!/usr/bin/env python3
"""Test actual PDF processing to ensure the full stack works."""

from pathlib import Path
from src.injestion.scientific import ingest_pdf
from src.injestion.shared.storage.paths import set_cache_root

# Use a test output directory
test_output = Path("data/test_pipeline_output")
test_output.mkdir(parents=True, exist_ok=True)
set_cache_root(test_output)

# Find a PDF to test with
pdf_dir = Path("data/clinical_files")
pdfs = list(pdf_dir.glob("*.pdf"))

if pdfs:
    test_pdf = pdfs[0]
    print(f"Testing with: {test_pdf.name}")
    
    try:
        # Process the PDF
        document = ingest_pdf(test_pdf)
        
        print(f"✓ Successfully processed PDF")
        print(f"  - Pages: {document.metadata.get('total_pages', '?')}")
        print(f"  - Blocks: {len(document.blocks)}")
        print(f"  - Output dir: {test_output}")
        
        # Check if output was created
        pdf_output_dir = test_output / test_pdf.stem
        if pdf_output_dir.exists():
            print(f"✓ Output directory created: {pdf_output_dir}")
            
            # Check for expected files
            content_json = pdf_output_dir / "extracted" / "content.json"
            if content_json.exists():
                print(f"✓ content.json created successfully")
            else:
                print(f"✗ content.json not found")
        
    except Exception as e:
        print(f"✗ Processing failed: {e}")
        import traceback
        traceback.print_exc()
else:
    print("No PDFs found to test with")

# Clean up
print("\nCleaning up test output...")
import shutil
if test_output.exists():
    shutil.rmtree(test_output)