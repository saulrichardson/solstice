"""Agent for extracting supporting evidence snippets from documents."""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..utils import document_utils
from ..core.responses_client import ResponsesClient
from ..evidence_extractor import EvidenceExtractor
from .base import BaseAgent, AgentError

logger = logging.getLogger(__name__)


class SupportingEvidenceExtractor(BaseAgent):
    """Extract supporting text snippets for claims from documents"""
    
    @property
    def agent_name(self) -> str:
        return "supporting_evidence"
    
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
        self.evidence_extractor = EvidenceExtractor(self.llm_client, config={"disable_cache": True})
    
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
        
        # Extract supporting evidence (synchronous now)
        result = self.evidence_extractor.extract_supporting_evidence(
            claim=claim,
            document_text=normalized_text
        )
        
        # Structure output
        output = {
            "claim_id": self.claim_id,
            "claim": claim,
            "document": {
                "pdf_name": self.pdf_name,
                "source_pdf": document_data.get("source_pdf", ""),
                "total_pages": len(document_data.get("reading_order", [])),
                "total_blocks": len(document_data.get("blocks", []))
            },
            "extraction_result": {
                "success": result.success,
                "total_snippets_found": result.total_snippets_found,
                "error": result.error
            },
            "supporting_snippets": []
        }
        
        # Add snippets without position tracking
        for snippet in result.supporting_snippets:
            snippet_data = {
                "id": snippet.id,
                "quote": snippet.quote,
                "relevance_explanation": snippet.relevance_explanation
            }
            output["supporting_snippets"].append(snippet_data)
        
        output["model_used"] = self.llm_client.model
        
        return output
    
