#!/usr/bin/env python3
"""Test image analyzer with a dosage-related image."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.fact_check.agents import ImageEvidenceAnalyzer

async def test_with_dosage_image():
    """Test with an image that might contain dosage information."""
    
    # Configuration
    pdf_name = "FlublokPI"
    claim_id = "test_claim_002"
    claim_text = "Flublok contains 3x the hemagglutinin (HA) content of standard flu vaccines"
    cache_dir = Path("data/cache")
    
    # Look for tables that might contain dosage info
    figures_dir = cache_dir / pdf_name / "extracted" / "figures"
    
    # Find tables (they often contain dosage data)
    table_files = sorted(figures_dir.glob("table_*.png"))
    
    if not table_files:
        print("No table images found")
        return
    
    print(f"Found {len(table_files)} table images")
    print(f"Testing claim: {claim_text}")
    print("-" * 80)
    
    # Test first few tables
    for i, table_file in enumerate(table_files[:5]):
        print(f"\n[{i+1}/{min(5, len(table_files))}] Testing: {table_file.name}")
        
        analyzer = ImageEvidenceAnalyzer(
            pdf_name=pdf_name,
            claim_id=claim_id,
            image_filename=table_file.name,
            cache_dir=cache_dir,
            config={"claim": claim_text}
        )
        
        try:
            result = await analyzer.process()
            
            supports = result.get('supports_claim', False)
            print(f"  Supports claim: {'✅ YES' if supports else '❌ NO'}")
            
            if supports:
                print(f"  Explanation: {result.get('explanation', '')[:200]}...")
                return result  # Found supporting evidence
            else:
                # Show brief reason why not
                explanation = result.get('explanation', '')
                if 'adverse' in explanation.lower():
                    print("  → Contains adverse event data")
                elif 'demographic' in explanation.lower():
                    print("  → Contains demographic data")
                elif 'dosage' in explanation.lower() or 'mcg' in explanation.lower():
                    print("  → Contains dosage info!")
                    print(f"  Explanation: {explanation[:200]}...")
                else:
                    print(f"  → {explanation[:100]}...")
                    
        except Exception as e:
            print(f"  Error: {e}")
    
    print("\nNo supporting evidence found in tested images")
    return None

if __name__ == "__main__":
    result = asyncio.run(test_with_dosage_image())