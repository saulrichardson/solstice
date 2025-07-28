#!/usr/bin/env python3
"""Standalone test of catalog pipeline V2."""

import sys
import json
import logging
from pathlib import Path

# Add src to path to enable direct imports
sys.path.insert(0, str(Path(__file__).parent))

# Direct imports avoiding __init__.py
from src.injestion.layout_pipeline import LayoutDetectionPipeline
from src.injestion.agent.visual_reordering import VisualReorderingAgent
from src.injestion.extractors.component_extractors import ComponentRouter

# Import the catalog V2 module directly
import importlib.util
spec = importlib.util.spec_from_file_location(
    "catalog_pipeline_v2", 
    "src/injestion/catalog_pipeline_v2.py"
)
catalog_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog_module)

PDFElementCatalogV2 = catalog_module.PDFElementCatalogV2

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
        return False
    
    # Test with first PDF
    test_pdf = pdf_files[0]
    print(f"\nTesting with: {test_pdf.name}")
    print("=" * 60)
    
    try:
        # Create cataloger
        cataloger = PDFElementCatalogV2(
            output_base_dir="output/test_catalogs_v2",
            detection_dpi=200,
            save_thumbnails=True,
            save_intermediate_stages=True
        )
        
        # Create catalog
        catalog_dir = cataloger.create_catalog(
            test_pdf,
            catalog_name=f"test_{test_pdf.stem}"
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
        
        # Check stages directory
        stages_dir = catalog_dir / "stages"
        if stages_dir.exists():
            print("\nPipeline stages (auditable):")
            for stage_file in sorted(stages_dir.iterdir()):
                print(f"  {stage_file.name}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("PDF Catalog Pipeline V2 Test (Standalone)")
    print("=" * 60)
    
    success = test_catalog_creation()
    
    if success:
        print("\n✓ Test completed successfully!")
        print("\nThe catalog includes:")
        print("- Text extracted and saved for all text elements")
        print("- Images/tables kept as references (not extracted)")
        print("- Auditable pipeline stages in stages/ directory")
        print("- Human-readable summary in summary_report.md")
    else:
        print("\n✗ Test failed!")