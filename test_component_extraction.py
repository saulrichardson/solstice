"""Test the component extraction pipeline."""

import json
import logging
from pathlib import Path
from src.injestion.pipeline_extraction import (
    ingest_pdf_for_extraction,
    extract_with_specialized_extractors,
    create_semantic_document
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_extraction_pipeline(pdf_path: str):
    """Test the extraction pipeline with component-specific extractors."""
    
    logger.info(f"Testing extraction pipeline on: {pdf_path}")
    
    # Step 1: Ingest PDF and prepare for extraction
    logger.info("Step 1: Ingesting PDF...")
    extraction_data = ingest_pdf_for_extraction(
        pdf_path,
        detection_dpi=200,
        merge_strategy="weighted"
    )
    
    logger.info(f"Found {len(extraction_data)} pages")
    
    # Step 2: Extract content with specialized extractors
    logger.info("Step 2: Extracting content with specialized extractors...")
    extracted_content = extract_with_specialized_extractors(
        extraction_data,
        pdf_path,
        extract_images=True
    )
    
    # Print extraction summary
    logger.info("\nExtraction Summary:")
    logger.info(f"  Text elements: {len(extracted_content['text_content'])}")
    logger.info(f"  Tables: {len(extracted_content['tables'])}")
    logger.info(f"  Figures: {len(extracted_content['figures'])}")
    
    # Show sample extracted text
    logger.info("\nSample extracted text:")
    for i, text_elem in enumerate(extracted_content['text_content'][:3]):
        if text_elem.get('extracted_text'):
            logger.info(f"  [{text_elem['type']}] {text_elem['extracted_text'][:100]}...")
    
    # Show table extraction results
    if extracted_content['tables']:
        logger.info("\nTable extraction results:")
        for i, table in enumerate(extracted_content['tables'][:2]):
            logger.info(f"  Table {i+1}: {table.get('shape', 'No data')}, "
                       f"method: {table.get('extraction_method', 'N/A')}")
            if table.get('extraction_error'):
                logger.info(f"    Error: {table['extraction_error']}")
    
    # Show figure extraction results
    if extracted_content['figures']:
        logger.info("\nFigure extraction results:")
        for i, figure in enumerate(extracted_content['figures'][:3]):
            logger.info(f"  Figure {i+1}: size={figure.get('image_size', 'N/A')}, "
                       f"color={figure.get('is_color', 'N/A')}, "
                       f"has_content={figure.get('has_content', 'N/A')}")
    
    # Step 3: Create semantic document
    logger.info("\nStep 3: Creating semantic document...")
    semantic_doc = create_semantic_document(extracted_content)
    
    logger.info(f"Semantic document has {len(semantic_doc)} blocks")
    
    # Save results
    output_file = "extraction_results_with_components.json"
    logger.info(f"\nSaving results to {output_file}")
    
    # Convert to serializable format
    results = {
        'extraction_data': extraction_data,
        'extracted_content': {
            'text_content': extracted_content['text_content'],
            'tables': [
                {k: v for k, v in table.items() if k != 'dataframe'}
                for table in extracted_content['tables']
            ],
            'figures': [
                {k: v for k, v in fig.items() if k != 'image_data'}
                for fig in extracted_content['figures']
            ],
            'metadata': extracted_content['metadata']
        },
        'semantic_document': [
            {k: v for k, v in block.items() if k != 'content' or not isinstance(v, bytes)}
            for block in semantic_doc
        ]
    }
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info("Extraction complete!")
    
    return extracted_content


if __name__ == "__main__":
    # Test with a sample PDF
    pdf_path = "Liu et al. (2024).pdf"
    
    if Path(pdf_path).exists():
        test_extraction_pipeline(pdf_path)
    else:
        logger.error(f"PDF file not found: {pdf_path}")
        logger.info("Please provide a valid PDF path")