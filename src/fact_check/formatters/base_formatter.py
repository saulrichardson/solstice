"""Base formatter interface for output formatting."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any


class BaseFormatter(ABC):
    """Abstract base class for output formatters."""
    
    def __init__(self, output_dir: Path):
        """Initialize formatter with output directory."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    @abstractmethod
    def format(self, study_results: Dict[str, Any]) -> Dict[str, Any]:
        """Format study results into desired structure.
        
        Args:
            study_results: Raw study results from orchestrator
            
        Returns:
            Formatted results
        """
        pass
    
    @abstractmethod
    def save(self, formatted_results: Dict[str, Any], filename: str) -> Path:
        """Save formatted results to file.
        
        Args:
            formatted_results: Formatted results to save
            filename: Output filename
            
        Returns:
            Path to saved file
        """
        pass