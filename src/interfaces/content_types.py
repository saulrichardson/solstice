"""Content type definitions."""

from enum import Enum


class ContentType(Enum):
    """Types of content that can be extracted."""
    TEXT = "text"
    FIGURE = "figure"
    TABLE = "table"
    ALL = "all"


class OutputFormat(Enum):
    """Output format options for content extraction."""
    TEXT_ONLY = "text_only"                    # Pure text, no placeholders
    TEXT_WITH_PLACEHOLDERS = "placeholders"     # Text with [FIGURE 1] markers
    STRUCTURED = "structured"                   # List of content items
    VISION_READY = "vision"                     # For vision LLMs


class BlockRole(Enum):
    """Standard block roles."""
    TEXT = "Text"
    TITLE = "Title"
    LIST = "List"
    FIGURE = "Figure"
    TABLE = "Table"