"""Fact-checking package for evidence extraction from documents."""

from .evidence_extractor import EvidenceExtractor, EvidenceExtractionResult
from .orchestrators import ClaimOrchestrator, StudyOrchestrator

__all__ = [
    "EvidenceExtractor", 
    "EvidenceExtractionResult", 
    "ClaimOrchestrator",
    "StudyOrchestrator"
]