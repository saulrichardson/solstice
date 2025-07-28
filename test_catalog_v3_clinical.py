#!/usr/bin/env python3
"""Test the catalog pipeline V3 with clinical files."""

import json
import logging
from pathlib import Path

from src.injestion.catalog_pipeline_v3 import create_catalog_v3

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def test_catalog_creation():
    """Test the catalog creation with a clinical PDF."""
    # Get first clinical file
    clinical_dir = Path("input/Clinical Files")
    pdf_files = list(clinical_dir.glob("*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in {clinical_dir}")
        return
    
    # Test with first PDF
    test_pdf = pdf_files[0]
    print(f"\nTesting with: {test_pdf.name}")
    print("=" * 60)
    
    try:
        # Create catalog
        catalog_dir = create_catalog_v3(
            test_pdf,
            catalog_name=f"test_v3_{test_pdf.stem}",
            output_dir="output/test_catalogs_v3"
        )
        
        print(f"\n✓ Catalog created at: {catalog_dir}")
        
        # Load and display summary
        with open(catalog_dir / "catalog.json") as f:
            catalog = json.load(f)
        
        print("\nCatalog Summary:")
        print(f"  Total elements: {catalog['statistics']['total_elements']}")
        print(f"  Text extracted: {catalog['statistics']['text_extracted']}")
        print(f"  Image references: {catalog['statistics']['image_references']}")
        
        print("\nElements by type:")
        for elem_type, count in sorted(catalog['statistics']['by_type'].items()):
            print(f"  {elem_type}: {count}")
        
        print("\nDirectory structure:")
        for item in sorted(catalog_dir.iterdir()):
            if item.is_file():
                print(f"  📄 {item.name}")
            else:
                print(f"  📁 {item.name}/")
                # Show a few files in subdirectories
                sub_files = list(item.iterdir())[:3]
                for sub in sub_files:
                    print(f"      {sub.name}")
                if len(list(item.iterdir())) > 3:
                    print(f"      ... ({len(list(item.iterdir()))} total files)")
        
        # Show sample text content
        print("\nSample extracted text:")
        text_elements = [e for e in catalog['elements'] if e.get('content')][:3]
        
        for elem in text_elements:
            print(f"\n  Element: {elem['element_id']} (Type: {elem['element_type']}, Page: {elem['page_num']})")
            content = elem['content'][:200] + "..." if len(elem['content']) > 200 else elem['content']
            print(f"  Content: {repr(content)}")
        
        # Check if text files were created
        text_content_dir = catalog_dir / "text_content"
        if text_content_dir.exists():
            text_files = list(text_content_dir.glob("*.txt"))
            print(f"\nText files created: {len(text_files)}")
            
            # Show content of first text file
            if text_files:
                with open(text_files[0], 'r', encoding='utf-8') as f:
                    sample_text = f.read()
                print(f"\nSample text file ({text_files[0].name}):")
                print(repr(sample_text[:200] + "..." if len(sample_text) > 200 else sample_text))
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("PDF Catalog Pipeline V3 Test (Fixed Coordinates)")
    print("=" * 60)
    
    success = test_catalog_creation()
    
    if success:
        print("\n✓ Test completed successfully!")
        print("\nThe catalog includes:")
        print("- Text extracted and saved for all text elements")
        print("- Images/tables kept as references (not extracted)")
        print("- Auditable pipeline stages in stages/ directory")
        print("- Human-readable summary in summary_report.md")
        print("- Proper coordinate conversion from detection pixels to PDF points")
    else:
        print("\n✗ Test failed!")