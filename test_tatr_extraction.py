"""Test Table Transformer extraction specifically."""

import logging
from pathlib import Path
from src.injestion.pipeline_extraction import (
    ingest_pdf_for_extraction,
    extract_with_specialized_extractors
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_table_methods(pdf_path: str):
    """Compare different table extraction methods."""
    
    logger.info(f"Testing table extraction methods on: {pdf_path}")
    
    # Step 1: Ingest PDF
    logger.info("Ingesting PDF...")
    extraction_data = ingest_pdf_for_extraction(
        pdf_path,
        detection_dpi=200,
        merge_strategy="weighted"
    )
    
    # Find pages with tables
    pages_with_tables = []
    for page_data in extraction_data:
        if len(page_data['organized_elements']['tables']) > 0:
            pages_with_tables.append(page_data['page_num'])
    
    logger.info(f"Found tables on pages: {pages_with_tables}")
    
    if not pages_with_tables:
        logger.warning("No tables found in document")
        return
    
    # Test different methods
    methods = ["camelot", "pdfplumber", "tatr"]
    
    for method in methods:
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing {method.upper()} method...")
        logger.info(f"{'='*60}")
        
        try:
            # Extract with current method
            extracted_content = extract_with_specialized_extractors(
                extraction_data,
                pdf_path,
                extract_images=True,
                table_method=method
            )
            
            # Show results
            logger.info(f"\nExtracted {len(extracted_content['tables'])} tables")
            
            for i, table in enumerate(extracted_content['tables']):
                logger.info(f"\nTable {i+1} (Page {table['page']}):")
                logger.info(f"  Method: {table.get('extraction_method', 'N/A')}")
                logger.info(f"  Shape: {table.get('shape', 'N/A')}")
                
                if method == "tatr" and 'structure_detection' in table:
                    struct = table['structure_detection']
                    logger.info(f"  TATR Structure: {struct}")
                
                if table.get('extracted_data'):
                    logger.info(f"  Data preview: {table['extracted_data'][:2] if len(table['extracted_data']) > 0 else 'Empty'}")
                elif table.get('raw_text'):
                    logger.info(f"  Raw text: {table['raw_text'][:100]}...")
                
                if table.get('extraction_error'):
                    logger.info(f"  Error: {table['extraction_error']}")
                    
        except Exception as e:
            logger.error(f"Error with {method}: {e}")


if __name__ == "__main__":
    # Test with a sample PDF
    pdf_path = "Liu et al. (2024).pdf"
    
    if Path(pdf_path).exists():
        test_table_methods(pdf_path)
    else:
        logger.error(f"PDF file not found: {pdf_path}")
        logger.info("Please provide a valid PDF path")