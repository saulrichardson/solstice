"""Text evidence finder agent that searches for textual evidence supporting or contradicting claims"""

import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from .base import BaseAgent, AgentError
from fact_check.fact_checker import FactChecker, VerificationResult
from fact_check.core.responses_client import ResponsesClient
from injestion.models.document import Document
from injestion.processing.fact_check_interface import FactCheckInterface

logger = logging.getLogger(__name__)


class TextEvidenceFinder(BaseAgent):
    """Agent that finds textual evidence for claims in document content"""
    
    @property
    def agent_name(self) -> str:
        return "text_evidence_finder"
    
    @property
    def required_inputs(self) -> List[str]:
        # Dynamic based on claims source
        base_inputs = ["extracted/content.json"]
        
        # Check if we have standalone claims or claims_file
        if hasattr(self, 'config'):
            if self.config.get('standalone_claims') or self.config.get('claims_file'):
                return base_inputs
        
        # Otherwise require claim extractor output
        return base_inputs + ["agents/claim_extractor/output.json"]
    
    def __init__(
        self, 
        pdf_name: str, 
        cache_dir: Path = Path("data/cache"),
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize text evidence finder agent.
        
        Config options:
            - model: LLM model to use (default: "gpt-4.1")
            - gateway_url: Gateway URL (default: from environment)
            - standalone_claims: List of claims to verify (if not using claim extractor)
            - claims_file: Path to JSON file containing claims
            - include_evidence_images: Whether to include figure/table images
        """
        super().__init__(pdf_name, cache_dir, config)
        
        # Set up LLM client
        gateway_url = self.config.get("gateway_url")
        self.llm_client = ResponsesClient(base_url=gateway_url)
        self.fact_checker = FactChecker(self.llm_client)
        
        # Check if we're using standalone claims or claim extractor output
        self.standalone_claims = self.config.get("standalone_claims", [])
    
    async def process(self) -> Dict[str, Any]:
        """
        Process claims and verify them against the document.
        
        Returns:
            Dictionary containing verification results
        """
        # Load document
        content_path = self.pdf_dir / "extracted" / "content.json"
        document_data = self.load_json(content_path)
        document = Document(**document_data)
        
        # Create fact check interface
        interface = FactCheckInterface(document)
        document_text = interface.get_full_text(include_figure_descriptions=True)
        
        # Get claims to verify
        if self.standalone_claims:
            claims = self.standalone_claims
            logger.info(f"Verifying {len(claims)} standalone claims")
        elif self.config.get("claims_file"):
            # Load claims from file
            claims_file = Path(self.config["claims_file"])
            if not claims_file.is_absolute():
                # Assume relative to project root
                claims_file = Path("data/claims") / claims_file
            
            if claims_file.exists():
                claims_data = self.load_json(claims_file)
                claims = [c["claim"] for c in claims_data.get("claims", [])]
                logger.info(f"Loaded {len(claims)} claims from {claims_file}")
            else:
                raise AgentError(f"Claims file not found: {claims_file}")
        else:
            # Load claims from claim extractor
            try:
                claims_data = self.get_upstream_output("claim_extractor")
                claims = claims_data.get("claims", [])
                logger.info(f"Loaded {len(claims)} claims from claim extractor")
            except AgentError:
                logger.warning("No claim extractor output found, using empty claims list")
                claims = []
        
        # Verify each claim
        results = []
        for i, claim in enumerate(claims):
            logger.info(f"Finding text evidence for claim {i+1}/{len(claims)}: {claim[:100]}...")
            
            try:
                # Check the claim
                result = await self.fact_checker.check_claim(claim, document_text)
                
                # Convert to serializable format
                verification = {
                    "claim": claim,
                    "verdict": result.verdict,
                    "confidence": result.confidence,
                    "success": result.success,
                    "reasoning_steps": []
                }
                
                if result.steps:
                    for step in result.steps:
                        verification["reasoning_steps"].append({
                            "id": step.id,
                            "reasoning": step.reasoning,
                            "quote": step.quote,
                            "start": step.start,
                            "end": step.end
                        })
                
                if result.offending_quote:
                    verification["error"] = f"Quote not found: {result.offending_quote}"
                
                results.append(verification)
                
            except Exception as e:
                logger.error(f"Failed to find evidence for claim: {e}")
                results.append({
                    "claim": claim,
                    "verdict": "error",
                    "confidence": 0.0,
                    "success": False,
                    "error": str(e)
                })
        
        # Get visual elements if requested
        visual_elements = []
        if self.config.get("include_evidence_images", False):
            visual_elements = interface.get_figures_and_tables(include_images=True)
        
        # Prepare output
        output = {
            "document": {
                "pdf_name": self.pdf_name,
                "source_pdf": document.source_pdf,
                "total_pages": len(document.reading_order),
                "total_blocks": len(document.blocks)
            },
            "verification_results": results,
            "summary": {
                "total_claims": len(claims),
                "verified_claims": sum(1 for r in results if r["success"]),
                "supporting_claims": sum(1 for r in results if r.get("verdict") == "supports"),
                "contradicting_claims": sum(1 for r in results if r.get("verdict") == "does_not_support"),
                "insufficient_evidence": sum(1 for r in results if r.get("verdict") == "insufficient"),
                "errors": sum(1 for r in results if r.get("verdict") == "error")
            },
            "visual_elements": visual_elements,
            "model_used": self.config.get("model", "gpt-4.1")
        }
        
        # Save additional outputs
        self.save_json(output["summary"], "summary.json")
        self.save_json(output["verification_results"], "verification_results.json")
        
        return output