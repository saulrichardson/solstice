"""Example usage of the document viewer module."""

from pathlib import Path
from viewer.aggregator import DocumentAggregator
from viewer.html_generator import UnifiedHTMLGenerator


def main():
    # Initialize aggregator with cache directory
    cache_dir = Path("data/cache")
    aggregator = DocumentAggregator(cache_dir)
    
    print(f"Found {len(aggregator.documents)} documents:")
    for doc in aggregator.documents:
        print(f"  - {doc.name}: {len(doc.blocks)} blocks")
    
    # Example 1: Search across all documents
    print("\nSearching for 'vaccine':")
    results = aggregator.search_content("vaccine")
    for result in results[:5]:  # Show first 5 results
        print(f"  Found in {result['document']} (page {result['page']}): {result['match_preview']}")
    
    # Example 2: Get all figures
    print(f"\nTotal figures across all documents: {len(aggregator.get_all_figures())}")
    
    # Example 3: Generate unified HTML view
    generator = UnifiedHTMLGenerator(aggregator)
    
    # Option A: Multi-page site
    print("\nGenerating multi-page HTML site...")
    site_path = generator.generate_unified_site(Path("output/unified_site"))
    print(f"  Site generated at: {site_path}")
    
    # Option B: Single HTML file
    print("\nGenerating single HTML file...")
    single_path = generator.generate_single_page_html(Path("output/unified_single.html"))
    print(f"  Single file generated at: {single_path}")
    
    # Example 4: Export combined JSON for custom processing
    print("\nExporting combined JSON...")
    json_path = aggregator.export_combined_json(Path("output/combined.json"))
    print(f"  JSON exported to: {json_path}")
    
    # Example 5: Get statistics
    stats = aggregator.get_statistics()
    print("\nDocument Statistics:")
    print(f"  Total pages: {stats['total_pages']}")
    print(f"  Total blocks: {stats['total_blocks']}")
    print(f"  Total figures: {stats['total_figures']}")
    print(f"  Total tables: {stats['total_tables']}")


if __name__ == "__main__":
    main()