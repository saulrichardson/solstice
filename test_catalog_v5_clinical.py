#!/usr/bin/env python3
"""Test the catalog pipeline V5 with full-page text extraction."""

import json
import logging
from pathlib import Path

from src.injestion.catalog_pipeline_v5 import create_catalog_v5

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
        catalog_dir = create_catalog_v5(
            test_pdf,
            catalog_name=f"test_v5_{test_pdf.stem}",
            output_dir="output/test_catalogs_v5"
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
        
        # Show sample text content with improved spacing
        print("\n" + "="*60)
        print("SAMPLE EXTRACTED TEXT (V5 - Full Page Analysis):")
        print("="*60)
        
        text_elements = [e for e in catalog['elements'] if e.get('content')][:5]
        
        for i, elem in enumerate(text_elements, 1):
            print(f"\n{i}. Element: {elem['element_id']} (Type: {elem['element_type']}, Page: {elem['page_num']})")
            print("-" * 40)
            content = elem['content']
            if len(content) > 300:
                # Show first 150 and last 150 chars for long text
                print(content[:150])
                print("...")
                print(content[-150:])
            else:
                print(content)
        
        # Compare with previous versions
        print("\n" + "="*60)
        print("COMPARISON ACROSS VERSIONS:")
        print("="*60)
        
        # Find a specific element to compare
        test_element_file = "elem_001_0002.txt"
        
        versions = [
            ("V3", f"output/test_catalogs_v3/test_v3_{test_pdf.stem}/text_content/{test_element_file}"),
            ("V4", f"output/test_catalogs_v4/test_v4_{test_pdf.stem}/text_content/{test_element_file}"),
            ("V5", f"{catalog_dir}/text_content/{test_element_file}")
        ]
        
        for version, path in versions:
            path = Path(path)
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    text = f.read()
                print(f"\n{version} (first 200 chars):")
                print(repr(text[:200]))
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("PDF Catalog Pipeline V5 Test (Full Page Text Extraction)")
    print("=" * 60)
    
    success = test_catalog_creation()
    
    if success:
        print("\n✓ Test completed successfully!")
        print("\nV5 Approach:")
        print("- Extracts character positions from full page")
        print("- Maps characters to bounding boxes")
        print("- Builds text with proper spacing based on character positions")
        print("- Preserves original PDF text quality")
    else:
        print("\n✗ Test failed!")