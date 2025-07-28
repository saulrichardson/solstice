"""Rerun ingestion on the Arunachalam paper."""

from pathlib import Path
from src.injestion.pipeline import ingest_pdf

# Run the pipeline
pdf_path = Path("data/clinical_files/Arunachalam et al. (2021).pdf")
print(f"Processing: {pdf_path}")

# Run ingestion
document = ingest_pdf(pdf_path)

print(f"\nIngestion complete!")
print(f"Total pages: {len(document.reading_order)}")
print(f"Total blocks: {len(document.blocks)}")

# Check page 3 (index 2) specifically
page_2_order = document.reading_order[2]
print(f"\nPage 3 reading order: {len(page_2_order)} elements")

# Get the title that was problematic before
from src.injestion.storage.paths import doc_id
cache_id = doc_id(pdf_path)
print(f"\nCache folder: {cache_id}")

# Show some details about page 3
page_2_blocks = [b for b in document.blocks if b.page_index == 2]
print(f"\nPage 3 blocks:")
for block in page_2_blocks:
    if "TERTIARY STRUCTURE" in (block.text or ""):
        print(f"Found title: {block.id}")
        print(f"  Position in reading order: {page_2_order.index(block.id) + 1}")
        print(f"  BBox: {block.bbox}")
        print(f"  Text preview: {block.text[:50]}...")