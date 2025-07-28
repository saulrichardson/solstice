#!/usr/bin/env python3
"""Simple test of catalog pipeline V2 with clinical files."""

import json
import logging
from pathlib import Path

from src.injestion.catalog_pipeline_v2 import create_catalog_v2

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
        catalog_dir = create_catalog_v2(
            test_pdf,
            catalog_name=f"test_{test_pdf.stem}",
            output_dir="output/test_catalogs_v2"
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
        text_elements = [e for e in catalog['elements'] if e.get('content')][:2]
        
        for elem in text_elements:
            print(f"\n  Element: {elem['element_id']} (Type: {elem['element_type']})")
            content = elem['content'][:150] + "..." if len(elem['content']) > 150 else elem['content']
            print(f"  Content: {content}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("PDF Catalog Pipeline V2 Test")
    print("=" * 60)
    
    success = test_catalog_creation()
    
    if success:
        print("\n✓ Test completed successfully!")
        print("\nNext steps:")
        print("1. Check output/test_catalogs_v2/ for the full catalog")
        print("2. Review summary_report.md for details")
        print("3. Examine stages/ directory for auditable pipeline stages")
        print("4. Look at text_content/ for individual text files")
    else:
        print("\n✗ Test failed!")