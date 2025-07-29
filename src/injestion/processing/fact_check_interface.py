"""Fact check interface for document processing.

DEPRECATED: Use src.interfaces.readers.StandardDocumentReader instead.
This module is maintained for backward compatibility only.
"""

from typing import List, Tuple, Dict, Any
from src.interfaces import Document, Block, StandardDocumentReader


class FactCheckInterface(StandardDocumentReader):
    """Interface for fact-checking operations on documents.
    
    DEPRECATED: This class now inherits from StandardDocumentReader
    and is maintained only for backward compatibility.
    """
    pass  # All methods inherited from StandardDocumentReader