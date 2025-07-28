"""Example of using the fact-checking interface with extracted documents."""

import asyncio
from pathlib import Path

from src.injestion.models.document import Document
from src.injestion.processing.fact_check_interface import FactCheckInterface, prepare_for_fact_checking
from src.fact_check.fact_checker import FactChecker
from src.fact_check.llm_client import LLMClient  # Assuming this exists


async def fact_check_document(pdf_path: str, claim: str):
    """Example of fact-checking a claim against an extracted document.
    
    Args:
        pdf_path: Path to the PDF that was processed
        claim: The claim to verify
    """
    # 1. Load the extracted document
    from src.injestion.storage.paths import extracted_content_path
    content_path = extracted_content_path(pdf_path)
    
    if not content_path.exists():
        print(f"No extracted content found for {pdf_path}")
        print("Please run the ingestion pipeline first.")
        return
    
    document = Document.load(content_path)
    print(f"Loaded document with {len(document.blocks)} blocks")
    
    # 2. Prepare document for fact-checking
    fact_check_data = prepare_for_fact_checking(document)
    print(f"Document has {fact_check_data['page_count']} pages")
    print(f"Found {len(fact_check_data['visual_elements'])} figures/tables")
    
    # 3. Initialize fact checker
    llm_client = LLMClient()  # Configure as needed
    fact_checker = FactChecker(llm_client)
    
    # 4. Check the claim
    print(f"\nChecking claim: {claim}")
    result = await fact_checker.check_claim(
        claim=claim,
        document_text=fact_check_data['full_text']
    )
    
    # 5. Display results
    print(f"\nVerdict: {result.verdict}")
    print(f"Confidence: {result.confidence}")
    
    if result.steps:
        print("\nReasoning steps:")
        for step in result.steps:
            print(f"\n{step.id}. {step.reasoning}")
            print(f"   Quote: '{step.quote}'")
            if step.start is not None:
                print(f"   Location: chars {step.start}-{step.end}")
    
    if not result.success:
        print(f"\nVerification failed: {result.offending_quote}")
    
    # 6. Advanced: Check claims involving visual content
    interface = FactCheckInterface(document)
    
    # Example: Find specific text locations
    if result.steps and result.steps[0].quote:
        location = interface.find_text_location(result.steps[0].quote)
        if location:
            print(f"\nFirst quote found on page {location['page_index'] + 1}")
            print(f"In block {location['block_id']} at position {location['char_start']}")
    
    # Example: Get visual elements that might be relevant
    visual_elements = interface.get_figures_and_tables()
    if visual_elements:
        print(f"\nVisual elements that may be relevant:")
        for elem in visual_elements[:3]:  # Show first 3
            print(f"- {elem['role']} on page {elem['page_index'] + 1}: {elem['description']}")


async def fact_check_with_images(pdf_path: str, claim: str):
    """Example of fact-checking that involves analyzing images.
    
    Args:
        pdf_path: Path to the PDF
        claim: The claim to verify (may reference visual content)
    """
    # Load document
    from src.injestion.storage.paths import extracted_content_path
    document = Document.load(extracted_content_path(pdf_path))
    
    # Create interface
    interface = FactCheckInterface(document)
    
    # Get all images
    images = interface.get_all_images()
    print(f"Found {len(images)} figures/tables in the document")
    
    # Show available images
    for img in images:
        print(f"\n{img['role']} on page {img['page_index'] + 1}:")
        print(f"  Description: {img['description']}")
        print(f"  File exists: {img['image_exists']}")
        print(f"  Path: {img['image_path']}")
    
    # For multimodal LLMs, get images with base64 encoding
    visual_elements = interface.get_figures_and_tables(include_images=True)
    
    # Example: Get a specific image by ID
    if images:
        first_image_id = images[0]['block_id']
        image_data = interface.get_image_by_id(first_image_id)
        if image_data:
            print(f"\nLoaded image {first_image_id}:")
            print(f"  Size of base64 data: {len(image_data['image_base64'])} chars")
            
            # For multimodal fact-checking, you could pass this to an LLM like:
            # llm_client = MultimodalLLMClient()  # e.g., GPT-4V, Claude, etc.
            # result = await llm_client.check_claim_with_image(
            #     claim=claim,
            #     document_text=interface.get_full_text(),
            #     image_data=image_data['image_base64']
            # )


async def fact_check_with_context(pdf_path: str, claim: str, page_number: int):
    """Example of fact-checking with page-specific context.
    
    Args:
        pdf_path: Path to the PDF
        claim: The claim to verify
        page_number: Human-readable page number (1-indexed)
    """
    # Load document
    from src.injestion.storage.paths import extracted_content_path
    document = Document.load(extracted_content_path(pdf_path))
    
    # Create interface
    interface = FactCheckInterface(document)
    
    # Get text from specific page (convert to 0-indexed)
    page_text = interface.get_page_text(page_number - 1)
    
    if not page_text:
        print(f"No text found on page {page_number}")
        return
    
    print(f"Checking claim against page {page_number} only")
    print(f"Page has {len(page_text)} characters")
    
    # Initialize and run fact checker
    llm_client = LLMClient()
    fact_checker = FactChecker(llm_client)
    
    result = await fact_checker.check_claim(
        claim=claim,
        document_text=page_text
    )
    
    print(f"Verdict: {result.verdict} (confidence: {result.confidence})")


def explore_document_structure(pdf_path: str):
    """Example of exploring the extracted document structure.
    
    Args:
        pdf_path: Path to the PDF
    """
    from src.injestion.storage.paths import extracted_content_path
    document = Document.load(extracted_content_path(pdf_path))
    
    interface = FactCheckInterface(document)
    
    print(f"Document: {document.source_pdf}")
    print(f"Total blocks: {len(document.blocks)}")
    print(f"Pages: {len(document.reading_order)}")
    
    # Count block types
    block_types = {}
    for block in document.blocks:
        block_types[block.role] = block_types.get(block.role, 0) + 1
    
    print("\nBlock types:")
    for role, count in block_types.items():
        print(f"  {role}: {count}")
    
    # Show text with locations
    print("\nFirst 5 text blocks with locations:")
    text_with_locs = interface.get_text_with_locations()
    for text, metadata in text_with_locs[:5]:
        preview = text[:60] + "..." if len(text) > 60 else text
        print(f"\nPage {metadata['page_index'] + 1}, {metadata['role']}:")
        print(f"  '{preview}'")
        print(f"  BBox: {metadata['bbox']}")
    
    # Show visual elements
    visuals = interface.get_figures_and_tables()
    if visuals:
        print(f"\nVisual elements ({len(visuals)} total):")
        for v in visuals[:3]:
            print(f"  Page {v['page_index'] + 1}: {v['role']} - {v['description'][:50]}...")


if __name__ == "__main__":
    # Example usage
    pdf_path = "data/clinical_files/Arunachalam et al. (2021).pdf"
    
    # Example 1: Basic fact checking
    claim = "RIV4 uses a baculovirus expression vector system"
    asyncio.run(fact_check_document(pdf_path, claim))
    
    # Example 2: Page-specific fact checking
    claim = "The vaccine provides cross-protection"
    page = 1
    asyncio.run(fact_check_with_context(pdf_path, claim, page))
    
    # Example 3: Fact checking with images
    claim = "The figure shows the vaccine production process"
    asyncio.run(fact_check_with_images(pdf_path, claim))
    
    # Example 4: Explore structure
    explore_document_structure(pdf_path)