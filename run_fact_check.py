#!/usr/bin/env python3
"""Driver script for running the fact-checking pipeline"""

import asyncio
import argparse
import json
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fact_check.pipeline import FactCheckPipeline

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_claims_from_file(claims_file: Path) -> list:
    """Load claims from a text file (one claim per line) or JSON file"""
    if claims_file.suffix == '.json':
        with open(claims_file, 'r') as f:
            data = json.load(f)
            # Handle both list and dict with 'claims' key
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'claims' in data:
                return data['claims']
            else:
                raise ValueError("JSON file must contain a list or dict with 'claims' key")
    else:
        # Text file - one claim per line
        with open(claims_file, 'r') as f:
            return [line.strip() for line in f if line.strip()]


async def main():
    parser = argparse.ArgumentParser(description="Run fact-checking pipeline on a PDF")
    parser.add_argument("pdf_name", help="Name of the PDF directory in cache")
    parser.add_argument(
        "--claims", 
        nargs="*", 
        help="Claims to verify (can specify multiple)"
    )
    parser.add_argument(
        "--claims-file",
        type=Path,
        help="File containing claims to verify (text or JSON)"
    )
    parser.add_argument(
        "--config", 
        type=Path,
        help="Pipeline configuration file (JSON)"
    )
    parser.add_argument(
        "--model",
        default="gpt-4.1",
        help="LLM model to use (default: gpt-4.1)"
    )
    parser.add_argument(
        "--gateway-url",
        help="Gateway URL (defaults to environment)"
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue pipeline even if an agent fails"
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default="data/cache",
        help="Cache directory (default: data/cache)"
    )
    
    args = parser.parse_args()
    
    # Build configuration
    if args.config:
        # Load from config file
        with open(args.config, 'r') as f:
            config = json.load(f)
    else:
        # Build from command line arguments
        config = {
            "continue_on_error": args.continue_on_error,
            "agents": {
                "claim_verifier": {
                    "model": args.model
                }
            }
        }
        
        if args.gateway_url:
            config["agents"]["claim_verifier"]["gateway_url"] = args.gateway_url
        
        # Handle claims
        claims = []
        if args.claims:
            claims.extend(args.claims)
        if args.claims_file:
            claims.extend(load_claims_from_file(args.claims_file))
        
        if claims:
            config["claims"] = claims
    
    # Check if PDF directory exists
    pdf_dir = Path(args.cache_dir) / args.pdf_name
    if not pdf_dir.exists():
        logger.error(f"PDF directory not found: {pdf_dir}")
        logger.error("Make sure you've run the ingestion pipeline first")
        return 1
    
    # Check if extracted content exists
    content_file = pdf_dir / "extracted" / "content.json"
    if not content_file.exists():
        logger.error(f"Extracted content not found: {content_file}")
        logger.error("Make sure the ingestion pipeline completed successfully")
        return 1
    
    # Create and run pipeline
    try:
        pipeline = FactCheckPipeline(
            args.pdf_name,
            cache_dir=args.cache_dir,
            config=config
        )
        
        logger.info(f"Starting fact-check pipeline for: {args.pdf_name}")
        if claims:
            logger.info(f"Verifying {len(claims)} claims")
        
        # Run the pipeline
        results = await pipeline.run()
        
        # Print summary
        print("\n" + "="*60)
        print("FACT-CHECK PIPELINE COMPLETED")
        print("="*60)
        
        # Get verification results
        if "claim_verifier" in results:
            verifier_results = results["claim_verifier"]
            summary = verifier_results.get("summary", {})
            
            print(f"\nDocument: {args.pdf_name}")
            print(f"Total claims verified: {summary.get('total_claims', 0)}")
            print(f"Supporting claims: {summary.get('supporting_claims', 0)}")
            print(f"Contradicting claims: {summary.get('contradicting_claims', 0)}")
            print(f"Insufficient evidence: {summary.get('insufficient_evidence', 0)}")
            print(f"Errors: {summary.get('errors', 0)}")
            
            # Show detailed results
            if verifier_results.get("verification_results"):
                print("\nDetailed Results:")
                print("-" * 60)
                for i, result in enumerate(verifier_results["verification_results"], 1):
                    print(f"\n{i}. Claim: {result['claim']}")
                    print(f"   Verdict: {result['verdict']}")
                    print(f"   Confidence: {result['confidence']}")
                    
                    if result.get("reasoning_steps"):
                        print("   Evidence:")
                        for step in result["reasoning_steps"]:
                            print(f"   - {step['reasoning']}")
                            if step.get('quote'):
                                quote = step['quote']
                                if len(quote) > 100:
                                    quote = quote[:100] + "..."
                                print(f"     Quote: \"{quote}\"")
        
        # Show output location
        output_dir = pdf_dir / "agents"
        print(f"\nFull results saved to: {output_dir}")
        print(f"- Pipeline manifest: {output_dir}/pipeline_manifest.json")
        print(f"- Pipeline results: {output_dir}/pipeline_results.json")
        print(f"- Agent outputs: {output_dir}/*/output.json")
        
        return 0
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))