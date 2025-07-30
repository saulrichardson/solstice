"""CLI command for running streamlined fact-checking studies."""

import asyncio
import argparse
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.fact_check.orchestrators import StudyOrchestrator


def get_default_documents():
    """Get list of document names from cache that have extracted content."""
    cache_dir = Path("data/cache")
    documents = []
    if cache_dir.exists():
        # Only include documents that have extracted content
        for doc_dir in cache_dir.iterdir():
            if doc_dir.is_dir() and (doc_dir / "extracted" / "content.json").exists():
                documents.append(doc_dir.name)
    return sorted(documents)


def main():
    parser = argparse.ArgumentParser(
        description="Run fact-checking study to find supporting evidence",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--claims",
        dest="claims_file",
        default="data/claims/Flublok_Claims.json",
        help="Path to JSON file containing claims (default: data/claims/Flublok_Claims.json)"
    )
    
    parser.add_argument(
        "--documents",
        nargs="+",
        default=get_default_documents(),
        help="List of document names to search (default: all documents in cache with extracted content)"
    )
    
    
    parser.add_argument(
        "--cache-dir",
        default="data/cache",
        help="Cache directory (default: data/cache)"
    )
    
    parser.add_argument(
        "--output-dir",
        default="data/studies",
        help="Output directory for results (default: data/studies)"
    )
    
    
    args = parser.parse_args()
    
    # Validate claims file exists
    if not Path(args.claims_file).exists():
        print(f"Error: Claims file not found: {args.claims_file}")
        sys.exit(1)
    
    # Configuration
    config = {
        "agent_config": {
            "disable_cache": True
        }
    }
    
    # Print study info
    print("Fact-Checking Study")
    print("=" * 30)
    print(f"Claims file: {args.claims_file}")
    print(f"Documents: {', '.join(args.documents)}")
    print()
    
    # Create and run orchestrator
    orchestrator = StudyOrchestrator(
        claims_file=Path(args.claims_file),
        documents=args.documents,
        cache_dir=Path(args.cache_dir),
        output_dir=Path(args.output_dir),
        config=config
    )
    
    # Run async
    asyncio.run(orchestrator.process())


if __name__ == "__main__":
    main()