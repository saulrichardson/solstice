"""Fact-checking pipeline orchestrator"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Type

from .agents.base import BaseAgent, AgentError
from .agents.claim_verifier import ClaimVerifierAgent

logger = logging.getLogger(__name__)


class PipelineError(Exception):
    """Pipeline execution error"""
    pass


class FactCheckPipeline:
    """Orchestrates the fact-checking agent pipeline"""
    
    def __init__(
        self,
        pdf_name: str,
        cache_dir: Path = Path("data/cache"),
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the fact-checking pipeline.
        
        Args:
            pdf_name: Name of the PDF to process
            cache_dir: Base cache directory
            config: Pipeline configuration including agent configs
        """
        self.pdf_name = pdf_name
        self.cache_dir = Path(cache_dir)
        self.pdf_dir = self.cache_dir / pdf_name
        self.agents_dir = self.pdf_dir / "agents"
        self.config = config or {}
        
        # Ensure agents directory exists
        self.agents_dir.mkdir(parents=True, exist_ok=True)
        
        # Pipeline state
        self.agents: List[BaseAgent] = []
        self.results: Dict[str, Any] = {}
        self.manifest = {
            "pdf_name": pdf_name,
            "pipeline_started_at": None,
            "pipeline_completed_at": None,
            "pipeline_status": "not_started",
            "agents": {},
            "config": self.config
        }
        
        # Initialize agents
        self._initialize_agents()
    
    def _initialize_agents(self) -> None:
        """Initialize agents based on configuration"""
        # Get agent configurations
        agent_configs = self.config.get("agents", {})
        
        # For now, we'll use a simple sequential pipeline
        # In the future, this could be configured via DAG
        
        # Check if we have claims to verify directly
        standalone_claims = self.config.get("claims", [])
        
        if standalone_claims:
            # Direct claim verification mode
            verifier_config = agent_configs.get("claim_verifier", {})
            verifier_config["standalone_claims"] = standalone_claims
            
            self.agents.append(
                ClaimVerifierAgent(
                    self.pdf_name,
                    self.cache_dir,
                    verifier_config
                )
            )
        else:
            # Full pipeline mode (will add more agents here)
            # For now, just the verifier with empty claims
            verifier_config = agent_configs.get("claim_verifier", {})
            
            self.agents.append(
                ClaimVerifierAgent(
                    self.pdf_name,
                    self.cache_dir,
                    verifier_config
                )
            )
        
        logger.info(f"Initialized pipeline with {len(self.agents)} agents")
    
    async def run(self) -> Dict[str, Any]:
        """
        Run the fact-checking pipeline.
        
        Returns:
            Dictionary containing all agent results and pipeline metadata
        """
        logger.info(f"Starting fact-check pipeline for {self.pdf_name}")
        
        # Update manifest
        self.manifest["pipeline_started_at"] = datetime.now().isoformat()
        self.manifest["pipeline_status"] = "running"
        self._save_manifest()
        
        try:
            # Run agents sequentially
            for agent in self.agents:
                agent_name = agent.agent_name
                logger.info(f"Running agent: {agent_name}")
                
                # Update manifest
                self.manifest["agents"][agent_name] = {
                    "status": "running",
                    "started_at": datetime.now().isoformat()
                }
                self._save_manifest()
                
                try:
                    # Run the agent
                    result = await agent.run()
                    self.results[agent_name] = result
                    
                    # Update manifest
                    self.manifest["agents"][agent_name].update({
                        "status": "completed",
                        "completed_at": datetime.now().isoformat()
                    })
                    self._save_manifest()
                    
                except Exception as e:
                    # Update manifest with error
                    self.manifest["agents"][agent_name].update({
                        "status": "failed",
                        "completed_at": datetime.now().isoformat(),
                        "error": str(e)
                    })
                    self._save_manifest()
                    
                    # Decide whether to continue or fail
                    if self.config.get("continue_on_error", False):
                        logger.error(f"Agent {agent_name} failed, continuing: {e}")
                        self.results[agent_name] = {"error": str(e)}
                    else:
                        raise PipelineError(f"Agent {agent_name} failed: {e}") from e
            
            # Pipeline completed
            self.manifest["pipeline_completed_at"] = datetime.now().isoformat()
            self.manifest["pipeline_status"] = "completed"
            self._save_manifest()
            
            # Save final results
            self._save_final_results()
            
            logger.info("Pipeline completed successfully")
            return self.results
            
        except Exception as e:
            # Pipeline failed
            self.manifest["pipeline_completed_at"] = datetime.now().isoformat()
            self.manifest["pipeline_status"] = "failed"
            self.manifest["pipeline_error"] = str(e)
            self._save_manifest()
            
            logger.error(f"Pipeline failed: {e}")
            raise PipelineError(f"Pipeline execution failed: {e}") from e
    
    def _save_manifest(self) -> None:
        """Save pipeline manifest"""
        manifest_file = self.agents_dir / "pipeline_manifest.json"
        with open(manifest_file, 'w') as f:
            json.dump(self.manifest, f, indent=2)
    
    def _save_final_results(self) -> None:
        """Save consolidated pipeline results"""
        results_file = self.agents_dir / "pipeline_results.json"
        
        # Prepare summary
        summary = {
            "pdf_name": self.pdf_name,
            "pipeline_started_at": self.manifest["pipeline_started_at"],
            "pipeline_completed_at": self.manifest["pipeline_completed_at"],
            "agents_run": len(self.agents),
            "agents_succeeded": sum(
                1 for a in self.manifest["agents"].values() 
                if a["status"] == "completed"
            ),
            "results": self.results
        }
        
        with open(results_file, 'w') as f:
            json.dump(summary, f, indent=2)
    
    @classmethod
    def from_config_file(cls, pdf_name: str, config_file: Path) -> "FactCheckPipeline":
        """Create pipeline from configuration file"""
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        return cls(pdf_name, config=config)
    
    def get_agent_status(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific agent"""
        return self.manifest["agents"].get(agent_name)
    
    def get_pipeline_status(self) -> str:
        """Get overall pipeline status"""
        return self.manifest["pipeline_status"]