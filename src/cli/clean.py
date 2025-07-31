#!/usr/bin/env python3
"""CLI for cleaning cache directory."""

import shutil
from pathlib import Path


def main():
    """Remove entire cache directory."""
    cache_dir = Path("data/scientific_cache")
    studies_dir = Path("data/studies")
    
    if not cache_dir.exists() and not studies_dir.exists():
        print("No cache or studies directories found.")
        return
    
    print("This will remove:")
    if cache_dir.exists():
        print(f"  • {cache_dir} (all cached documents)")
    if studies_dir.exists():
        print(f"  • {studies_dir} (all study results)")
    
    response = input("\nAre you sure? Type 'yes' to confirm: ")
    
    if response.lower() != 'yes':
        print("Cancelled.")
        return
    
    # Remove directories
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
        print(f"✓ Removed {cache_dir}")
    
    if studies_dir.exists():
        shutil.rmtree(studies_dir)
        print(f"✓ Removed {studies_dir}")
    
    print("\nCache cleared.")