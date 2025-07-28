"""
Main entry point for fact-checking pipeline.

Usage:
    python -m src.fact_check <pdf_name> [options]
    
Options:
    --claims-file <file>    Use claims from JSON file in data/claims/
    --claims <claim1> ...   Provide claims directly
    --config <file>         Use custom config file
    --model <model>         LLM model to use (default: gpt-4.1)
    
Examples:
    # Use claims file matching PDF name
    python -m src.fact_check FlublokPI
    
    # Use specific claims file
    python -m src.fact_check FlublokPI --claims-file Flublok_Claims.json
    
    # Provide claims directly
    python -m src.fact_check FlublokPI --claims "Flublok contains 45 mcg HA per strain"
    
    # Use custom config
    python -m src.fact_check FlublokPI --config my_config.json
"""

import asyncio
import sys
import argparse
from pathlib import Path

from .pipeline import FactCheckPipeline


def main():
    parser = argparse.ArgumentParser(
        description="Run fact-checking pipeline on extracted PDFs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument("pdf_name", help="Name of the PDF to fact-check")
    parser.add_argument("--claims-file", help="Claims file in data/claims/")
    parser.add_argument("--claims", nargs="+", help="Claims to verify")
    parser.add_argument("--config", help="Custom config file")
    parser.add_argument("--model", default="gpt-4.1", help="LLM model to use")
    parser.add_argument("--continue-on-error", action="store_true", 
                        help="Continue pipeline if an agent fails")
    
    args = parser.parse_args()
    
    # Build config from arguments
    config = {
        "continue_on_error": args.continue_on_error,
        "agents": {
            "text_evidence_finder": {
                "model": args.model
            }
        }
    }
    
    # Determine claims source
    if args.config:
        # Use custom config file
        config_file = Path(args.config)
        if not config_file.exists():
            print(f"Error: Config file '{config_file}' not found")
            sys.exit(1)
        pipeline = FactCheckPipeline.from_config_file(args.pdf_name, config_file)
    else:
        # Build config from command line
        if args.claims:
            # Direct claims from command line
            config["agents"]["text_evidence_finder"]["standalone_claims"] = args.claims
        elif args.claims_file:
            # Specific claims file
            config["agents"]["text_evidence_finder"]["claims_file"] = args.claims_file
        else:
            # Default: look for claims file matching PDF name
            default_claims_file = f"{args.pdf_name}_Claims.json"
            claims_path = Path("data/claims") / default_claims_file
            if claims_path.exists():
                config["agents"]["text_evidence_finder"]["claims_file"] = default_claims_file
                print(f"Using claims file: {default_claims_file}")
            else:
                print(f"No claims provided. Options:")
                print(f"  1. Create {claims_path}")
                print(f"  2. Use --claims-file <file>")
                print(f"  3. Use --claims <claim1> <claim2> ...")
                print(f"  4. Use --config <config.json>")
                sys.exit(1)
        
        pipeline = FactCheckPipeline(args.pdf_name, config=config)
    
    # Run pipeline
    try:
        results = asyncio.run(pipeline.run())
        print(f"\nPipeline completed successfully for {args.pdf_name}")
        print(f"Results saved to: {pipeline.agents_dir}")
        
        # Show summary
        if "text_evidence_finder" in results:
            summary = results["text_evidence_finder"].get("summary", {})
            print(f"\nSummary:")
            print(f"  Total claims: {summary.get('total_claims', 0)}")
            print(f"  Supporting: {summary.get('supporting_claims', 0)}")
            print(f"  Contradicting: {summary.get('contradicting_claims', 0)}")
            print(f"  Insufficient evidence: {summary.get('insufficient_evidence', 0)}")
    except Exception as e:
        print(f"Pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()