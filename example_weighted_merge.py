#!/usr/bin/env python3
"""Example of using the weighted merge approach (Approach 4)."""

from pathlib import Path
from src.injestion.pipeline_simple import ingest_pdf_simple


def main():
    """Demonstrate the weighted merge approach."""
    
    pdf_path = Path("Liu et al. (2024).pdf")
    
    print("Using Weighted Merge Approach (Approach 4)")
    print("=" * 50)
    print("This approach:")
    print("1. Merges overlapping boxes of the same type")
    print("2. Resolves conflicts using weighted scoring:")
    print("   - 70% weight on confidence score")
    print("   - 30% weight on box area")
    print("=" * 50)
    
    # Process with default settings (weighted resolution)
    pages = ingest_pdf_simple(pdf_path)
    
    print(f"\nProcessed {len(pages)} pages")
    
    for page in pages:
        print(f"\nPage {page.page_index + 1}:")
        print(f"  Total boxes: {len(page.boxes)}")
        
        # Count by type
        type_counts = {}
        for box in page.boxes:
            type_counts[box.label] = type_counts.get(box.label, 0) + 1
        
        print("  Box types:")
        for label, count in sorted(type_counts.items()):
            print(f"    {label}: {count}")
    
    # You can also customize the weights
    print("\n" + "=" * 50)
    print("Customizing the approach:")
    print("=" * 50)
    
    # Example: Give more weight to confidence
    custom_pages = ingest_pdf_simple(
        pdf_path,
        conflict_resolution="confident"  # Use pure confidence-based resolution
    )
    
    # Example: Use the old priority-based approach
    priority_pages = ingest_pdf_simple(
        pdf_path,
        conflict_resolution="priority"  # List > Text hierarchy
    )
    
    # Example: Disable conflict resolution entirely
    no_resolution_pages = ingest_pdf_simple(
        pdf_path,
        resolve_conflicts=False  # Just merge, don't resolve conflicts
    )
    
    print("Different strategies produce different results:")
    print(f"  Weighted (default): {len(pages[0].boxes)} boxes on page 1")
    print(f"  Confidence-based: {len(custom_pages[0].boxes)} boxes on page 1")
    print(f"  Priority-based: {len(priority_pages[0].boxes)} boxes on page 1")
    print(f"  No resolution: {len(no_resolution_pages[0].boxes)} boxes on page 1")


if __name__ == "__main__":
    main()