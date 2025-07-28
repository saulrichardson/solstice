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
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()