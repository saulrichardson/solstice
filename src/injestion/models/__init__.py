"""Data models for document ingestion."""

from .box import Box
from .document import Document, Block

__all__ = ["Box", "Document", "Block"]