"""Output formatters for fact-checking results."""

from .base_formatter import BaseFormatter
from .consolidated_json_formatter import ConsolidatedJsonFormatter
from .markdown_formatter import MarkdownFormatter
from .evidence_utils import extract_all_evidence, extract_text_evidence, extract_image_evidence

__all__ = [
    "BaseFormatter",
    "ConsolidatedJsonFormatter",
    "MarkdownFormatter",
    "extract_all_evidence",
    "extract_text_evidence", 
    "extract_image_evidence",
]