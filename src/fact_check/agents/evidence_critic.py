"""Agent for critiquing individual pieces of evidence for quality and relevance."""

import logging
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..core.responses_client import ResponsesClient
from .base import BaseAgent, AgentError

logger = logging.getLogger(__name__)


class EvidenceCritic(BaseAgent):
    """
    Critique individual evidence snippets for relevance and quality.
    
    This agent evaluates each piece of evidence individually to ensure:
    1. Direct relevance to the claim
    2. High quality and specificity
    3. Proper contextual usage
    """
    
    @property
    def agent_name(self) -> str:
        return "evidence_critic"
    
    @property
    def required_inputs(self) -> List[str]:
        return [f"agents/claims/{self.claim_id}/regex_verifier/output.json"]
    
    def __init__(
        self, 
        pdf_name: str,
        claim_id: str,
        cache_dir: Path = Path("data/cache"),
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize evidence critic agent."""
        super().__init__(pdf_name, cache_dir, config)
        self.claim_id = claim_id
        
        # Override agent directory to be claim-specific
        self.agent_dir = self.pdf_dir / "agents" / "claims" / claim_id / self.agent_name
        self.agent_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up LLM client
        self.llm_client = ResponsesClient()
        self.llm_client.model = self.config.get("model", "gpt-4.1")
        
        # Configurable thresholds
        self.relevance_threshold = self.config.get("relevance_threshold", 6.0)
        self.quality_threshold = self.config.get("quality_threshold", 5.0)
        self.overall_threshold = self.config.get("overall_threshold", 6.0)
    
    async def process(self) -> Dict[str, Any]:
        """
        Critique each evidence snippet for quality and relevance.
        
        Returns:
            Dictionary containing validated and rejected snippets with detailed assessments
        """
        logger.info(f"Critiquing evidence for {self.claim_id}")
        
        # Get verified evidence from regex verifier
        verifier_path = self.pdf_dir / "agents" / "claims" / self.claim_id / "regex_verifier" / "output.json"
        verifier_data = self.load_json(verifier_path)
        
        claim = self.config.get("claim")
        if not claim:
            raise AgentError("No claim provided in config")
        
        validated_snippets = []
        rejected_snippets = []
        
        # Process each verified snippet with concurrent evaluation for efficiency
        snippets_to_evaluate = verifier_data.get("verified_snippets", [])
        
        # Batch process for efficiency if many snippets
        if len(snippets_to_evaluate) > 5:
            # Process in batches of 3 for API efficiency
            batch_size = 3
            for i in range(0, len(snippets_to_evaluate), batch_size):
                batch = snippets_to_evaluate[i:i + batch_size]
                tasks = []
                for snippet in batch:
                    quote = snippet.get("verified_quote", snippet.get("quote", ""))
                    task = self._critique_snippet(
                        claim=claim,
                        quote=quote,
                        relevance_explanation=snippet.get("relevance_explanation", "")
                    )
                    tasks.append(task)
                
                # Wait for batch to complete
                results = await asyncio.gather(*tasks)
                
                # Process results
                for snippet, critique_result in zip(batch, results):
                    self._process_critique_result(snippet, critique_result, validated_snippets, rejected_snippets)
        else:
            # Process sequentially for small sets
            for snippet in snippets_to_evaluate:
                quote = snippet.get("verified_quote", snippet.get("quote", ""))
                critique_result = await self._critique_snippet(
                    claim=claim,
                    quote=quote,
                    relevance_explanation=snippet.get("relevance_explanation", "")
                )
                self._process_critique_result(snippet, critique_result, validated_snippets, rejected_snippets)
        
        # Sort validated snippets by overall score (best first)
        validated_snippets.sort(
            key=lambda x: x["critic_evaluation"]["overall_score"], 
            reverse=True
        )
        
        output = {
            "claim_id": self.claim_id,
            "claim": claim,
            "document": self.pdf_name,
            "critic_stats": {
                "total_evaluated": len(snippets_to_evaluate),
                "approved": len(validated_snippets),
                "rejected": len(rejected_snippets),
                "approval_rate": len(validated_snippets) / len(snippets_to_evaluate) 
                                if snippets_to_evaluate else 0,
                "average_score": sum(s["critic_evaluation"]["overall_score"] for s in validated_snippets) / len(validated_snippets)
                                if validated_snippets else 0,
                "score_distribution": self._get_score_distribution(validated_snippets)
            },
            "validated_snippets": validated_snippets,
            "rejected_snippets": rejected_snippets
        }
        
        logger.info(
            f"Approved {output['critic_stats']['approved']} of "
            f"{output['critic_stats']['total_evaluated']} snippets "
            f"(avg score: {output['critic_stats']['average_score']:.2f})"
        )
        
        return output
    
    def _process_critique_result(self, snippet: Dict[str, Any], critique_result: Dict[str, Any], 
                                 validated_snippets: List[Dict], rejected_snippets: List[Dict]):
        """Process a critique result and categorize the snippet."""
        # Add critique metadata
        snippet["critic_evaluation"] = {
            "relevance_score": critique_result["relevance_score"],
            "quality_score": critique_result["quality_score"],
            "specificity_score": critique_result["specificity_score"],
            "overall_score": critique_result["overall_score"],
            "strength": critique_result["strength"],
            "assessment": critique_result["assessment"]
        }
        
        if critique_result["is_valid"]:
            validated_snippets.append(snippet)
        else:
            snippet["critic_evaluation"]["rejection_reason"] = critique_result["rejection_reason"]
            rejected_snippets.append(snippet)
    
    def _get_score_distribution(self, validated_snippets: List[Dict]) -> Dict[str, int]:
        """Get distribution of evidence strength."""
        distribution = {"STRONG": 0, "MODERATE": 0, "WEAK": 0}
        for snippet in validated_snippets:
            strength = snippet["critic_evaluation"]["strength"]
            if strength in distribution:
                distribution[strength] += 1
        return distribution
    
    async def _critique_snippet(
        self, 
        claim: str, 
        quote: str, 
        relevance_explanation: str
    ) -> Dict[str, Any]:
        """
        Critique a single snippet using AI-forward evaluation.
        
        Returns:
            Dictionary with validation result and detailed scores
        """
        prompt = f"""You are an expert evidence evaluator for fact-checking. Evaluate the following evidence snippet.

CLAIM: {claim}

EVIDENCE QUOTE: "{quote}"

ORIGINAL RELEVANCE EXPLANATION: {relevance_explanation or "No explanation provided"}

Please evaluate this evidence on the following criteria (0-10 scale):

1. RELEVANCE (0-10): How directly does this quote support or relate to the specific claim?
   - 9-10: Directly addresses the exact claim with specific information
   - 7-8: Clearly relevant but may not address all aspects
   - 5-6: Somewhat relevant but indirect
   - 0-4: Tangentially related or irrelevant

2. QUALITY (0-10): How strong, specific, and authoritative is this evidence?
   - 9-10: Highly specific, quantitative, or from authoritative source
   - 7-8: Good specificity with clear information
   - 5-6: General statement with some useful information
   - 0-4: Vague, ambiguous, or weak evidence

3. SPECIFICITY (0-10): How specific vs. general is this evidence?
   - 9-10: Contains specific facts, numbers, dates, or technical details
   - 7-8: Reasonably specific with clear statements
   - 5-6: Somewhat general but still informative
   - 0-4: Very general or vague

Provide your response in this exact format:
RELEVANCE_SCORE: [number]
QUALITY_SCORE: [number]
SPECIFICITY_SCORE: [number]
STRENGTH: [STRONG/MODERATE/WEAK]
IS_VALID: [YES/NO]
ASSESSMENT: [2-3 sentences explaining your evaluation]
REJECTION_REASON: [Only if IS_VALID is NO]
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
            
            # Parse structured response
            result = self._parse_critique_response(response)
            
            # Calculate overall score
            result["overall_score"] = (
                result["relevance_score"] * 0.5 +
                result["quality_score"] * 0.3 +
                result["specificity_score"] * 0.2
            )
            
            # Validate based on thresholds
            result["is_valid"] = (
                result.get("is_valid", True) and
                result["relevance_score"] >= self.relevance_threshold and
                result["quality_score"] >= self.quality_threshold and
                result["overall_score"] >= self.overall_threshold
            )
            
            if not result["is_valid"] and not result.get("rejection_reason"):
                reasons = []
                if result["relevance_score"] < self.relevance_threshold:
                    reasons.append(f"relevance ({result['relevance_score']:.1f} < {self.relevance_threshold})")
                if result["quality_score"] < self.quality_threshold:
                    reasons.append(f"quality ({result['quality_score']:.1f} < {self.quality_threshold})")
                if result["overall_score"] < self.overall_threshold:
                    reasons.append(f"overall score ({result['overall_score']:.1f} < {self.overall_threshold})")
                result["rejection_reason"] = f"Below thresholds: {', '.join(reasons)}"
            
            return result
            
        except Exception as e:
            logger.error(f"Error critiquing snippet: {e}")
            # Default to moderate acceptance on error
            return {
                "is_valid": True,
                "relevance_score": 7.0,
                "quality_score": 7.0,
                "specificity_score": 7.0,
                "overall_score": 7.0,
                "strength": "MODERATE",
                "assessment": "Error in critique process, defaulting to moderate acceptance",
                "rejection_reason": None
            }
    
    def _parse_critique_response(self, response: str) -> Dict[str, Any]:
        """Parse the structured response from the LLM."""
        # Default values in case parsing fails
        result = {
            "relevance_score": 7.0,
            "quality_score": 7.0,
            "specificity_score": 7.0,
            "strength": "MODERATE",
            "is_valid": True,
            "assessment": "",
            "rejection_reason": None
        }
        
        try:
            lines = response.strip().split('\n')
            current_key = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Check if this line contains a key:value pair
                if ':' in line and not current_key:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        key = parts[0].strip().upper()
                        value = parts[1].strip()
                        
                        if key == "RELEVANCE_SCORE":
                            try:
                                score = float(value.split()[0])  # Handle "8.5 - High relevance"
                                result["relevance_score"] = max(0.0, min(10.0, score))  # Clamp to 0-10
                            except (ValueError, IndexError):
                                logger.warning(f"Could not parse relevance score: {value}")
                        elif key == "QUALITY_SCORE":
                            try:
                                score = float(value.split()[0])
                                result["quality_score"] = max(0.0, min(10.0, score))
                            except (ValueError, IndexError):
                                logger.warning(f"Could not parse quality score: {value}")
                        elif key == "SPECIFICITY_SCORE":
                            try:
                                score = float(value.split()[0])
                                result["specificity_score"] = max(0.0, min(10.0, score))
                            except (ValueError, IndexError):
                                logger.warning(f"Could not parse specificity score: {value}")
                        elif key == "STRENGTH":
                            strength_val = value.upper().split()[0]  # Take first word
                            if strength_val in ["STRONG", "MODERATE", "WEAK"]:
                                result["strength"] = strength_val
                            else:
                                logger.warning(f"Invalid strength value: {value}, using MODERATE")
                        elif key == "IS_VALID":
                            result["is_valid"] = value.upper().startswith("YES")
                        elif key == "ASSESSMENT":
                            result["assessment"] = value
                            current_key = "assessment"
                        elif key == "REJECTION_REASON":
                            result["rejection_reason"] = value
                            current_key = "rejection_reason"
                elif current_key and line:
                    # Handle multi-line values
                    result[current_key] += " " + line
            
            # Validate scores are reasonable
            if result["relevance_score"] == 0 and result["quality_score"] == 0:
                logger.warning("All scores are 0, using default moderate scores")
                result["relevance_score"] = 5.0
                result["quality_score"] = 5.0
                result["specificity_score"] = 5.0
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing critique response: {e}")
            logger.debug(f"Response was: {response[:500]}...")
            return result