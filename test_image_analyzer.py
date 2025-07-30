#!/usr/bin/env python3
"""Test script for image evidence analyzer."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.fact_check.agents import ImageEvidenceAnalyzer

async def test_image_analyzer():
    """Test the image evidence analyzer with a sample image."""
    
    # Configuration
    pdf_name = "FlublokPI"
    claim_id = "test_claim_001"
    claim_text = "Flublok contains 3x the hemagglutinin (HA) content of standard flu vaccines"
    cache_dir = Path("data/cache")
    
    # Find a test image
    figures_dir = cache_dir / pdf_name / "extracted" / "figures"
    if not figures_dir.exists():
        print(f"Error: No figures directory found at {figures_dir}")
        return
    
    # Get first available image
    image_files = list(figures_dir.glob("*.png")) + list(figures_dir.glob("*.jpg"))
    if not image_files:
        print("Error: No image files found")
        return
    
    test_image = image_files[0]
    print(f"Testing with image: {test_image.name}")
    print(f"Claim: {claim_text}")
    print("-" * 80)
    
    # Create analyzer
    analyzer = ImageEvidenceAnalyzer(
        pdf_name=pdf_name,
        claim_id=claim_id,
        image_filename=test_image.name,
        cache_dir=cache_dir,
        config={"claim": claim_text}
    )
    
    try:
        # Run analysis
        print("Running image analysis...")
        result = await analyzer.process()
        
        # Display results
        print("\nResults:")
        print(f"  Supports claim: {result.get('supports_claim')}")
        print(f"  Explanation: {result.get('explanation')}")
        print(f"  Model used: {result.get('model_used')}")
        
        if result.get('error'):
            print(f"  Error: {result.get('error')}")
        
        # Save output for inspection
        output_path = analyzer.agent_dir / "output.json"
        print(f"\nOutput saved to: {output_path}")
        
        return result
        
    except Exception as e:
        print(f"Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = asyncio.run(test_image_analyzer())
    
    if result:
        print("\n✅ Test completed successfully")
    else:
        print("\n❌ Test failed")