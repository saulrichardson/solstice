"""CLI command for running fact-checking studies."""

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
    # Check if we have defaults available
    default_claims = "data/claims/Flublok_Claims.json"
    has_default_claims = Path(default_claims).exists()
    available_docs = get_default_documents()
    
    parser = argparse.ArgumentParser(
        description="Run fact-checking study across multiple claims and documents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  # Use all defaults (Flublok claims and all documents)
  python -m src.cli run-study
  
  # Use default claims with specific documents
  python -m src.cli run-study --documents FlublokPI "Liu et al. (2024)"
  
  # Use custom claims file
  python -m src.cli run-study --claims path/to/claims.json
  
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
        "--continue-on-error",
        action="store_true",
        help="Continue processing even if an agent fails"
    )
    
    parser.add_argument(
        "--agents",
        nargs="+",
        choices=["supporting_evidence", "regex_verifier", "evidence_critic", "evidence_judge"],
        default=["supporting_evidence", "regex_verifier", "evidence_critic", "evidence_judge"],
        help="Which agents to run (default: all agents)"
    )
    
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output (shows LLM calls and responses)"
    )

    # ------------------------------------------------------------------
    # Caching control – we *disable* server-side caching by default so every
    # run gets a fresh completion.  Power users can re-enable it with
    # --enable-cache.
    # ------------------------------------------------------------------

    parser.add_argument(
        "--enable-cache",
        action="store_true",
        help="Allow OpenAI server-side caching (default: disabled)"
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
    
    # Clear cache if requested
    
    # Configure logging if debug mode
    if args.debug:
        import logging
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            force=True
        )
        # Also set httpx logging for API calls
        logging.getLogger("httpx").setLevel(logging.INFO)
        logging.getLogger("httpcore").setLevel(logging.INFO)
        print("🔍 Debug mode enabled - LLM calls will be shown\n")
    
    # Build config
    config = {
        "agent_config": {
            "model": args.model,
            "debug": args.debug,
            # Disable cache unless user explicitly requested enabling it
            "disable_cache": not args.enable_cache,
        },
        "continue_on_error": args.continue_on_error,
        "agents": args.agents
    }

    
    # Create orchestrator
    orchestrator = StudyOrchestrator(
        claims_file=args.claims_file,
        documents=args.documents,
        cache_dir=Path(args.cache_dir),
        config=config
    )
    
    print(f"Fact-Checking Study")
    print(f"==================")
    print(f"Claims file: {args.claims_file}")
    print(f"Documents: {', '.join(args.documents)}")
    print(f"Model: {args.model}")
    print(f"Agents: {', '.join(args.agents)}")
    print(f"Total claims: {len(orchestrator.claims)}")
    
    # Run study
    try:
        results = asyncio.run(orchestrator.run())
        
        # Save results
        output_path = Path(args.output) if args.output else None
        saved_path = orchestrator.save_results(output_path)
        
    except KeyboardInterrupt:
        print("\n\nStudy interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nStudy failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
