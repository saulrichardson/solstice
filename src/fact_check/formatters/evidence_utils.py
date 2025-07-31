"""Utilities for standardizing evidence format across formatters."""

from typing import Dict, Any, List


def extract_text_evidence(supporting_evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract text evidence in standardized format.
    
    Args:
        supporting_evidence: List of text evidence from study results
        
    Returns:
        List of standardized text evidence dictionaries
    """
    return [
        {
            "type": "text",
            "quote": evidence.get("quote", ""),
            "explanation": evidence.get("explanation", "")
        }
        for evidence in supporting_evidence
    ]


def extract_image_evidence(image_evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract image evidence in standardized format.
    
    Args:
        image_evidence: List of image evidence from study results
        
    Returns:
        List of standardized image evidence dictionaries
    """
    results = []
    for img in image_evidence:
        if not img.get("supports_claim", True):
            continue
            
        # Get reasoning from detailed analysis or fallback to explanation
        detailed = img.get("detailed_analysis", {})
        reasoning = detailed.get("reasoning", img.get("explanation", ""))
        
        results.append({
            "type": "image",
            "filename": img.get("image_filename", ""),
            "reasoning": reasoning
        })
    
    return results


def extract_all_evidence(doc_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract all evidence (text and image) from a document result.
    
    Args:
        doc_result: Document processing result containing evidence
        
    Returns:
        List of all evidence in standardized format
    """
    all_evidence = []
    
    # Add text evidence
    text_evidence = doc_result.get("supporting_evidence", [])
    all_evidence.extend(extract_text_evidence(text_evidence))
    
    # Add image evidence
    image_evidence = doc_result.get("image_evidence", [])
    all_evidence.extend(extract_image_evidence(image_evidence))
    
    return all_evidence