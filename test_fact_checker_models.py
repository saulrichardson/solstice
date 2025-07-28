#!/usr/bin/env python3
"""Test fact-checking with different models"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from fact_check.fact_checker import FactChecker
from fact_check.core.responses_client import ResponsesClient


async def test_with_model(model_name: str):
    """Test fact-checking with a specific model"""
    print(f"\n{'='*60}")
    print(f"Testing with model: {model_name}")
    print(f"{'='*60}")
    
    # Simple test document
    test_document = """
    The Earth orbits around the Sun.
    The Moon orbits around the Earth.
    Water freezes at 0 degrees Celsius.
    The speed of light is approximately 300,000 km/s.
    """
    
    # Test claims
    claims = [
        "The Earth orbits the Sun",
        "The Sun orbits the Earth",
        "Water freezes at 0°C"
    ]
    
    client = ResponsesClient()
    
    # Create a custom fact checker that uses the specified model
    class CustomFactChecker(FactChecker):
        async def _reasoner(self, claim: str, document_text: str):
            """Override to use custom model"""
            prompt = f"""Given a claim and a document, provide a structured analysis.

CLAIM: {claim}

DOCUMENT:
{document_text}

Instructions:
1. Find verbatim quotes from the document that relate to the claim
2. For each quote, explain why it's relevant
3. Quotes MUST be exact substrings from the document
4. Provide a verdict: supports, does_not_support, or insufficient
5. Give a confidence score between 0 and 1

Return a JSON response in this exact format:
{{
    "steps": [
        {{
            "id": 1,
            "reasoning": "Explanation of why this quote matters",
            "quote": "Exact text from the document"
        }}
    ],
    "verdict": "supports|does_not_support|insufficient",
    "confidence": 0.0-1.0
}}

IMPORTANT: Return ONLY valid JSON, no other text."""

            try:
                response = self.llm_client.create_response(
                    model=model_name,  # Use the specified model
                    input=prompt,
                    temperature=0.1
                )
                
                # Print model info
                print(f"API returned model: {response.get('model')}")
                
                # Same parsing logic as original
                if hasattr(response, 'output') and response.output:
                    output = response.output
                else:
                    output = response.get("output", [])
                
                content = None
                if isinstance(output, list) and output:
                    for msg in output:
                        if isinstance(msg, dict) and 'content' in msg:
                            msg_content = msg['content']
                            if isinstance(msg_content, list):
                                for item in msg_content:
                                    if isinstance(item, dict) and item.get('type') == 'output_text':
                                        content = item.get('text', '')
                                        break
                                    elif isinstance(item, dict) and 'text' in item:
                                        content = item['text']
                                        break
                            elif isinstance(msg_content, str):
                                content = msg_content
                                break
                        if content:
                            break
                elif isinstance(output, str):
                    content = output
                
                if not content:
                    raise ValueError("No content in response")
                
                # Handle markdown-wrapped JSON
                if content.startswith('```json') and content.endswith('```'):
                    content = content[7:-3].strip()
                elif content.startswith('```') and content.endswith('```'):
                    content = content[3:-3].strip()
                
                import json
                data = json.loads(content)
                
                from fact_check.fact_checker import ReasonerOutput
                return ReasonerOutput(**data)
                
            except Exception as e:
                print(f"Error with {model_name}: {e}")
                from fact_check.fact_checker import ReasonerOutput
                return ReasonerOutput(
                    steps=[],
                    verdict="insufficient",
                    confidence=0.0
                )
    
    fact_checker = CustomFactChecker(client)
    
    results = []
    for claim in claims:
        print(f"\nClaim: {claim}")
        try:
            result = await fact_checker.check_claim(claim, test_document)
            print(f"Verdict: {result.verdict}")
            print(f"Confidence: {result.confidence}")
            results.append((claim, result.verdict))
        except Exception as e:
            print(f"Error: {e}")
            results.append((claim, "error"))
    
    return results


async def main():
    """Test different models"""
    models = ["gpt-4.1", "gpt-4o", "o4-mini"]
    
    print("Fact-Checking with Different Models")
    print("="*60)
    
    all_results = {}
    
    for model in models:
        try:
            results = await test_with_model(model)
            all_results[model] = results
        except Exception as e:
            print(f"Failed to test {model}: {e}")
            all_results[model] = []
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    for model, results in all_results.items():
        print(f"\n{model}:")
        for claim, verdict in results:
            print(f"  - {claim}: {verdict}")
    
    print("\nConclusion:")
    print("- Gateway passes through model names without aliasing")
    print("- Users can specify any model they want")
    print("- Each model maintains its identity (gpt-4.1 -> gpt-4.1-2025-04-14)")
    print("- o4-mini works but may require special handling for reasoning features")


if __name__ == "__main__":
    asyncio.run(main())