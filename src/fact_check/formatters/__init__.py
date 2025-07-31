"""Output formatters for fact-checking results."""

from .base_formatter import BaseFormatter
from .consolidated_json_formatter import ConsolidatedJsonFormatter
from .markdown_formatter import MarkdownFormatter

__all__ = [
    "BaseFormatter",
    "ConsolidatedJsonFormatter",
    "MarkdownFormatter",
]