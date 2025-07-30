"""Agent for analyzing images to find evidence supporting claims."""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import base64

from .base import BaseAgent, AgentError
from ..core.responses_client import ResponsesClient
from ..config.agent_models import get_model_for_agent
from ..config.model_capabilities import build_vision_request, extract_text_from_response
from ..models.image_outputs import ImageAnalysisOutput
from ..utils.llm_parser import LLMResponseParser

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
        image_filename: str,
        cache_dir: Path = Path("data/cache"),
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize image evidence analyzer for a specific image.
        
        Args:
            pdf_name: Name of the PDF document
            claim_id: ID of the claim being processed
            image_filename: Name of the image file to analyze
            cache_dir: Base cache directory
            config: Agent configuration
        """
        super().__init__(pdf_name, cache_dir, config)
        self.claim_id = claim_id
        self.image_filename = image_filename
        
        # Store results per image
        image_id = image_filename.replace('.png', '').replace('.jpg', '')
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
        
        logger.info(f"Analyzing image {self.image_filename} for claim {self.claim_id}")
        
        # Build image path
        image_path = self.pdf_dir / "extracted" / "figures" / self.image_filename
        
        if not image_path.exists():
            logger.warning(f"Image file not found: {image_path}")
            return {
                "image_filename": self.image_filename,
                "supports_claim": False,
                "explanation": "Image file not found",
                "error": True
            }
        
        try:
            # Read and encode image
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # Encode to base64 for LLM
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Determine image mime type
            mime_type = "image/png" if image_path.suffix == ".png" else "image/jpeg"
            
            # Build comprehensive multimodal prompt
            prompt = f"""You are analyzing an image from a medical/clinical document to determine if it contains evidence supporting a specific claim.

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
  "reasoning": "Detailed explanation of why this does or doesn't support the claim",
  "confidence_notes": "Any limitations, caveats, or confidence issues (null if none)"
}}

Focus on clear, evidence-based reasoning that explains your determination."""

            # Create data URI for image
            data_uri = f"data:{mime_type};base64,{image_base64}"
            
            # Parse with retry using Pydantic model
            try:
                # Build request without prompt (will be added by parser)
                base_request = build_vision_request(
                    model=self.llm_client.model,
                    text_prompt="",  # Parser will add the prompt
                    image_data_uri=data_uri,
                    max_output_tokens=1500,
                    temperature=0.0
                )
                
                # Use the robust parser with retry logic
                parsed_output = await LLMResponseParser.parse_with_retry(
                    llm_client=self.llm_client,
                    prompt=prompt,
                    output_model=ImageAnalysisOutput,
                    max_retries=2,
                    temperature=0.0,
                    max_output_tokens=1500,
                    # Pass the image data through kwargs
                    model=self.llm_client.model,
                    input=[{
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": prompt},
                            {"type": "input_image", "image_url": data_uri}
                        ]
                    }],
                    tools=base_request.get("tools")  # Include tools if needed for o4-mini
                )
                
                # Convert Pydantic model to dict
                result = parsed_output.dict()
                
            except Exception as e:
                logger.error(f"Failed to parse image analysis: {e}")
                # Fallback to direct parsing
                request = build_vision_request(
                    model=self.llm_client.model,
                    text_prompt=prompt,
                    image_data_uri=data_uri,
                    max_output_tokens=1500,
                    temperature=0.0
                )
                response = await self.llm_client.create_response(**request)
                response_text = extract_text_from_response(response, self.llm_client.model)
                
                # Try to parse as JSON one more time
                import json
                try:
                    result = json.loads(response_text)
                except:
                    result = {
                        "supports_claim": False,
                        "image_description": "Failed to parse response",
                        "reasoning": response_text[:500],
                        "evidence_found": None,
                        "confidence_notes": "Parsing error occurred"
                    }
            
            # Add metadata and create final output
            output = {
                "image_filename": self.image_filename,
                "image_path": str(image_path.relative_to(self.cache_dir)),
                "claim_id": self.claim_id,
                "claim": claim,
                "supports_claim": result.get("supports_claim", False),
                "explanation": self._format_explanation(result),
                "model_used": self.llm_client.model,
                # Store detailed analysis separately
                "detailed_analysis": result
            }
            
            logger.info(f"  Result: {'Supports' if result.get('supports_claim') else 'Does not support'} claim")
            
            return output
            
        except Exception as e:
            logger.error(f"Failed to analyze image {self.image_filename}: {e}")
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