"""Agent for analyzing images to find evidence supporting claims."""

import base64
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from .base import BaseAgent, AgentError
from ..core.responses_client import ResponsesClient
from ..config.agent_models import get_model_for_agent
from ..config.model_capabilities import build_vision_request, extract_text_from_response
from ..models.image_outputs import ImageAnalysisOutput
from ..utils.llm_parser import LLMResponseParser
from ..utils.json_parser import parse_json_response, parse_json_with_pydantic

logger = logging.getLogger(__name__)


class ImageEvidenceAnalyzer(BaseAgent):
    """
    Analyze a single image to determine if it contains evidence supporting a claim.
    
    This agent:
    1. Loads a specific image file
    2. Uses multimodal LLM to analyze its content
    3. Determines if it supports the claim
    4. Extracts relevant information if supportive
    """
    
    @property
    def agent_name(self) -> str:
        return "image_evidence_analyzer"
    
    @property
    def required_inputs(self) -> List[str]:
        # No dependencies - just needs the image file to exist
        return []
    
    def __init__(
        self, 
        pdf_name: str,
        claim_id: str,
        image_metadata: Dict[str, Any],
        cache_dir: Path = Path("data/cache"),
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize image evidence analyzer for a specific image.
        
        Args:
            pdf_name: Name of the PDF document
            claim_id: ID of the claim being processed
            image_metadata: Image metadata from document_utils.get_images() containing:
                - image_path: Path to image file relative to extracted dir
                - page_number: Page number (1-based)
                - role: Figure or Table
                - block_id: Block identifier
            cache_dir: Base cache directory
            config: Agent configuration
        """
        super().__init__(pdf_name, cache_dir, config)
        self.claim_id = claim_id
        self.image_metadata = image_metadata
        
        # Extract filename from path for backward compatibility
        if 'image_path' in image_metadata:
            image_path = Path(image_metadata['image_path'])
            self.image_filename = image_path.name
        else:
            # Fallback to block_id or empty string
            self.image_filename = image_metadata.get('block_id', 'unknown_image')
        
        # Store results per image using block_id for uniqueness
        image_id = image_metadata.get('block_id', self.image_filename.replace('.png', '').replace('.jpg', ''))
        self.agent_dir = (
            self.pdf_dir / "agents" / "claims" / claim_id / 
            self.agent_name / image_id
        )
        self.agent_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up LLM client
        self.llm_client = ResponsesClient()
        # Use centrally configured model for this agent
        self.llm_client.model = get_model_for_agent(self.agent_name)
    
    async def process(self) -> Dict[str, Any]:
        """
        Analyze the image for evidence supporting the claim.
        
        Returns:
            Dictionary containing analysis results
        """
        claim = self.config.get("claim")
        if not claim:
            raise AgentError("No claim provided in config")
        
        logger.info(f"\n{'='*60}")
        logger.info(f"🖼️  IMAGE EVIDENCE ANALYZER")
        logger.info(f"Claim ID: {self.claim_id}")
        logger.info(f"Image: {self.image_filename}")
        
        # Build image path from metadata
        # image_path in metadata is relative to extracted directory
        if 'image_path' not in self.image_metadata:
            logger.error(f"❌ No image_path in metadata for {self.image_filename}")
            return {
                "image_filename": self.image_filename,
                "block_id": self.image_metadata.get('block_id', ''),
                "supports_claim": False,
                "confidence": 0.0,
                "analysis": "No image path found in metadata",
                "error": "missing_image_path"
            }
        
        image_path = self.pdf_dir / "extracted" / self.image_metadata['image_path']
        logger.info(f"Full path: {image_path}")
        logger.info(f"{'='*60}")
        
        if not image_path.exists():
            logger.warning(f"❌ Image file not found: {image_path}")
            logger.warning(f"   Expected location: {image_path.absolute()}")
            logger.warning(f"   Parent directory exists: {image_path.parent.exists()}")
            return {
                "image_filename": self.image_filename,
                "supports_claim": False,
                "explanation": "Image file not found",
                "error": True
            }
        
        try:
            # Read and encode image
            logger.info(f"📂 Loading image from: {image_path}")
            file_size = image_path.stat().st_size
            logger.info(f"   File size: {file_size:,} bytes")
            
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # Encode to base64 for LLM
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            logger.info(f"   Base64 length: {len(image_base64):,} chars")
            
            # Determine image mime type
            mime_type = "image/png" if image_path.suffix == ".png" else "image/jpeg"
            logger.info(f"   MIME type: {mime_type}")
            
            # Build comprehensive multimodal prompt with metadata context
            image_type = self.image_metadata.get('role', 'Figure')
            page_num = self.image_metadata.get('page_number', 'unknown')
            
            logger.info(f"\n📄 Image metadata:")
            logger.info(f"   Type: {image_type}")
            logger.info(f"   Page: {page_num}")
            logger.info(f"   Claim: {claim[:100]}..." if len(claim) > 100 else f"   Claim: {claim}")
            
            prompt = f"""You are analyzing a {image_type} from page {page_num} of a medical/clinical document to determine if it contains evidence supporting a specific claim.

CLAIM TO EVALUATE: {claim}

ANALYSIS APPROACH:
1. Carefully examine the entire image and identify what type of content it contains
2. Understand what information is presented and how it relates to the claim
3. Consider the context and source of the information shown
4. Evaluate whether the evidence directly addresses the claim or only partially relates to it
5. Think critically about what the evidence actually demonstrates versus what it might imply

KEY PRINCIPLES:
- Base your analysis solely on what is visible in the image - do not infer or assume information not present
- Distinguish between different types of evidence (e.g., study data, regulatory statements, clinical findings)
- Consider the completeness and directness of the evidence
- Note any limitations in what can be determined from the image
- Be precise about what the evidence shows versus what it doesn't show
- Consider the medical/clinical context when interpreting data
- Account for image quality issues - note if text is blurry, cut off, or difficult to read

Return your analysis as a JSON object with these fields:
{{
  "supports_claim": true/false,
  "image_description": "Objective description of what the image contains",
  "evidence_found": "Specific evidence in the image related to the claim (null if none)",
  "reasoning": "MUST say 'supports the claim' if true OR 'does not support the claim' if false",
  "confidence_notes": "Any limitations, caveats, or confidence issues (null if none)"
}}

CRITICAL REQUIREMENTS for the "reasoning" field:
- If supports_claim is true: Your reasoning MUST include the phrase "supports the claim"
- If supports_claim is false: Your reasoning MUST include "does not support" or "doesn't support the claim"
- This is required for validation - responses without these phrases will be rejected

Focus on clear, evidence-based reasoning that explains your determination.

Return ONLY the JSON object above. Do NOT wrap in ```json``` or any other markdown."""

            # Create data URI for image
            data_uri = f"data:{mime_type};base64,{image_base64}"
            
            # Parse with retry using Pydantic model
            response_text = None
            result = None
            
            # First attempt with structured JSON prompt
            try:
                # Add JSON format instruction to prompt
                json_prompt = prompt + "\n\nReturn ONLY valid JSON, nothing else. Do NOT wrap in ```json``` or any other markdown."
                
                # Build and send request
                logger.info(f"\n🤖 Sending vision request to LLM")
                logger.info(f"   Model: {self.llm_client.model}")
                logger.info(f"   Prompt length: {len(json_prompt)} chars")
                logger.info(f"   Max output tokens: None (unlimited)")
                logger.info(f"   Temperature: 0.0")
                
                request = build_vision_request(
                    model=self.llm_client.model,
                    text_prompt=json_prompt,
                    image_data_uri=data_uri,
                    temperature=0.0
                    # Removed max_output_tokens - let model use what it needs
                )
                
                logger.debug(f"   Request input structure: {type(request.get('input'))}")
                
                response = await self.llm_client.create_response(**request)
                response_text = extract_text_from_response(response, self.llm_client.model)
                
                logger.info(f"✅ Received response")
                logger.info(f"   Response length: {len(response_text)} chars")
                logger.debug(f"   Response preview: {response_text[:200]}..." if len(response_text) > 200 else f"   Response: {response_text}")
                
                # Parse JSON response with Pydantic using robust parser
                result = parse_json_with_pydantic(
                    response_text, 
                    ImageAnalysisOutput,
                    strict=True
                )
                
            except json.JSONDecodeError as e:
                logger.error(f"⚠️  JSON decode error: {e}")
                if response_text:
                    logger.error(f"   Response text: {response_text[:500]}..." if len(response_text) > 500 else f"   Response text: {response_text}")
                
                # Retry with original response and fix instructions
                logger.info(f"\n🔄 Retrying with error feedback")
                
                structured_prompt = prompt + f"""

YOUR PREVIOUS RESPONSE HAD AN ERROR:
{response_text[:1000] + '...' if len(response_text) > 1000 else response_text}

ERROR: The response was not valid JSON. Please fix it.

Return your response as valid JSON matching this exact structure:
{{
  "supports_claim": true or false,
  "image_description": "Brief description of what's shown in the image",
  "evidence_found": "Specific evidence if claim is supported, or null",
  "reasoning": "MUST say 'supports the claim' if true OR 'does not support the claim' if false",
  "confidence_notes": "Any limitations or caveats, or null"
}}

CRITICAL: The "reasoning" field MUST contain:
- The phrase "supports the claim" if supports_claim is true
- The phrase "does not support" or "doesn't support the claim" if supports_claim is false
This is REQUIRED for validation.

Return ONLY the JSON object, no other text. Do NOT wrap in ```json``` or any other markdown."""
                
                try:
                    request = build_vision_request(
                        model=self.llm_client.model,
                        text_prompt=structured_prompt,
                        image_data_uri=data_uri,
                        temperature=0.0
                        # Removed max_output_tokens - let model use what it needs
                    )
                    
                    response = await self.llm_client.create_response(**request)
                    response_text = extract_text_from_response(response, self.llm_client.model)
                    
                    logger.info(f"✅ Received retry response")
                    logger.info(f"   Response length: {len(response_text)} chars")
                    
                    # Try parsing again with robust parser
                    try:
                        # Try strict parsing first
                        result = parse_json_with_pydantic(
                            response_text, 
                            ImageAnalysisOutput,
                            strict=True
                        )
                    except Exception as pydantic_error:
                        logger.warning(f"Strict parsing failed: {pydantic_error}")
                        # Try non-strict parsing
                        result = parse_json_with_pydantic(
                            response_text, 
                            ImageAnalysisOutput,
                            strict=False
                        )
                        # Validate minimum required fields
                        if not all(key in result for key in ["supports_claim", "reasoning"]):
                            raise ValueError("Missing required fields in JSON response")
                            
                except Exception as retry_error:
                    logger.error(f"❌ Retry also failed: {retry_error}")
                    # Final fallback
                    result = {
                        "supports_claim": False,
                        "image_description": "Failed to analyze image",
                        "reasoning": f"Error: {str(retry_error)}",
                        "evidence_found": None,
                        "confidence_notes": "Analysis failed due to errors"
                    }
                    
            except Exception as e:
                from pydantic import ValidationError
                
                # Handle Pydantic validation errors specially
                if isinstance(e, ValidationError) and response_text:
                    logger.error(f"⚠️  Pydantic validation error: {e}")
                    logger.info(f"\n🔄 Retrying with validation feedback")
                    
                    # Extract the specific validation error
                    validation_errors = []
                    for error in e.errors():
                        field = error['loc'][0] if error['loc'] else 'unknown'
                        msg = error['msg']
                        validation_errors.append(f"- {field}: {msg}")
                    
                    structured_prompt = prompt + f"""

YOUR PREVIOUS RESPONSE:
{response_text[:1000] + '...' if len(response_text) > 1000 else response_text}

VALIDATION ERRORS:
{chr(10).join(validation_errors)}

Please fix these errors. Remember:
- If supports_claim is true, reasoning MUST contain "supports the claim"
- If supports_claim is false, reasoning MUST contain "does not support" or "doesn't support the claim"

Return your response as valid JSON matching this exact structure:
{{
  "supports_claim": true or false,
  "image_description": "Brief description of what's shown in the image",
  "evidence_found": "Specific evidence if claim is supported, or null",
  "reasoning": "MUST say 'supports the claim' if true OR 'does not support the claim' if false",
  "confidence_notes": "Any limitations or caveats, or null"
}}

Return ONLY the JSON object, no other text. Do NOT wrap in ```json``` or any other markdown."""
                    
                    try:
                        request = build_vision_request(
                            model=self.llm_client.model,
                            text_prompt=structured_prompt,
                            image_data_uri=data_uri,
                            # max_output_tokens=None,  # Let model use as many tokens as needed
                            temperature=0.0
                        )
                        
                        response = await self.llm_client.create_response(**request)
                        response_text = extract_text_from_response(response, self.llm_client.model)
                        
                        logger.info(f"✅ Received validation retry response")
                        
                        # Try parsing again with robust parser
                        result = parse_json_with_pydantic(
                            response_text, 
                            ImageAnalysisOutput,
                            strict=True
                        )
                        
                    except Exception as validation_retry_error:
                        logger.error(f"❌ Validation retry also failed: {validation_retry_error}")
                        # Try to get raw JSON and fix it
                        try:
                            raw_json = parse_json_response(response_text)
                            if isinstance(raw_json, dict) and 'supports_claim' in raw_json:
                                # Fix the reasoning to pass validation
                                if raw_json.get('supports_claim'):
                                    raw_json['reasoning'] = raw_json.get('reasoning', '') + ' This evidence supports the claim.'
                                else:
                                    raw_json['reasoning'] = raw_json.get('reasoning', '') + ' This image does not support the claim.'
                                result = raw_json
                            else:
                                raise
                        except:
                            result = {
                                "supports_claim": False,
                                "image_description": "Failed to analyze image",
                                "reasoning": "The image does not support the claim due to analysis errors.",
                                "evidence_found": None,
                                "confidence_notes": "Analysis failed due to validation errors"
                            }
                else:
                    # Other types of errors
                    logger.error(f"❌ Unexpected error: {e}")
                    logger.error(f"   Error type: {type(e).__name__}")
                    # Final fallback
                    result = {
                        "supports_claim": False,
                        "image_description": "Failed to analyze image",
                        "reasoning": f"The image does not support the claim. Error: {str(e)}",
                        "evidence_found": None,
                        "confidence_notes": "Analysis failed due to errors"
                    }
            
            # Add metadata and create final output
            output = {
                "image_filename": self.image_filename,
                "image_path": str(image_path.relative_to(self.cache_dir)),
                "image_type": self.image_metadata.get('role', 'Figure'),
                "page_number": self.image_metadata.get('page_number'),
                "block_id": self.image_metadata.get('block_id'),
                "claim_id": self.claim_id,
                "claim": claim,
                "supports_claim": result.get("supports_claim", False),
                "explanation": self._format_explanation(result),
                "model_used": self.llm_client.model,
                # Store detailed analysis separately
                "detailed_analysis": result
            }
            
            logger.info(f"\n📊 ANALYSIS RESULT:")
            logger.info(f"   Supports claim: {'✅ YES' if result.get('supports_claim') else '❌ NO'}")
            if result.get('reasoning'):
                logger.info(f"   Reasoning: {result['reasoning'][:200]}..." if len(str(result['reasoning'])) > 200 else f"   Reasoning: {result['reasoning']}")
            if result.get('evidence_found'):
                logger.info(f"   Evidence found: {str(result['evidence_found'])[:200]}..." if len(str(result['evidence_found'])) > 200 else f"   Evidence found: {result['evidence_found']}")
            logger.info(f"   Confidence notes: {result.get('confidence_notes', 'N/A')}")
            
            return output
            
        except Exception as e:
            logger.error(f"\n❌ ERROR: Failed to analyze image {self.image_filename}")
            logger.error(f"   Error type: {type(e).__name__}")
            logger.error(f"   Error message: {str(e)}")
            import traceback
            logger.debug(f"   Traceback:\n{traceback.format_exc()}")
            return {
                "image_filename": self.image_filename,
                "claim_id": self.claim_id,
                "claim": claim,
                "supports_claim": False,
                "explanation": f"Error analyzing image: {str(e)}",
                "error": True,
                "model_used": self.llm_client.model
            }
    
    def _format_explanation(self, result: Dict[str, Any]) -> str:
        """Format the detailed analysis into a concise explanation."""
        parts = []
        
        # Add description
        if result.get("image_description"):
            parts.append(result["image_description"])
        
        # Add evidence if found
        if result.get("evidence_found"):
            parts.append(f"Evidence: {result['evidence_found']}")
        
        # Add reasoning
        if result.get("reasoning"):
            parts.append(result["reasoning"])
        
        # Add confidence notes if any
        if result.get("confidence_notes"):
            parts.append(f"Note: {result['confidence_notes']}")
        
        return " ".join(parts) if parts else "No explanation available"