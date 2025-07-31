"""CLI command for running streamlined fact-checking studies."""

import asyncio
import logging
from pathlib import Path
import sys

from ..fact_check.orchestrators import StudyOrchestrator

# Configure logging to show all agent logs
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'  # Simple format for CLI output
)


def get_default_documents():
    """Get list of document names from cache that have extracted content."""
    cache_dir = Path("data/scientific_cache")
    documents = []
    if cache_dir.exists():
        # Only include documents that have extracted content
        for doc_dir in cache_dir.iterdir():
            if doc_dir.is_dir() and (doc_dir / "extracted" / "content.json").exists():
                # Skip marketing materials that shouldn't be in cache
                if doc_dir.name != "FlublokOnePage":
                    documents.append(doc_dir.name)
    return sorted(documents)


def main(claims_file=None, documents=None):
    """Main entry point.
    
    Args:
        claims_file: Path to claims JSON file
        documents: List of document names to analyze
    """
    # Use defaults if not provided
    if claims_file is None:
        claims_file = "data/claims/Flublok_Claims.json"
    if documents is None:
        documents = get_default_documents()
    
    # Fixed directories
    cache_dir = "data/scientific_cache"
    output_dir = "data/studies"
    
    # Validate claims file exists
    if not Path(claims_file).exists():
        print(f"Error: Claims file not found: {claims_file}")
        sys.exit(1)
    
    # Configuration
    config = {
        "agent_config": {
            "disable_cache": True
        },
        "max_concurrent_claims": 6  # Optimal for 32GB RAM, 10 CPU cores
    }
    
    # Print study info
    print("Fact-Checking Study")
    print("=" * 30)
    print(f"Claims file: {claims_file}")
    print(f"Documents: {', '.join(documents)}")
    print()
    
    # Create and run orchestrator
    orchestrator = StudyOrchestrator(
        claims_file=Path(claims_file),
        documents=documents,
        cache_dir=Path(cache_dir),
        output_dir=Path(output_dir),
        config=config
    )
    
    # Run async
    asyncio.run(orchestrator.process())


