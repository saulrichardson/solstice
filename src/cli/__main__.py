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
    
    # Run study command
    study_parser = subparsers.add_parser(
        "run-study",
        help="Run fact-checking study across claims and documents (uses Flublok defaults)"
    )
    
    # Legacy extract evidence command (deprecated)
    evidence_parser = subparsers.add_parser(
        "extract-evidence",
        help="[DEPRECATED - use run-study] Extract supporting evidence"
    )
    
    # Parse only known args to get the command
    args, remaining = parser.parse_known_args()
    
    # Route to appropriate command
    if args.command == "ingest":
        from .ingest import main as ingest_main
        # Pass through to ingest CLI
        sys.argv = ["ingest"]
        if args.output_dir:
            sys.argv.extend(["--output-dir", args.output_dir])
        ingest_main()
    elif args.command == "run-study":
        from .run_study import main as study_main
        # Set sys.argv to include remaining args
        sys.argv = [sys.argv[0]] + remaining
        study_main()
    elif args.command == "extract-evidence":
        # Deprecated - redirect to run-study
        print("Note: extract-evidence is deprecated. Using run-study instead.\n")
        from .run_study import main as study_main
        sys.argv = [sys.argv[0]] + remaining
        study_main()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()