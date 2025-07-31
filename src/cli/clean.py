#!/usr/bin/env python3
"""CLI for cleaning cache directory."""

import shutil
from pathlib import Path


def main():
    """Remove entire cache directory."""
    # Directories to be fully removed in a cache clear
    cache_dirs = [
        Path("data/scientific_cache"),  # default scientific pipeline output
        Path("data/marketing_cache"),   # marketing-material pipeline output
        Path("data/gateway_cache"),     # audit logs from the gateway service
    ]

    studies_dir = Path("data/studies")  # finished fact-checking studies
    
    # Check if there is anything to delete
    if not any(d.exists() for d in cache_dirs) and not studies_dir.exists():
        print("No cache or studies directories found.")
        return
    
    print("This will remove:")
    for d in cache_dirs:
        if d.exists():
            print(f"  • {d} (cache)")
    if studies_dir.exists():
        print(f"  • {studies_dir} (all study results)")
    
    response = input("\nAre you sure? Type 'yes' to confirm: ")
    
    if response.lower() != 'yes':
        print("Cancelled.")
        return
    
    # Remove directories
    for d in cache_dirs:
        if d.exists():
            shutil.rmtree(d)
            print(f"✓ Removed {d}")
    
    if studies_dir.exists():
        shutil.rmtree(studies_dir)
        print(f"✓ Removed {studies_dir}")
    
    print("\nCache cleared.")
