"""Base agent class for fact-checking pipeline"""

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, List

logger = logging.getLogger(__name__)


class AgentError(Exception):
    """Base exception for agent errors"""
    pass


class BaseAgent(ABC):
    """Base class for all fact-checking agents"""
    
    def __init__(
        self, 
        pdf_name: str, 
        cache_dir: Path = Path("data/scientific_cache"),
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize base agent.
        
        Args:
            pdf_name: Name of the PDF being processed
            cache_dir: Base cache directory
            config: Agent-specific configuration
        """
        self.pdf_name = pdf_name
        self.cache_dir = Path(cache_dir)
        self.config = config or {}
        
        # Set up directories
        self.pdf_dir = self.cache_dir / pdf_name
        self.agents_dir = self.pdf_dir / "agents"
        
        # Default agent directory (can be overridden by subclasses)
        self.agent_dir = self.agents_dir / self.agent_name
        self.agent_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize metadata
        self.metadata = {
            "agent_name": self.agent_name,
            "pdf_name": pdf_name,
            "started_at": None,
            "completed_at": None,
            "status": "not_started",
            "error": None,
            "config": self.config
        }
        
        logger.info(f"Initialized {self.agent_name} for {pdf_name}")
    
    @property
    @abstractmethod
    def agent_name(self) -> str:
        """Return the name of this agent"""
        pass
    
    @property
    @abstractmethod
    def required_inputs(self) -> List[str]:
        """List of required input files/directories relative to pdf_dir"""
        pass
    
    @abstractmethod
    async def process(self) -> Dict[str, Any]:
        """
        Main processing logic for the agent.
        
        Returns:
            Dictionary containing the agent's output data
        """
        pass
    
    def validate_inputs(self) -> bool:
        """
        Check if all required inputs exist.
        
        Returns:
            True if all inputs are available, False otherwise
        """
        missing = []
        for input_path in self.required_inputs:
            full_path = self.pdf_dir / input_path
            if not full_path.exists():
                missing.append(str(input_path))
        
        if missing:
            logger.error(f"{self.agent_name} missing inputs: {missing}")
            return False
        
        logger.info(f"{self.agent_name} inputs validated")
        return True
    
    async def run(self) -> Dict[str, Any]:
        """
        Run the agent with error handling and metadata tracking.
        
        Returns:
            Dictionary containing results and metadata
        """
        logger.info(f"Starting {self.agent_name}")
        
        # Update metadata
        self.metadata["started_at"] = datetime.now().isoformat()
        self.metadata["status"] = "running"
        self._save_metadata()
        
        try:
            # Validate inputs
            if not self.validate_inputs():
                raise AgentError(f"Input validation failed for {self.agent_name}")
            
            # Run processing
            result = await self.process()
            
            # Update metadata
            self.metadata["completed_at"] = datetime.now().isoformat()
            self.metadata["status"] = "completed"
            self._save_metadata()
            
            # Save outputs
            self.save_outputs(result)
            
            logger.info(f"Completed {self.agent_name}")
            return result
            
        except Exception as e:
            # Update metadata with error
            self.metadata["completed_at"] = datetime.now().isoformat()
            self.metadata["status"] = "failed"
            self.metadata["error"] = str(e)
            self._save_metadata()
            
            logger.error(f"{self.agent_name} failed: {e}")
            raise AgentError(f"{self.agent_name} processing failed: {e}") from e
    
    def save_outputs(self, data: Dict[str, Any]) -> None:
        """
        Save agent outputs to files.
        
        Args:
            data: Dictionary of output data to save
        """
        # Save main output
        output_file = self.agent_dir / "output.json"
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved {self.agent_name} outputs to {output_file}")
    
    def load_json(self, path: Path) -> Dict[str, Any]:
        """Load JSON file helper"""
        with open(path, 'r') as f:
            return json.load(f)
    
    def save_json(self, data: Dict[str, Any], filename: str) -> None:
        """Save JSON file helper"""
        output_path = self.agent_dir / filename
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _save_metadata(self) -> None:
        """Save agent metadata"""
        metadata_file = self.agent_dir / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)