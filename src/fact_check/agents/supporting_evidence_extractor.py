"""Agent for extracting supporting evidence snippets from documents."""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from src.interfaces import Document, StandardDocumentReader

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
        
        # Load document
        content_path = self.pdf_dir / "extracted" / "content.json"
        document_data = self.load_json(content_path)
        document = Document(**document_data)
        
        # Create fact check interface
        interface = StandardDocumentReader(document)
        
        # Get normalized text (our single operating model)
        normalized_text = interface.get_full_text(include_figure_descriptions=True, normalize=True)
        
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
                "location": {
                    "start": snippet.start,
                    "end": snippet.end,
                    "page_index": page_info.get("page_index"),
                    "page_number": page_info.get("page_number")
                }
            }
            output["supporting_snippets"].append(snippet_data)
        
        output["model_used"] = self.llm_client.model
        
        return output
    
    def _find_snippet_page(self, snippet, interface: StandardDocumentReader) -> Dict[str, Any]:
        """Find which page a snippet appears on using normalized positions."""
        if snippet.start is None:
            return {"page_index": None, "page_number": None}
            
        # Get normalized text to reconstruct the same document the LLM saw
        full_text = interface.get_full_text(include_figure_descriptions=True, normalize=True)
        
        # Get normalized text blocks with locations
        text_with_locs = interface.get_text_with_locations(normalize=True)
        
        # Build position map matching get_full_text construction
        current_pos = 0
        last_page = -1
        
        for text, metadata in text_with_locs:
            page_idx = metadata["page_index"]
            
            # Add page separator if we moved to a new page
            if page_idx > last_page and last_page >= 0:
                separator = f"\n\n[Page {page_idx + 1}]\n"
                current_pos += len(separator)
                last_page = page_idx
            elif last_page == -1:
                last_page = page_idx
            
            # Check if snippet starts within this block
            text_len = len(text)
            if current_pos <= snippet.start < current_pos + text_len:
                return {
                    "page_index": metadata["page_index"],
                    "page_number": metadata["page_index"] + 1
                }
            
            # Move position forward (text + "\n\n" separator)
            current_pos += text_len + 2
        
        return {"page_index": None, "page_number": None}