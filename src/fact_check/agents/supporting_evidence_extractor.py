"""Agent for extracting supporting evidence snippets from documents."""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from injestion.models.document import Document
from injestion.processing.fact_check_interface import FactCheckInterface

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
        cache_dir: Path = Path("data/cache"),
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize supporting evidence extractor agent.
        
        Config options:
            - model: LLM model to use (default: "gpt-4.1")
            - include_context: Whether to include surrounding context
            - max_snippets_per_claim: Maximum snippets to extract per claim
        """
        super().__init__(pdf_name, cache_dir, config)
        
        # Set up LLM client
        self.llm_client = ResponsesClient()
        self.llm_client.model = self.config.get("model", "gpt-4.1")
        self.evidence_extractor = EvidenceExtractor(self.llm_client)
        
        # Config options
        self.include_context = self.config.get("include_context", True)
        self.max_snippets = self.config.get("max_snippets_per_claim", 10)
    
    async def process(self) -> Dict[str, Any]:
        """
        Process document and extract supporting evidence.
        
        This method is called by the pipeline but we won't use it directly
        for claim processing. Instead, we'll have a separate method for
        processing individual claims.
        """
        # This shouldn't be called in the new architecture
        raise NotImplementedError(
            "SupportingEvidenceExtractor should be called via process_claim() "
            "in the claim-centric workflow"
        )
    
    async def process_claim(self, claim: str, claim_id: str) -> Dict[str, Any]:
        """
        Extract supporting evidence for a single claim.
        
        Args:
            claim: The claim text
            claim_id: Unique identifier for this claim (e.g., "claim_001")
            
        Returns:
            Dictionary containing extracted evidence
        """
        logger.info(f"Extracting evidence for {claim_id}: {claim[:50]}...")
        
        # Load document
        content_path = self.pdf_dir / "extracted" / "content.json"
        document_data = self.load_json(content_path)
        document = Document(**document_data)
        
        # Create fact check interface
        interface = FactCheckInterface(document)
        document_text = interface.get_full_text(include_figure_descriptions=True)
        
        # Extract supporting evidence
        result = await self.evidence_extractor.extract_supporting_evidence(claim, document_text)
        
        # Structure output
        output = {
            "claim_id": claim_id,
            "claim": claim,
            "document": {
                "pdf_name": self.pdf_name,
                "source_pdf": document.source_pdf,
                "total_pages": len(document.reading_order),
                "total_blocks": len(document.blocks)
            },
            "extraction_result": {
                "success": result.success,
                "total_snippets_found": result.total_snippets_found,
                "error": result.error
            },
            "supporting_snippets": []
        }
        
        # Add page information to snippets
        for snippet in result.supporting_snippets:
            # Find which page this snippet is on
            page_info = self._find_snippet_page(snippet, interface)
            
            snippet_data = {
                "id": snippet.id,
                "quote": snippet.quote,
                "relevance_explanation": snippet.relevance_explanation,
                "context": snippet.context,
                "location": {
                    "start": snippet.start,
                    "end": snippet.end,
                    "page_index": page_info.get("page_index"),
                    "page_number": page_info.get("page_number")
                }
            }
            output["supporting_snippets"].append(snippet_data)
        
        # Get any relevant visual elements
        if self.config.get("include_visual_references", False):
            visual_elements = interface.get_figures_and_tables()
            output["visual_elements"] = [
                {
                    "type": elem["role"],
                    "page": elem["page_index"] + 1,
                    "description": elem["description"][:200]
                }
                for elem in visual_elements
            ]
        else:
            output["visual_elements"] = []
        
        output["model_used"] = self.llm_client.model
        
        return output
    
    def _find_snippet_page(self, snippet, interface: FactCheckInterface) -> Dict[str, Any]:
        """Find which page a snippet appears on."""
        if snippet.start is None:
            return {"page_index": None, "page_number": None}
            
        # Get text with locations to find the page
        text_with_locs = interface.get_text_with_locations()
        current_pos = 0
        
        for text, metadata in text_with_locs:
            text_len = len(text)
            if current_pos <= snippet.start < current_pos + text_len:
                return {
                    "page_index": metadata["page_index"],
                    "page_number": metadata["page_index"] + 1
                }
            current_pos += text_len + 1  # +1 for space between blocks
        
        return {"page_index": None, "page_number": None}