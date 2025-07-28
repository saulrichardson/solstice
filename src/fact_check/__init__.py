"""Fact-checking package for evidence extraction from documents."""

from .evidence_extractor import EvidenceExtractor, EvidenceExtractionResult
from .pipeline import FactCheckPipeline
from .claim_orchestrator import ClaimOrchestrator

__all__ = [
    "EvidenceExtractor", 
    "EvidenceExtractionResult", 
    "FactCheckPipeline",
    "ClaimOrchestrator"
]