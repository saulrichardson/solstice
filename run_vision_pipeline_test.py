#!/usr/bin/env python3
"""Run the vision pipeline with o4-mini and detailed logging."""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.fact_check.orchestrators.claim_orchestrator import ClaimOrchestrator
from src.fact_check.config.agent_models import get_model_for_agent

# Set up detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Enable debug logging for our modules
logging.getLogger("src.fact_check").setLevel(logging.INFO)
logging.getLogger("src.fact_check.agents.image_evidence_analyzer").setLevel(logging.INFO)
logging.getLogger("src.fact_check.orchestrators").setLevel(logging.INFO)

async def run_vision_pipeline():
    """Run the vision pipeline with detailed logging."""
    
    print("=" * 80)
    print("RUNNING VISION PIPELINE WITH O4-MINI")
    print("=" * 80)
    
    # Verify configuration
    model = get_model_for_agent("image_evidence_analyzer")
    print(f"\nImage analyzer configured to use: {model}")
    
    # Test claims
    test_claims = [
        {
            "id": "claim_000",
            "claim": "Flublok is approved for adults 18 years and older"
        },
        {
            "id": "claim_001", 
            "claim": "Flublok contains 45 mcg of hemagglutinin per strain"
        }
    ]
    
    # Document to analyze
    document = {
        "name": "FlublokPI",
        "path": Path("data/cache/FlublokPI")
    }
    
    # Create orchestrator
    orchestrator = ClaimOrchestrator(
        cache_dir=Path("data/cache"),
        claims=test_claims
    )
    
    print(f"\nProcessing {len(test_claims)} claims for document: {document['name']}")
    print("-" * 80)
    
    # Process claims
    results = await orchestrator.process_document(document)
    
    # Display results
    print("\n" + "=" * 80)
    print("VISION PIPELINE RESULTS")
    print("=" * 80)
    
    for claim_id, claim_data in results.items():
        print(f"\nClaim {claim_id}: {claim_data['claim']}")
        print("-" * 60)
        
        # Check if image evidence was found
        if "image_evidence" in claim_data:
            image_evidence = claim_data["image_evidence"]
            if image_evidence:
                print(f"Found {len(image_evidence)} images analyzed")
                for img in image_evidence:
                    print(f"\n  Image: {img['image_filename']}")
                    print(f"  Supports claim: {img.get('supports_claim', False)}")
                    print(f"  Explanation: {img.get('explanation', 'N/A')[:200]}...")
                    if img.get('error'):
                        print(f"  Error: {img.get('explanation')}")
            else:
                print("No images analyzed")
        else:
            print("Image analysis not performed")
        
        # Also show text evidence summary
        if "evidence" in claim_data:
            text_evidence = claim_data["evidence"]
            print(f"\nText evidence: {len(text_evidence.get('supporting_quotes', []))} supporting quotes")

if __name__ == "__main__":
    asyncio.run(run_vision_pipeline())