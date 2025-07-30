"""Agent for analyzing images to find evidence supporting claims."""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import base64

from .base import BaseAgent, AgentError
from ..core.responses_client import ResponsesClient
from ..config.agent_models import get_model_for_agent
from ..config.model_capabilities import build_vision_request, extract_text_from_response

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
            
            # Build multimodal prompt
            prompt = f"""Analyze if this image contains evidence supporting the claim.

CLAIM: {claim}

Return your analysis:
{{
  "supports_claim": true/false,
  "explanation": "Describe what you see in the image, then explain how and why it does (or doesn't) support the claim."
}}

Quality standards:
- First describe the image content objectively
- Then connect (or explain lack of connection) to the claim
- Be specific about the logical relationship
- Include specific data points, numbers, or text visible in the image"""

            # Create data URI for image
            data_uri = f"data:{mime_type};base64,{image_base64}"
            
            # Use model capabilities to build appropriate request
            request = build_vision_request(
                model=self.llm_client.model,
                text_prompt=prompt,
                image_data_uri=data_uri,
                max_output_tokens=1000,
                temperature=0.0
            )
            
            response = await self.llm_client.create_response(**request)
            
            # Extract response text using model-specific handler
            response_text = extract_text_from_response(response, self.llm_client.model)
            
            # Parse JSON response
            import json
            try:
                result = json.loads(response_text)
            except json.JSONDecodeError:
                # Fallback parsing if response isn't valid JSON
                logger.warning(f"Failed to parse JSON response, using fallback")
                result = {
                    "supports_claim": False,
                    "explanation": response_text
                }
            
            # Add metadata
            output = {
                "image_filename": self.image_filename,
                "image_path": str(image_path.relative_to(self.cache_dir)),
                "claim_id": self.claim_id,
                "claim": claim,
                **result,
                "model_used": self.llm_client.model
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