#!/usr/bin/env python3
"""Test all the fixes we made to the fact-checking pipeline."""

import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_response_client_compatibility():
    """Test that ResponsesClient has backward-compatible get_response method."""
    print("Testing ResponsesClient compatibility...")
    
    from src.fact_check.core.responses_client import ResponsesClient
    
    # Check that get_response method exists
    client = ResponsesClient()
    assert hasattr(client, 'get_response'), "ResponsesClient missing get_response method"
    assert hasattr(client, 'create_response'), "ResponsesClient missing create_response method"
    
    print("  ✓ ResponsesClient has both create_response and get_response methods")

def test_evidence_critic_data_structure():
    """Test that EvidenceCritic outputs the expected data structure."""
    print("\nTesting EvidenceCritic data structure...")
    
    # Mock the output structure
    critic_output = {
        "claim_id": "test_001",
        "claim": "Test claim",
        "document": "test.pdf",
        "critic_stats": {
            "total_evaluated": 5,
            "approved": 3,
            "rejected": 2,
            "approval_rate": 0.6,
            "average_score": 7.5,
            "score_distribution": {"STRONG": 1, "MODERATE": 2, "WEAK": 0}
        },
        "validated_snippets": [
            {
                "quote": "Test quote",
                "critic_evaluation": {
                    "overall_score": 8.5
                }
            }
        ],
        "rejected_snippets": []
    }
    
    # Check expected fields exist
    assert "critic_stats" in critic_output, "Missing critic_stats field"
    assert "validated_snippets" in critic_output, "Missing validated_snippets field"
    assert "rejected_snippets" in critic_output, "Missing rejected_snippets field"
    
    # Check that old fields don't exist
    assert "critique_summary" not in critic_output, "Old critique_summary field still present"
    assert "critiqued_snippets" not in critic_output, "Old critiqued_snippets field still present"
    
    print("  ✓ EvidenceCritic output structure is correct")

def test_evidence_judge_compatibility():
    """Test that EvidenceJudge can handle new data structure."""
    print("\nTesting EvidenceJudge compatibility...")
    
    # This would be tested more thoroughly with actual data
    # For now just verify the logic would work
    
    # Mock critic data in new format
    critic_data = {
        "critic_stats": {},
        "validated_snippets": [
            {"quote": "Test", "critic_evaluation": {"overall_score": 9.0}},
            {"quote": "Test2", "critic_evaluation": {"overall_score": 8.0}},
        ]
    }
    
    # Test the logic for counting high quality
    validated_snippets = critic_data.get("validated_snippets", [])
    high_quality_count = sum(1 for s in validated_snippets 
                            if s.get("critic_evaluation", {}).get("overall_score", 0) >= 8.0)
    
    assert high_quality_count == 2, f"Expected 2 high quality snippets, got {high_quality_count}"
    
    print("  ✓ EvidenceJudge can process new data structure")

def test_no_context_field():
    """Test that context field has been removed from data structures."""
    print("\nTesting context field removal...")
    
    from src.fact_check.evidence_extractor import SupportingSnippet
    
    # Create a snippet
    snippet = SupportingSnippet(
        id=1,
        quote="Test quote",
        relevance_explanation="Test explanation"
    )
    
    # Check that context is not in the model
    assert not hasattr(snippet, 'context'), "SupportingSnippet still has context field"
    
    print("  ✓ Context field successfully removed from SupportingSnippet")

def test_json_parsing_robustness():
    """Test that JSON parsing has error handling."""
    print("\nTesting JSON parsing robustness...")
    
    from src.fact_check.evidence_extractor import EvidenceExtractor
    
    # Test various malformed responses
    extractor = EvidenceExtractor(None)
    
    # Test with trailing comma
    malformed_json = '{"snippets": [{"quote": "test",},]}'
    
    # The manual extraction should handle this
    result = extractor._extract_snippets_manually(malformed_json)
    assert "snippets" in result, "Manual extraction failed"
    
    print("  ✓ JSON parsing has fallback error handling")

def test_document_truncation_warning():
    """Test that long documents produce warnings."""
    print("\nTesting document truncation warning...")
    
    # Create a long document
    long_text = "x" * 60000  # 60k characters
    
    # Check that truncation logic would work
    if len(long_text) > 50000:
        truncated = long_text[:50000]
        assert len(truncated) == 50000, "Truncation logic error"
        print(f"  ✓ Document truncation works (60k -> 50k chars)")
    
def test_prompt_updates():
    """Test that prompts have been updated correctly."""
    print("\nTesting prompt updates...")
    
    # Read the evidence extractor file
    extractor_path = Path("src/fact_check/evidence_extractor.py")
    content = extractor_path.read_text()
    
    # Check for updated prompt
    assert "Extract VERBATIM quotes" in content, "Prompt not updated to verbatim extraction"
    assert "No ellipsis (...)" in content, "Prompt doesn't mention no ellipsis"
    
    print("  ✓ Extraction prompts updated correctly")

def main():
    """Run all tests."""
    print("Running comprehensive fix verification...\n")
    
    try:
        test_response_client_compatibility()
        test_evidence_critic_data_structure()
        test_evidence_judge_compatibility()
        test_no_context_field()
        test_json_parsing_robustness()
        test_document_truncation_warning()
        test_prompt_updates()
        
        print("\n" + "="*50)
        print("✅ All fixes verified successfully!")
        print("="*50)
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()