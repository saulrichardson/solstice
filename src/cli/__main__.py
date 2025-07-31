#!/usr/bin/env python3
"""Main CLI entry point for all commands."""

import argparse
import sys


def main():
    """Main CLI dispatcher."""
    parser = argparse.ArgumentParser(
        description="Solstice CLI - Process clinical documents",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(
        dest="command",
        help="Available commands",
        required=True
    )
    
    # Ingest command
    ingest_parser = subparsers.add_parser(
        "ingest",
        help="Process PDFs from data/clinical_files/"
    )
    ingest_parser.add_argument(
        "--output-dir",
        help="Custom output directory (default: data/scientific_cache)"
    )
    
    # Run study command  
    study_parser = subparsers.add_parser(
        "run-study",
        help="Run fact-checking study across claims and documents"
    )
    study_parser.add_argument(
        "--claims",
        help="Claims file (default: data/claims/Flublok_Claims.json)"
    )
    study_parser.add_argument(
        "--documents",
        nargs="+",
        help="Documents to analyze (default: all cached documents)"
    )
    
    # Marketing ingest command
    marketing_parser = subparsers.add_parser(
        "ingest-marketing",
        help="Process marketing PDFs with specialized layout detection"
    )
    marketing_parser.add_argument(
        "pdf_path",
        help="Path to marketing PDF file"
    )
    marketing_parser.add_argument(
        "--output-dir",
        help="Custom output directory (default: data/marketing_cache)"
    )
    
    # Clear cache command
    clear_cache_parser = subparsers.add_parser(
        "clear-all-cache",
        help="Remove entire cache directory (requires confirmation)"
    )
    
    args = parser.parse_args()
    
    # Route to appropriate command
    if args.command == "ingest":
        from .ingest import main as ingest_main
        ingest_main(output_dir=args.output_dir)
    elif args.command == "run-study":
        from .run_study import main as study_main
        study_main(claims_file=args.claims, documents=args.documents)
    elif args.command == "ingest-marketing":
        from .ingest_marketing import main as marketing_main
        marketing_main(pdf_path=args.pdf_path, output_dir=args.output_dir)
    elif args.command == "clear-all-cache":
        from .clean import main as clean_main
        clean_main()
    else:
        parser.print_help()
        sys.exit(1)


# When run as python -m src.cli, this file is executed directly
main()