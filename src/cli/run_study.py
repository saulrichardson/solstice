"""CLI command for running streamlined fact-checking studies."""

import asyncio
import argparse
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.fact_check.orchestrators import StudyOrchestrator


def get_default_documents():
    """Get list of PDF names from clinical_files directory (without .pdf extension)."""
    clinical_dir = Path("data/clinical_files")
    if clinical_dir.exists():
        return [f.stem for f in clinical_dir.glob("*.pdf")]
    return []


def main():
    parser = argparse.ArgumentParser(
        description="Run fact-checking study to find supporting evidence",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--claims",
        dest="claims_file",
        required=True,
        help="Path to JSON file containing claims"
    )
    
    parser.add_argument(
        "--documents",
        nargs="+",
        default=get_default_documents(),
        help="List of PDF names to search (default: all documents in data/clinical_files)"
    )
    
    parser.add_argument(
        "--model",
        default="gpt-4.1",
        help="LLM model to use (default: gpt-4.1)"
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
    
    parser.add_argument(
        "--max-loops",
        type=int,
        default=2,
        help="Maximum completeness loops (default: 2)"
    )
    
    parser.add_argument(
        "--no-additional",
        dest="reverify_additional",
        action="store_false",
        default=True,
        help="Skip verification of additional evidence from completeness checker"
    )
    
    args = parser.parse_args()
    
    # Validate claims file exists
    if not Path(args.claims_file).exists():
        print(f"Error: Claims file not found: {args.claims_file}")
        sys.exit(1)
    
    # Configuration
    config = {
        "agent_config": {
            "model": args.model,
            "disable_cache": True
        },
        "max_completeness_loops": args.max_loops,
        "reverify_additional": args.reverify_additional
    }
    
    # Print study info
    print("Fact-Checking Study")
    print("=" * 30)
    print(f"Claims file: {args.claims_file}")
    print(f"Documents: {', '.join(args.documents)}")
    print(f"Model: {args.model}")
    print(f"Max loops: {args.max_loops}")
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