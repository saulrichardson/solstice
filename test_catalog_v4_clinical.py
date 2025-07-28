#!/usr/bin/env python3
"""Test the catalog pipeline V4 with improved text extraction."""

import json
import logging
from pathlib import Path

from src.injestion.catalog_pipeline_v4 import create_catalog_v4

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
        catalog_dir = create_catalog_v4(
            test_pdf,
            catalog_name=f"test_v4_{test_pdf.stem}",
            output_dir="output/test_catalogs_v4"
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
        print("SAMPLE EXTRACTED TEXT (first 5 text elements):")
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
        
        # Compare with V3 if it exists
        v3_dir = Path(f"output/test_catalogs_v3/test_v3_{test_pdf.stem}")
        if v3_dir.exists():
            print("\n" + "="*60)
            print("COMPARISON WITH V3:")
            print("="*60)
            
            # Load a V3 text file
            v3_text_files = list((v3_dir / "text_content").glob("*.txt"))
            if v3_text_files:
                with open(v3_text_files[0], 'r', encoding='utf-8') as f:
                    v3_text = f.read()
                
                # Load the same element from V4
                v4_text_file = catalog_dir / "text_content" / v3_text_files[0].name
                if v4_text_file.exists():
                    with open(v4_text_file, 'r', encoding='utf-8') as f:
                        v4_text = f.read()
                    
                    print(f"\nElement: {v3_text_files[0].stem}")
                    print("\nV3 (missing spaces):")
                    print(repr(v3_text[:200]))
                    print("\nV4 (improved spacing):")
                    print(repr(v4_text[:200]))
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("PDF Catalog Pipeline V4 Test (Improved Text Extraction)")
    print("=" * 60)
    
    success = test_catalog_creation()
    
    if success:
        print("\n✓ Test completed successfully!")
        print("\nImprovements in V4:")
        print("- Better text spacing by expanding bounding boxes slightly")
        print("- Smarter space detection and fixing")
        print("- Improved pdfplumber parameters for better layout analysis")
        print("- Preserves intentional line breaks while fixing spacing issues")
    else:
        print("\n✗ Test failed!")