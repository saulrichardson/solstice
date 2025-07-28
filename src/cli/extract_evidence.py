"""CLI command for claim-centric evidence extraction."""

import asyncio
import argparse
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.fact_check.claim_orchestrator import ClaimOrchestrator


def get_default_documents():
    """Get list of PDF names from clinical_files directory (without .pdf extension)."""
    clinical_dir = Path("data/clinical_files")
    if clinical_dir.exists():
        return [f.stem for f in clinical_dir.glob("*.pdf")]
    return []


def main():
    # Check if we have defaults available
    default_claims = "data/claims/Flublok_Claims.json"
    has_default_claims = Path(default_claims).exists()
    available_docs = get_default_documents()
    
    parser = argparse.ArgumentParser(
        description="Extract supporting evidence for claims across multiple documents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  # Use all defaults (Flublok claims and all documents)
  python -m src.cli extract-evidence
  
  # Use default claims with specific documents
  python -m src.cli extract-evidence --documents FlublokPI "Liu et al. (2024)"
  
  # Use custom claims file
  python -m src.cli extract-evidence --claims path/to/claims.json
  
Available documents: {', '.join(available_docs) if available_docs else 'None found'}
Default claims: {default_claims if has_default_claims else 'Not found'}
"""
    )
    
    parser.add_argument(
        "--claims",
        dest="claims_file",
        default=default_claims if has_default_claims else None,
        help=f"Path to JSON file containing claims (default: {default_claims})"
    )
    
    parser.add_argument(
        "--documents",
        nargs="+",
        default=available_docs,
        help="List of PDF names to search (default: all documents in data/clinical_files)"
    )
    
    parser.add_argument(
        "--model",
        default="gpt-4.1",
        help="LLM model to use for extraction (default: gpt-4.1)"
    )
    
    parser.add_argument(
        "--output",
        help="Output file path for results"
    )
    
    parser.add_argument(
        "--cache-dir",
        default="data/cache",
        help="Cache directory (default: data/cache)"
    )
    
    parser.add_argument(
        "--include-context",
        action="store_true",
        help="Include surrounding context with snippets"
    )
    
    parser.add_argument(
        "--max-snippets",
        type=int,
        default=10,
        help="Maximum snippets per claim per document (default: 10)"
    )
    
    args = parser.parse_args()
    
    # Validate inputs
    if not args.claims_file:
        print("Error: No claims file specified and no default claims found.")
        print("Please create data/claims/Flublok_Claims.json or specify --claims")
        sys.exit(1)
    
    if not args.documents:
        print("Error: No documents found in data/clinical_files/")
        print("Please run ingestion first or specify --documents")
        sys.exit(1)
    
    # Build config
    config = {
        "agent_config": {
            "model": args.model,
            "include_context": args.include_context,
            "max_snippets_per_claim": args.max_snippets
        }
    }
    
    # Create orchestrator
    orchestrator = ClaimOrchestrator(
        claims_file=args.claims_file,
        documents=args.documents,
        cache_dir=Path(args.cache_dir),
        config=config
    )
    
    print(f"Evidence Extraction")
    print(f"==================")
    print(f"Claims file: {args.claims_file}")
    print(f"Documents: {', '.join(args.documents)}")
    print(f"Model: {args.model}")
    print(f"Total claims: {len(orchestrator.claims)}")
    
    # Run extraction
    try:
        results = asyncio.run(orchestrator.run())
        
        # Save results
        output_path = Path(args.output) if args.output else None
        saved_path = orchestrator.save_results(output_path)
        
        # Print final summary
        print(f"\n{'='*60}")
        print(f"Extraction Complete")
        print(f"{'='*60}")
        print(f"Total claims processed: {results['summary']['total_claims']}")
        print(f"Claims with evidence: {results['summary']['claims_with_evidence']}")
        print(f"Total snippets extracted: {results['summary']['total_snippets_extracted']}")
        print(f"\nDocument coverage:")
        for doc, count in results['summary']['document_coverage'].items():
            print(f"  {doc}: {count} claims with evidence")
        
    except KeyboardInterrupt:
        print("\n\nExtraction interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nExtraction failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()