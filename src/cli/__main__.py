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
        help="Available commands"
    )
    
    # Ingest command
    ingest_parser = subparsers.add_parser(
        "ingest",
        help="Process PDFs with layout detection and text extraction"
    )
    ingest_parser.add_argument(
        "--output-dir",
        help="Custom output directory"
    )
    
    # Extract evidence command
    evidence_parser = subparsers.add_parser(
        "extract-evidence",
        help="Extract supporting evidence for claims across documents"
    )
    evidence_parser.add_argument(
        "claims_file",
        help="Path to JSON file containing claims"
    )
    evidence_parser.add_argument(
        "documents",
        nargs="+",
        help="List of PDF names to search"
    )
    evidence_parser.add_argument(
        "--model",
        default="gpt-4.1",
        help="LLM model to use"
    )
    evidence_parser.add_argument(
        "--output",
        help="Output file path"
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Route to appropriate command
    if args.command == "ingest":
        from .ingest import main as ingest_main
        # Pass through to ingest CLI
        sys.argv = ["ingest"]
        if args.output_dir:
            sys.argv.extend(["--output-dir", args.output_dir])
        ingest_main()
    elif args.command == "extract-evidence":
        from .extract_evidence import main as extract_main
        # Build new sys.argv for extract_evidence
        sys.argv = ["extract-evidence", args.claims_file] + args.documents
        if args.model:
            sys.argv.extend(["--model", args.model])
        if args.output:
            sys.argv.extend(["--output", args.output])
        extract_main()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()