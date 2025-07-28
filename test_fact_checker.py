#!/usr/bin/env python3
"""Test the fact-checking agent with a sample claim from the FlublokPI document"""

import asyncio
import json
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fact_check.fact_checker import FactChecker
from fact_check.core.responses_client import ResponsesClient
from injestion.models.document import Document
from injestion.processing.fact_check_interface import FactCheckInterface


async def main():
    """Test the fact-checking agent"""
    
    # Load the FlublokPI document
    cache_dir = Path(__file__).parent / "data" / "cache" / "FlublokPI"
    content_file = cache_dir / "extracted" / "content.json"
    
    print("Loading document...")
    with open(content_file, "r") as f:
        data = json.load(f)
    
    # Create Document object
    document = Document(**data)
    
    # Create fact check interface
    interface = FactCheckInterface(document)
    
    # Get full document text
    document_text = interface.get_full_text(include_figure_descriptions=True)
    
    # Print a snippet to verify it loaded correctly
    print(f"Document loaded. First 200 chars: {document_text[:200]}...")
    print(f"Total document length: {len(document_text)} characters")
    
    # Define test claims
    test_claims = [
        # True claim from the document
        "Flublok is approved for use in persons 18 years of age and older.",
        
        # False claim (document says 18+, not 16+)
        "Flublok is approved for use in persons 16 years of age and older.",
        
        # Partially true claim with specific details
        "In adults 18 through 49 years of age, the most common injection-site adverse reaction was pain at 37%.",
        
        # Complex claim requiring multiple pieces of evidence
        "Guillain-Barré syndrome history within 6 weeks of prior influenza vaccine requires careful consideration before giving Flublok.",
    ]
    
    # Initialize the gateway client
    print("\nInitializing Responses API client...")
    # Let the client use default URL from environment
    client = ResponsesClient()
    
    # Initialize fact checker
    fact_checker = FactChecker(client)
    
    # Test each claim
    for i, claim in enumerate(test_claims, 1):
        print(f"\n{'='*80}")
        print(f"Test {i}: {claim}")
        print(f"{'='*80}")
        
        try:
            # Check the claim
            result = await fact_checker.check_claim(claim, document_text)
            
            # Print results
            print(f"\nVerdict: {result.verdict}")
            print(f"Confidence: {result.confidence}")
            print(f"Success: {result.success}")
            
            if result.steps:
                print(f"\nReasoning steps ({len(result.steps)}):")
                for step in result.steps:
                    print(f"\n  Step {step.id}:")
                    print(f"  Reasoning: {step.reasoning}")
                    print(f"  Quote: '{step.quote}'")
                    if step.start is not None:
                        print(f"  Position: {step.start}-{step.end}")
            
            if result.offending_quote:
                print(f"\nOffending quote not found: '{result.offending_quote}'")
                
        except Exception as e:
            print(f"\nError checking claim: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n\nTest completed!")


if __name__ == "__main__":
    asyncio.run(main())