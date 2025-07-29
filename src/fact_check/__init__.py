"""Fact-checking package for evidence extraction from documents."""

from .orchestrators import ClaimOrchestrator, StudyOrchestrator

__all__ = [
    "ClaimOrchestrator",
    "StudyOrchestrator"
]