"""Agent for extracting supporting evidence snippets from documents."""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..utils import document_utils
from ..core.responses_client import ResponsesClient
from ..models.llm_outputs import ExtractorOutput
from ..utils.llm_parser import LLMResponseParser
from .base import BaseAgent, AgentError

logger = logging.getLogger(__name__)


class EvidenceExtractor(BaseAgent):
    """Extract relevant text snippets for claims from documents"""
    
    @property
    def agent_name(self) -> str:
        return "evidence_extractor"
    
    @property
    def required_inputs(self) -> List[str]:
        # Only need the extracted document
        return ["extracted/content.json"]
    
    def __init__(
        self, 
        pdf_name: str,
        claim_id: str,
        cache_dir: Path = Path("data/cache"),
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize supporting evidence extractor agent.
        
        Args:
            pdf_name: Name of the PDF document
            claim_id: ID of the claim being processed (e.g., "claim_001")
            cache_dir: Base cache directory
            config: Agent configuration
        """
        super().__init__(pdf_name, cache_dir, config)
        self.claim_id = claim_id
        
        # Override agent directory to be claim-specific
        self.agent_dir = self.pdf_dir / "agents" / "claims" / claim_id / self.agent_name
        self.agent_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up LLM client
        self.llm_client = ResponsesClient()
        self.llm_client.model = self.config.get("model", "gpt-4.1")
    
    async def process(self) -> Dict[str, Any]:
        """
        Extract supporting evidence for the claim.
        
        Returns:
            Dictionary containing extracted evidence
        """
        # Get the claim text from config
        claim = self.config.get("claim")
        if not claim:
            raise AgentError("No claim provided in config")
        
        logger.info(f"Extracting evidence for {self.claim_id}: {claim[:50]}...")
        
        # Load document JSON directly
        content_path = self.pdf_dir / "extracted" / "content.json"
        document_data = self.load_json(content_path)
        
        # Get normalized text using utility
        normalized_text = document_utils.get_text(document_data, include_figures=True)
        
        # Build extraction prompt
        prompt = f'''Extract VERBATIM quotes from the document that support this claim.

Rules:
- Quotes must be exact text from the document (no modifications)
- No ellipsis (...) - extract complete segments
- A quote supports the claim if it provides evidence, data, or statements that directly relate to and affirm the claim

Standard for "supports the claim":
"Would this quote help convince a skeptical reader that the claim is true?"

CLAIM: {claim}

Return your response as a JSON object:
{{
    "snippets": [
        {{
            "quote": "exact quote from document",
            "relevance_explanation": "1-2 sentences explaining how this supports the claim"
        }}
    ]
}}

DOCUMENT:
{normalized_text}'''

        try:
            # Parse with retry
            extracted = await LLMResponseParser.parse_with_retry(
                llm_client=self.llm_client,
                prompt=prompt,
                output_model=ExtractorOutput,
                max_retries=2,
                temperature=0.0,
                max_output_tokens=4000
            )
            
            # Structure output
            output = {
                "claim_id": self.claim_id,
                "claim": claim,
                "document": {
                    "pdf_name": self.pdf_name,
                    "source_pdf": document_data.get("source_pdf", ""),
                    "total_pages": len(document_data.get("reading_order", [])),
                    "total_blocks": len(document_data.get("blocks", [])),
                    "total_characters": len(normalized_text)
                },
                "extraction_result": {
                    "success": True,
                    "total_snippets_found": len(extracted.snippets),
                    "error": None
                },
                "extracted_evidence": []
            }
            
            # Add snippets without position tracking
            for i, snippet in enumerate(extracted.snippets):
                snippet_data = {
                    "id": i + 1,
                    "quote": snippet.quote,
                    "relevance_explanation": snippet.relevance_explanation
                }
                output["extracted_evidence"].append(snippet_data)
            
            output["model_used"] = self.llm_client.model
            
            return output
            
        except Exception as e:
            logger.error(f"Failed to extract evidence: {e}")
            # Return error structure
            return {
                "claim_id": self.claim_id,
                "claim": claim,
                "document": {
                    "pdf_name": self.pdf_name,
                    "source_pdf": document_data.get("source_pdf", ""),
                    "total_pages": len(document_data.get("reading_order", [])),
                    "total_blocks": len(document_data.get("blocks", [])),
                    "total_characters": len(normalized_text)
                },
                "extraction_result": {
                    "success": False,
                    "total_snippets_found": 0,
                    "error": str(e)
                },
                "extracted_evidence": [],
                "model_used": self.llm_client.model
            }
    
