#!/usr/bin/env python3
"""Test the catalog pipeline V2 with clinical files."""

import json
import logging
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree

from src.injestion.catalog_pipeline_v2 import create_catalog_v2

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

console = Console()


def display_catalog_contents(catalog_dir: Path):
    """Display catalog contents in a nice format."""
    # Load catalog
    with open(catalog_dir / "catalog.json") as f:
        catalog = json.load(f)
    
    # Display summary
    console.print(Panel.fit(
        f"[bold green]Catalog Created Successfully![/bold green]\n"
        f"Location: {catalog_dir}\n"
        f"Total Elements: {catalog['statistics']['total_elements']}\n"
        f"Text Extracted: {catalog['statistics']['text_extracted']}\n"
        f"Image References: {catalog['statistics']['image_references']}",
        title="Catalog Summary"
    ))
    
    # Display element types
    table = Table(title="Elements by Type")
    table.add_column("Type", style="cyan")
    table.add_column("Count", style="magenta")
    
    for elem_type, count in sorted(catalog['statistics']['by_type'].items()):
        table.add_row(elem_type, str(count))
    
    console.print(table)
    
    # Display file structure
    tree = Tree(f"[bold]{catalog_dir.name}/[/bold]")
    
    # Add main files
    tree.add("📄 catalog.json")
    tree.add("📄 elements.json")
    tree.add("📄 text_elements.json")
    tree.add("📄 index_by_type.json")
    tree.add("📄 pdf_reference.json")
    tree.add("📄 summary_report.md")
    
    # Add directories
    stages = tree.add("📁 stages/")
    stages.add("📄 stage1_layout_detection.json")
    stages.add("📄 stage2_visual_reordering.json")
    stages.add("📄 stage3_text_extraction.json")
    
    text_content = tree.add("📁 text_content/")
    text_content.add("📄 elem_001_0001.txt")
    text_content.add("📄 elem_001_0002.txt")
    text_content.add("📄 ... (text files)")
    
    thumbnails = tree.add("📁 thumbnails/")
    thumbnails.add("🖼️ elem_001_0001.png")
    thumbnails.add("🖼️ elem_001_0002.png")
    thumbnails.add("🖼️ ... (thumbnails)")
    
    console.print(tree)
    
    # Show sample text content
    text_elements = catalog['elements'][:3]  # First 3 elements
    
    console.print("\n[bold]Sample Extracted Text:[/bold]")
    for elem in text_elements:
        if elem.get('content'):
            console.print(Panel(
                f"[yellow]Element ID:[/yellow] {elem['element_id']}\n"
                f"[yellow]Type:[/yellow] {elem['element_type']}\n"
                f"[yellow]Page:[/yellow] {elem['page_num']}\n"
                f"[yellow]Content:[/yellow]\n{elem['content'][:200]}..."
                if len(elem.get('content', '')) > 200 else elem.get('content', ''),
                title=f"Element {elem['element_id']}"
            ))


def test_single_pdf(pdf_path: Path):
    """Test catalog creation on a single PDF."""
    console.print(f"\n[bold blue]Testing catalog creation for:[/bold blue] {pdf_path.name}")
    
    try:
        # Create catalog
        catalog_dir = create_catalog_v2(
            pdf_path,
            catalog_name=f"test_{pdf_path.stem}",
            output_dir="output/test_catalogs"
        )
        
        # Display results
        display_catalog_contents(catalog_dir)
        
        return True
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Test the catalog pipeline with clinical files."""
    console.print("[bold]PDF Catalog Pipeline V2 Test[/bold]\n")
    
    # Get clinical files
    clinical_dir = Path("input/Clinical Files")
    
    if not clinical_dir.exists():
        console.print(f"[red]Clinical files directory not found: {clinical_dir}[/red]")
        return
    
    pdf_files = list(clinical_dir.glob("*.pdf"))
    
    if not pdf_files:
        console.print(f"[red]No PDF files found in: {clinical_dir}[/red]")
        return
    
    console.print(f"Found {len(pdf_files)} PDF files:\n")
    for i, pdf in enumerate(pdf_files, 1):
        console.print(f"{i}. {pdf.name}")
    
    # Test with first PDF
    console.print("\n[bold]Testing with first PDF...[/bold]")
    test_pdf = pdf_files[0]
    
    success = test_single_pdf(test_pdf)
    
    if success:
        console.print("\n[bold green]✓ Test completed successfully![/bold green]")
        console.print("\nYou can now:")
        console.print("1. Check the output/test_catalogs directory for results")
        console.print("2. Review the summary_report.md for a human-readable overview")
        console.print("3. Examine the stages/ directory to audit each processing step")
        console.print("4. Look at text_content/ for extracted text files")
    else:
        console.print("\n[bold red]✗ Test failed![/bold red]")


if __name__ == "__main__":
    main()