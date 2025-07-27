#!/usr/bin/env python3
"""Test the extraction-focused pipeline."""

import json
from pathlib import Path
from src.injestion.pipeline_extraction import (
    ingest_pdf_for_extraction,
    extract_with_specialized_extractors,
    create_semantic_document
)


def test_extraction_pipeline():
    """Test the extraction pipeline on a PDF."""
    
    pdf_path = Path("Liu et al. (2024).pdf")
    if not pdf_path.exists():
        print(f"Error: {pdf_path} not found")
        return
    
    print("Testing Extraction Pipeline")
    print("="*70)
    
    # Step 1: Ingest and organize
    print("\nStep 1: Ingesting PDF and organizing elements...")
    extraction_data = ingest_pdf_for_extraction(
        pdf_path,
        detection_dpi=200,
        merge_strategy="weighted"
    )
    
    print(f"\nProcessed {len(extraction_data)} pages")
    
    # Show summary statistics
    total_text = sum(len(page['organized_elements']['text']) for page in extraction_data)
    total_figures = sum(len(page['organized_elements']['figures']) for page in extraction_data)
    total_tables = sum(len(page['organized_elements']['tables']) for page in extraction_data)
    
    print(f"\nTotal elements detected:")
    print(f"  - Text blocks: {total_text}")
    print(f"  - Figures: {total_figures}")
    print(f"  - Tables: {total_tables}")
    
    # Show sample page
    if extraction_data:
        sample_page = extraction_data[0]
        print(f"\nSample (Page 1):")
        print(f"  - Elements: {len(sample_page['all_boxes'])} total")
        print(f"  - Reading order: {len(sample_page['reading_order'])} elements ordered")
        
        # Show first few elements in reading order
        print("\n  First 5 elements in reading order:")
        for i, elem_id in enumerate(sample_page['reading_order'][:5]):
            # Find the box with this ID
            box = next((b for b in sample_page['all_boxes'] if b.id == elem_id), None)
            if box:
                print(f"    {i+1}. {box.label} at y={box.bbox[1]:.1f}")
    
    # Step 2: Extract with specialized extractors
    print("\n" + "-"*70)
    print("Step 2: Routing to specialized extractors...")
    extracted_content = extract_with_specialized_extractors(
        extraction_data,
        pdf_path,
        extract_images=False  # Skip image extraction for speed
    )
    
    print(f"\nExtracted content:")
    print(f"  - Text elements: {len(extracted_content['text_content'])}")
    print(f"  - Tables: {len(extracted_content['tables'])}")
    print(f"  - Figures: {len(extracted_content['figures'])}")
    
    # Step 3: Create semantic document
    print("\n" + "-"*70)
    print("Step 3: Creating semantic document...")
    semantic_doc = create_semantic_document(extracted_content)
    
    print(f"\nSemantic document has {len(semantic_doc)} blocks")
    
    # Show sample of semantic ordering
    print("\nFirst 10 blocks in semantic order:")
    for i, block in enumerate(semantic_doc[:10]):
        print(f"  {i+1}. Page {block['page']}, {block['type']} "
              f"(id: {block['id'][:8]}...)")
    
    # Save results
    output_file = Path("extraction_pipeline_results.json")
    results = {
        'summary': {
            'total_pages': len(extraction_data),
            'total_text': total_text,
            'total_figures': total_figures,
            'total_tables': total_tables,
            'total_blocks': len(semantic_doc)
        },
        'extraction_data': [
            {
                'page': page['page_num'],
                'element_counts': {
                    'text': len(page['organized_elements']['text']),
                    'figures': len(page['organized_elements']['figures']),
                    'tables': len(page['organized_elements']['tables'])
                },
                'reading_order_length': len(page['reading_order'])
            }
            for page in extraction_data
        ],
        'sample_semantic_blocks': semantic_doc[:20]  # First 20 blocks
    }
    
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to {output_file}")
    
    # Analyze element distribution
    print("\n" + "="*70)
    print("ELEMENT DISTRIBUTION BY PAGE:")
    print("="*70)
    print(f"{'Page':<6} {'Text':<8} {'Figures':<10} {'Tables':<10}")
    print("-"*40)
    
    for page_data in extraction_data[:5]:  # First 5 pages
        page_num = page_data['page_num']
        org = page_data['organized_elements']
        print(f"{page_num:<6} {len(org['text']):<8} "
              f"{len(org['figures']):<10} {len(org['tables']):<10}")


def analyze_reading_order():
    """Analyze how well the reading order algorithm works."""
    
    pdf_path = Path("Liu et al. (2024).pdf")
    if not pdf_path.exists():
        print(f"Error: {pdf_path} not found")
        return
    
    print("\nAnalyzing Reading Order Algorithm")
    print("="*70)
    
    # Get extraction data
    extraction_data = ingest_pdf_for_extraction(pdf_path)
    
    # Analyze page 2 (has a figure)
    page_2_data = extraction_data[1]  # 0-indexed
    
    print(f"\nPage 2 Analysis:")
    print(f"Total elements: {len(page_2_data['all_boxes'])}")
    
    # Group elements by type in reading order
    ordered_types = []
    for elem_id in page_2_data['reading_order']:
        box = next((b for b in page_2_data['all_boxes'] if b.id == elem_id), None)
        if box:
            ordered_types.append(box.label)
    
    print(f"\nElement sequence in reading order:")
    for i, elem_type in enumerate(ordered_types):
        print(f"  {i+1}. {elem_type}")
    
    # Check if figure caption follows figure
    for i in range(len(ordered_types) - 1):
        if ordered_types[i] == 'Figure' and ordered_types[i+1] == 'Text':
            print(f"\n✓ Found potential figure-caption pair at positions {i+1}-{i+2}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "order":
        analyze_reading_order()
    else:
        test_extraction_pipeline()