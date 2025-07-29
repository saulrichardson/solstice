"""Backward compatibility shim for document models.

This module maintains backward compatibility by re-exporting
the models from the new interfaces package.
"""

from src.interfaces import Block, Document

__all__ = ["Block", "Document"]