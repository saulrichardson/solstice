"""Command-line interface for the document viewer."""

import argparse
import logging
from pathlib import Path
import webbrowser
import sys

from .aggregator import DocumentAggregator
from .html_generator import UnifiedHTMLGenerator

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Generate unified views of extracted Solstice documents"
    )
    
    parser.add_argument(
        '--cache-dir',
        type=Path,
        default=Path('data/cache'),
        help='Path to the cache directory containing extracted documents (default: data/cache)'
    )
    
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('unified_documents'),
        help='Output directory or file path (default: unified_documents)'
    )
    
    parser.add_argument(
        '--format',
        choices=['site', 'single-html', 'json'],
        default='site',
        help='Output format: site (multi-page HTML), single-html (one file), or json'
    )
    
    parser.add_argument(
        '--no-images',
        action='store_true',
        help='Exclude images from the output'
    )
    
    parser.add_argument(
        '--open',
        action='store_true',
        help='Open the generated output in a web browser'
    )
    
    parser.add_argument(
        '--search',
        type=str,
        help='Search for a specific term across all documents'
    )
    
    args = parser.parse_args()
    
    # Initialize aggregator
    logger.info(f"Scanning for documents in {args.cache_dir}")
    aggregator = DocumentAggregator(args.cache_dir)
    
    if not aggregator.documents:
        logger.error("No extracted documents found in the cache directory")
        sys.exit(1)
    
    logger.info(f"Found {len(aggregator.documents)} documents")
    
    # Handle search if requested
    if args.search:
        logger.info(f"Searching for: {args.search}")
        results = aggregator.search_content(args.search)
        
        if not results:
            logger.info("No matches found")
        else:
            logger.info(f"Found {len(results)} matches:")
            for i, result in enumerate(results[:10]):  # Show first 10
                print(f"\n[{i+1}] {result['document']} - Page {result['page'] + 1}")
                print(f"    Type: {result['role']}")
                print(f"    Preview: {result['match_preview']}")
            
            if len(results) > 10:
                print(f"\n... and {len(results) - 10} more matches")
        
        return
    
    # Generate output based on format
    generator = UnifiedHTMLGenerator(aggregator)
    
    if args.format == 'site':
        logger.info(f"Generating multi-page HTML site at {args.output}")
        index_path = generator.generate_unified_site(
            args.output,
            include_images=not args.no_images
        )
        output_path = index_path
        
    elif args.format == 'single-html':
        output_path = args.output
        if output_path.is_dir():
            output_path = output_path / 'unified_documents.html'
        
        logger.info(f"Generating single HTML file at {output_path}")
        generator.generate_single_page_html(
            output_path,
            include_images=not args.no_images
        )
        
    elif args.format == 'json':
        output_path = args.output
        if output_path.is_dir():
            output_path = output_path / 'unified_documents.json'
        
        logger.info(f"Exporting combined JSON to {output_path}")
        aggregator.export_combined_json(output_path)
    
    logger.info(f"Successfully generated output: {output_path}")
    
    # Show statistics
    stats = aggregator.get_statistics()
    print("\nDocument Statistics:")
    print(f"  Total documents: {stats['total_documents']}")
    print(f"  Total pages: {stats['total_pages']}")
    print(f"  Total blocks: {stats['total_blocks']}")
    print(f"  Total figures: {stats['total_figures']}")
    print(f"  Total tables: {stats['total_tables']}")
    
    # Open in browser if requested
    if args.open and args.format in ['site', 'single-html']:
        logger.info("Opening in web browser...")
        webbrowser.open(str(output_path))


if __name__ == '__main__':
    main()