"""Agent for checking completeness of evidence extraction and finding missing evidence."""

import logging
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from .base import BaseAgent, AgentError
from ..core.responses_client import ResponsesClient
from ..evidence_extractor import EvidenceExtractor

logger = logging.getLogger(__name__)


class CompletenessChecker(BaseAgent):
    """
    Check for missing evidence and extract additional snippets.
    
    This agent:
    1. Reviews existing validated evidence
    2. Analyzes the document for potentially missed evidence
    3. Extracts additional supporting quotes
    4. Ensures comprehensive coverage of the claim
    """
    
    @property
    def agent_name(self) -> str:
        return "completeness_checker"
    
    @property
    def required_inputs(self) -> List[str]:
        return [
            "extracted/content.json",
            f"agents/claims/{self.claim_id}/evidence_critic/output.json"
        ]
    
    def __init__(
        self, 
        pdf_name: str,
        claim_id: str,
        cache_dir: Path = Path("data/cache"),
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize completeness checker agent."""
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
        Check for missing evidence and extract additional snippets.
        
        Returns:
            Dictionary containing all evidence (existing + new)
        """
        logger.info(f"Checking evidence completeness for {self.claim_id}")
        
        # Get validated evidence from critic
        critic_path = self.pdf_dir / "agents" / "claims" / self.claim_id / "evidence_critic" / "output.json"
        critic_data = self.load_json(critic_path)
        
        # Load document
        content_path = self.pdf_dir / "extracted" / "content.json"
        document_data = self.load_json(content_path)
        
        # Import here to avoid circular imports
        from src.injestion.models.document import Document
        from src.injestion.processing.fact_check_interface import FactCheckInterface
        
        document = Document(**document_data)
        interface = FactCheckInterface(document)
        normalized_text = interface.get_full_text(include_figure_descriptions=True, normalize=True)
        
        claim = self.config.get("claim")
        if not claim:
            raise AgentError("No claim provided in config")
        
        # Get existing evidence
        existing_snippets = critic_data.get("validated_snippets", [])
        existing_quotes = [s.get("verified_quote", s.get("quote", "")) for s in existing_snippets]
        
        # Analyze completeness
        completeness_analysis = await self._analyze_completeness(
            claim=claim,
            existing_evidence=existing_snippets,
            document_text=normalized_text[:5000]  # First 5000 chars for context
        )
        
        # Find additional evidence if needed
        additional_snippets = []
        if completeness_analysis["needs_more_evidence"]:
            additional_snippets = await self._find_additional_evidence(
                claim=claim,
                document_text=normalized_text,
                existing_quotes=existing_quotes,
                missing_aspects=completeness_analysis["missing_aspects"]
            )
        
        # Combine all evidence (existing validated + new)
        all_snippets = existing_snippets + additional_snippets
        
        output = {
            "claim_id": self.claim_id,
            "claim": claim,
            "document": self.pdf_name,
            "completeness_analysis": completeness_analysis,
            "completeness_stats": {
                "existing_snippets": len(existing_snippets),
                "new_snippets_found": len(additional_snippets),
                "total_snippets": len(all_snippets),
                "completeness_score": completeness_analysis["completeness_score"]
            },
            "validated_snippets": existing_snippets,  # Already validated evidence
            "new_snippets": additional_snippets,      # New evidence to be verified
            "all_snippets": all_snippets             # Combined for next stage
        }
        
        logger.info(
            f"Found {output['completeness_stats']['new_snippets_found']} additional snippets, "
            f"total: {output['completeness_stats']['total_snippets']} "
            f"(completeness: {completeness_analysis['completeness_score']:.0%})"
        )
        
        return output
    
    async def _analyze_completeness(
        self,
        claim: str,
        existing_evidence: List[Dict[str, Any]],
        document_text: str
    ) -> Dict[str, Any]:
        """
        Analyze whether existing evidence fully supports the claim.
        
        Returns:
            Analysis of completeness with missing aspects
        """
        # Format existing evidence for analysis
        evidence_summary = "\n".join([
            f"- {e.get('verified_quote', e.get('quote', ''))[:200]}... "
            f"(Score: {e.get('critic_evaluation', {}).get('overall_score', 'N/A')})"
            for e in existing_evidence[:10]  # Limit to top 10
        ])
        
        prompt = f"""You are analyzing whether extracted evidence fully supports a claim.

CLAIM: {claim}

EXISTING EVIDENCE FOUND ({len(existing_evidence)} pieces):
{evidence_summary}

DOCUMENT PREVIEW (first 5000 characters):
{document_text}

Please analyze:
1. Does the existing evidence fully support all aspects of the claim?
2. What aspects of the claim might need additional evidence?
3. Are there other sections of the document that might contain relevant evidence?

Provide your response in this format:
COMPLETENESS_SCORE: [0.0-1.0, where 1.0 means fully complete]
NEEDS_MORE_EVIDENCE: [YES/NO]
MISSING_ASPECTS: [List key aspects that need more evidence, one per line]
SUGGESTED_SEARCH_AREAS: [Areas in document to search for additional evidence]
ANALYSIS: [Brief explanation of completeness assessment]
"""

        try:
            # Call create_response synchronously (it's not async)
            response_dict = self.llm_client.create_response(
                input=prompt,
                model=self.llm_client.model,
                temperature=0.0,
                max_output_tokens=1000
            )
            response = self.llm_client.extract_text(response_dict)
            return self._parse_completeness_response(response)
            
        except Exception as e:
            logger.error(f"Error analyzing completeness: {e}")
            # Default to not needing more evidence on error
            return {
                "completeness_score": 0.8,
                "needs_more_evidence": False,
                "missing_aspects": [],
                "suggested_search_areas": [],
                "analysis": "Error in completeness analysis, assuming sufficient evidence"
            }
    
    async def _find_additional_evidence(
        self, 
        claim: str, 
        document_text: str,
        existing_quotes: List[str],
        missing_aspects: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Find additional evidence not in existing quotes.
        
        Returns:
            List of new evidence snippets
        """
        # Create focused prompt based on missing aspects
        missing_aspects_text = "\n".join([f"- {aspect}" for aspect in missing_aspects]) if missing_aspects else "General additional support"
        
        # Format existing evidence to avoid duplicates
        existing_evidence_text = "\n".join([f"- {quote[:150]}..." for quote in existing_quotes[:10]])
        
        # We'll use the regular evidence extractor and let it find additional evidence

        try:
            # Use the evidence extractor to find additional evidence
            # Modify the claim to focus on missing aspects
            focused_claim = claim
            if missing_aspects:
                focused_claim = f"{claim} (specifically regarding: {', '.join(missing_aspects)})"
            
            result = self.evidence_extractor.extract_supporting_evidence(
                claim=focused_claim,
                document_text=document_text
            )
            
            # Process results - trust the LLM to not duplicate
            new_snippets = []
            for snippet in result.supporting_snippets:
                new_snippet = {
                    "id": f"comp_{snippet.id}",
                    "quote": snippet.quote,
                    "relevance_explanation": snippet.relevance_explanation,
                    "location": {
                        "start": snippet.start,
                        "end": snippet.end
                    },
                    "source": "completeness_check",
                    "metadata": {
                        "extraction_round": 2,
                        "targeted_aspect": missing_aspects[0] if missing_aspects else "general"
                    }
                }
                new_snippets.append(new_snippet)
            
            return new_snippets
            
        except Exception as e:
            logger.error(f"Error finding additional evidence: {e}")
            return []
    
    
    def _parse_completeness_response(self, response: str) -> Dict[str, Any]:
        """Parse the completeness analysis response."""
        # Default values
        result = {
            "completeness_score": 0.8,
            "needs_more_evidence": False,
            "missing_aspects": [],
            "suggested_search_areas": [],
            "analysis": ""
        }
        
        try:
            lines = response.strip().split('\n')
            current_key = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    # Reset on empty line
                    current_key = None
                    continue
                
                # Check for key:value pairs
                if ':' in line and not current_key:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        key = parts[0].strip().upper()
                        value = parts[1].strip()
                        
                        if key == "COMPLETENESS_SCORE":
                            try:
                                score = float(value.split()[0])  # Handle "0.8 (80%)"
                                result["completeness_score"] = max(0.0, min(1.0, score))  # Clamp to 0-1
                            except (ValueError, IndexError):
                                logger.warning(f"Could not parse completeness score: {value}")
                        elif key == "NEEDS_MORE_EVIDENCE":
                            result["needs_more_evidence"] = value.upper().startswith("YES")
                        elif key == "MISSING_ASPECTS":
                            current_key = "missing_aspects"
                            if value:  # If value on same line
                                result["missing_aspects"].append(value)
                        elif key == "SUGGESTED_SEARCH_AREAS":
                            current_key = "suggested_search_areas"
                            if value:
                                result["suggested_search_areas"].append(value)
                        elif key == "ANALYSIS":
                            result["analysis"] = value
                            current_key = "analysis"
                elif current_key in ["missing_aspects", "suggested_search_areas"]:
                    # Handle list items (with or without dash)
                    item = line[1:].strip() if line.startswith("-") else line
                    if item:
                        result[current_key].append(item)
                elif current_key == "analysis" and line:
                    # Handle multi-line analysis
                    result["analysis"] += " " + line
            
            # Ensure consistency between score and needs_more_evidence
            if result["completeness_score"] < 0.7 and not result["needs_more_evidence"]:
                logger.info("Low completeness score but needs_more_evidence=False, setting to True")
                result["needs_more_evidence"] = True
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing completeness response: {e}")
            logger.debug(f"Response was: {response[:500]}...")
            return result