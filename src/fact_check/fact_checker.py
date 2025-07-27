"""Fact Checker Agent - Reasoner + Quote Verifier Implementation"""

import json
from typing import Dict, List, Tuple, Optional, Literal
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


# Data models
class ReasoningStep(BaseModel):
    """A single step in the reasoning process"""
    id: int
    reasoning: str
    quote: str
    # Added by verifier
    start: Optional[int] = None
    end: Optional[int] = None


class ReasonerOutput(BaseModel):
    """Output from the reasoner LLM"""
    steps: List[ReasoningStep]
    verdict: Literal["supports", "does_not_support", "insufficient"]
    confidence: float = Field(ge=0.0, le=1.0)


class VerificationResult(BaseModel):
    """Result from the quote verifier"""
    success: bool
    steps: Optional[List[ReasoningStep]] = None
    offending_quote: Optional[str] = None
    verdict: Optional[Literal["supports", "does_not_support", "insufficient"]] = None
    confidence: Optional[float] = None


class FactChecker:
    """Main fact checking agent combining reasoner and verifier"""
    
    def __init__(self, llm_client):
        """
        Initialize the fact checker with an LLM client
        
        Args:
            llm_client: An object that can make LLM calls (e.g., OpenAI client)
        """
        self.llm_client = llm_client
    
    async def check_claim(self, claim: str, document_text: str) -> VerificationResult:
        """
        Check a claim against a document
        
        Args:
            claim: The claim to verify
            document_text: The full text of the document
            
        Returns:
            VerificationResult with the outcome
        """
        # Step 1: Call reasoner
        reasoner_output = await self._reasoner(claim, document_text)
        
        # Step 2: Verify quotes
        verification = self._verify_quotes(reasoner_output, document_text)
        
        # Step 3: Handle verification failure with one retry
        if not verification.success and verification.offending_quote:
            logger.info(f"Quote verification failed for: {verification.offending_quote}")
            
            # Try to fix the quote
            fixed_output = await self._fix_quote(
                reasoner_output, 
                verification.offending_quote,
                document_text
            )
            
            # Re-verify
            verification = self._verify_quotes(fixed_output, document_text)
            
            # If still failing, return insufficient evidence
            if not verification.success:
                return VerificationResult(
                    success=False,
                    verdict="insufficient",
                    confidence=0.0,
                    offending_quote=verification.offending_quote
                )
        
        return verification
    
    async def _reasoner(self, claim: str, document_text: str) -> ReasonerOutput:
        """
        Use LLM to reason about the claim
        
        Args:
            claim: The claim to verify
            document_text: The full document text
            
        Returns:
            ReasonerOutput with reasoning steps
        """
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
}}"""

        # Make LLM call
        from ..gateway.app.providers.base import ResponseRequest
        # For Responses API, include JSON instruction in the prompt
        json_prompt = prompt + "\n\nIMPORTANT: Return ONLY valid JSON, no other text."
        request = ResponseRequest(
            model="gpt-4.1",
            input=json_prompt,
            temperature=0.1
        )
        response = await self.llm_client.create_response(request)
        
        # Parse response
        try:
            # Extract content from response structure
            # The Responses API returns output as a list of content items
            if hasattr(response, 'output') and response.output:
                output = response.output
            else:
                output = response.get("output", [])
            
            # Find the text content in the output
            content = None
            if isinstance(output, list) and output:
                # Response structure: output is a list of message objects
                for msg in output:
                    if isinstance(msg, dict) and 'content' in msg:
                        msg_content = msg['content']
                        # content can be a list of content items
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
                logger.error(f"No content found in response output: {output}")
                raise ValueError("No content in response")
                
            data = json.loads(content)
            return ReasonerOutput(**data)
        except Exception as e:
            logger.error(f"Failed to parse reasoner output: {e}")
            logger.error(f"Response was: {response}")
            # Return empty result on parse failure
            return ReasonerOutput(
                steps=[],
                verdict="insufficient",
                confidence=0.0
            )
    
    def _verify_quotes(self, reasoner_output: ReasonerOutput, document_text: str) -> VerificationResult:
        """
        Verify that all quotes exist in the document
        
        Args:
            reasoner_output: Output from the reasoner
            document_text: The document text
            
        Returns:
            VerificationResult with verification status
        """
        verified_steps = []
        
        for step in reasoner_output.steps:
            # TODO: Add quote normalization here when input format is finalized
            # For now, do exact string matching
            
            position = document_text.find(step.quote)
            
            if position == -1:
                # Quote not found
                return VerificationResult(
                    success=False,
                    offending_quote=step.quote
                )
            
            # Add position information
            verified_step = step.model_copy()
            verified_step.start = position
            verified_step.end = position + len(step.quote)
            verified_steps.append(verified_step)
        
        # All quotes verified
        return VerificationResult(
            success=True,
            steps=verified_steps,
            verdict=reasoner_output.verdict,
            confidence=reasoner_output.confidence
        )
    
    async def _fix_quote(
        self, 
        original_output: ReasonerOutput,
        offending_quote: str,
        document_text: str
    ) -> ReasonerOutput:
        """
        Ask LLM to fix an incorrect quote
        
        Args:
            original_output: The original reasoner output
            offending_quote: The quote that couldn't be found
            document_text: The document text
            
        Returns:
            Fixed ReasonerOutput
        """
        prompt = f"""The following quote could not be found in the document:
"{offending_quote}"

Please either:
1. Provide the correct verbatim quote from the document
2. Remove this step if no suitable quote exists

Original reasoning steps:
{json.dumps([step.model_dump() for step in original_output.steps], indent=2)}

DOCUMENT:
{document_text}

Return the corrected JSON with the same structure as before."""

        from ..gateway.app.providers.base import ResponseRequest
        json_prompt = prompt + "\n\nIMPORTANT: Return ONLY valid JSON, no other text."
        request = ResponseRequest(
            model="gpt-4.1",
            input=json_prompt,
            temperature=0.1
        )
        response = await self.llm_client.create_response(request)
        
        try:
            # Extract content - same logic as _reasoner
            if hasattr(response, 'output') and response.output:
                output = response.output
            else:
                output = response.get("output", [])
            
            content = None
            if isinstance(output, list) and output:
                # Same structure as in _reasoner
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
                
            data = json.loads(content)
            return ReasonerOutput(**data)
        except Exception as e:
            logger.error(f"Failed to parse fixed output: {e}")
            # Return original on parse failure
            return original_output