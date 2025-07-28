#!/usr/bin/env python3
"""Example of using the complete catalog pipeline with visualization."""

import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.injestion import (
    create_catalog_complete,
    load_catalog,
    export_catalog_text
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def main():
    """Demonstrate the complete catalog pipeline."""
    
    # Find a clinical PDF
    clinical_dir = Path(__file__).parent.parent / "input" / "Clinical Files"
    pdf_files = list(clinical_dir.glob("*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in {clinical_dir}")
        return
    
    test_pdf = pdf_files[0]
    print(f"\nProcessing: {test_pdf.name}")
    print("=" * 60)
    
    # Create catalog with complete pipeline
    catalog_dir = create_catalog_complete(
        test_pdf,
        catalog_name=f"demo_{test_pdf.stem}",
        output_dir="output/demo_catalogs",
        # Pipeline parameters
        confidence_weight=0.7,
        area_weight=0.3,
        overlap_threshold=0.7,
        # Enable visualizations
        create_visualizations=True
    )
    
    print(f"\n✓ Catalog created at: {catalog_dir}")
    
    # Load and explore the catalog
    print("\n" + "="*60)
    print("EXPLORING CATALOG")
    print("="*60)
    
    reader = load_catalog(catalog_dir)
    
    # Show statistics
    stats = reader.get_statistics()
    print(f"\nStatistics:")
    print(f"  Total elements: {stats['total_elements']}")
    print(f"  Text extracted: {stats['text_extracted']}")
    print(f"  Image references: {stats['image_references']}")
    
    # Show element types
    print(f"\nElements by type:")
    for elem_type, count in sorted(stats['by_type'].items()):
        print(f"  {elem_type}: {count}")
    
    # Export text content
    export_path = catalog_dir / "exported_text.txt"
    export_catalog_text(catalog_dir, export_path)
    print(f"\n✓ Text exported to: {export_path}")
    
    # Show sample text from page 2
    print("\n" + "="*60)
    print("SAMPLE TEXT FROM PAGE 2")
    print("="*60)
    
    page_text = reader.get_page_text(2)
    if page_text:
        # Show first 500 characters
        preview = page_text[:500] + "..." if len(page_text) > 500 else page_text
        print(preview)
    
    # List visualizations created
    viz_dir = catalog_dir / "visualizations"
    if viz_dir.exists():
        print("\n" + "="*60)
        print("VISUALIZATIONS CREATED")
        print("="*60)
        
        viz_files = sorted(viz_dir.glob("*.png"))
        print(f"\n{len(viz_files)} visualization files created:")
        
        # Show key visualizations
        key_files = [
            "00_pipeline_summary.png",
            "page_02_stage3_final.png",
            "page_02_catalog.png"
        ]
        
        for filename in key_files:
            if (viz_dir / filename).exists():
                print(f"  ✓ {filename}")
    
    print("\n" + "="*60)
    print("PIPELINE COMPLETE!")
    print("="*60)
    print(f"\nExplore the catalog at: {catalog_dir}")
    print(f"View visualizations at: {viz_dir}")


if __name__ == "__main__":
    main()