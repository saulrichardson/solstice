#!/usr/bin/env python3
"""Test script to verify the refactored fact-checking pipeline."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import modules
from src.fact_check.orchestrators import ClaimOrchestrator
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_single_claim():
    """Test processing a single claim with the refactored pipeline."""
    
    # Test claim and document
    claim_id = "test_claim_001"
    claim_text = "Flublok contains 45 micrograms (mcg) of HA per strain vs 15 mcg of HA per strain in a standard-dose influenza vaccine."
    documents = ["FlublokPI"]
    
    logger.info(f"Testing refactored pipeline with claim: {claim_text[:50]}...")
    
    # Configure which agents to run
    config = {
        "agents": [
            "supporting_evidence",
            "regex_verifier", 
            "evidence_critic",
            "completeness_checker",
            "regex_verifier_final",
            "evidence_judge"
        ],
        "agent_config": {
            "model": "gpt-4"
        }
    }
    
    # Create orchestrator
    orchestrator = ClaimOrchestrator(
        claim_id=claim_id,
        claim_text=claim_text,
        documents=documents,
        cache_dir=Path("data/cache"),
        config=config
    )
    
    # Process claim
    try:
        result = await orchestrator.process()
        
        # Check results
        logger.info("\n=== RESULTS ===")
        
        for doc_name, doc_result in result["documents"].items():
            logger.info(f"\nDocument: {doc_name}")
            
            if doc_result.get("success", False):
                # Check supporting evidence extraction
                supporting_evidence = doc_result.get("supporting_evidence", {})
                snippets = supporting_evidence.get("supporting_snippets", [])
                logger.info(f"  Supporting snippets found: {len(snippets)}")
                
                # Verify no context field in snippets
                for i, snippet in enumerate(snippets):
                    if "context" in snippet:
                        logger.error(f"  ERROR: Context field found in snippet {i+1}!")
                    else:
                        logger.info(f"  ✓ Snippet {i+1}: No context field (correct)")
                    
                    # Log quote preview
                    quote_preview = snippet.get("quote", "")[:100]
                    logger.info(f"    Quote: {quote_preview}...")
                
                # Check critic results
                critic_result = doc_result.get("evidence_critic", {})
                validated = critic_result.get("validated_snippets", [])
                rejected = critic_result.get("rejected_snippets", [])
                
                logger.info(f"\n  Evidence Critic:")
                logger.info(f"    Validated: {len(validated)}")
                logger.info(f"    Rejected: {len(rejected)}")
                
                # Check completeness results
                completeness = doc_result.get("completeness_checker", {})
                if completeness:
                    new_snippets = completeness.get("new_snippets", [])
                    logger.info(f"\n  Completeness Checker:")
                    logger.info(f"    New snippets found: {len(new_snippets)}")
                    
                    # Verify no context in new snippets
                    for i, snippet in enumerate(new_snippets):
                        if "context" in snippet:
                            logger.error(f"    ERROR: Context field found in new snippet {i+1}!")
                        else:
                            logger.info(f"    ✓ New snippet {i+1}: No context field (correct)")
                
                # Check final judgment
                judge_result = doc_result.get("evidence_judge", {})
                if judge_result:
                    judgment = judge_result.get("judgment", {})
                    logger.info(f"\n  Final Judgment:")
                    logger.info(f"    Verdict: {judgment.get('verdict', 'N/A')}")
                    logger.info(f"    Confidence: {judgment.get('confidence', 'N/A')}")
                
                logger.info("\n✅ Pipeline completed successfully!")
                
            else:
                logger.error(f"  Failed: {doc_result.get('error', 'Unknown error')}")
                
    except Exception as e:
        logger.error(f"Pipeline failed with error: {e}")
        raise
    
    return result


async def main():
    """Run the test."""
    try:
        result = await test_single_claim()
        logger.info("\n🎉 Test completed successfully!")
    except Exception as e:
        logger.error(f"\n❌ Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())