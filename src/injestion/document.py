"""Lightweight pydantic models representing the fully processed document."""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from pydantic import BaseModel, Field


class Block(BaseModel):
    id: str
    page_index: int
    role: str
    bbox: Tuple[float, float, float, float]
    text: str | None = None
    html: str | None = None  # tables
    image_path: str | None = None  # figures
    metadata: dict = Field(default_factory=dict)  # Additional metadata like score, dpi


class Document(BaseModel):
    source_pdf: str = Field(..., description="Original PDF path or URI")
    blocks: List[Block]
    metadata: dict = {}
    reading_order: List[List[str]] = Field(default_factory=list, description="Reading order per page")

    def save(self, path: str | Path) -> None:
        # Handle both Pydantic v1 and v2
        try:
            # Pydantic v2
            json_str = self.model_dump_json(indent=2)
        except AttributeError:
            # Pydantic v1
            json_str = self.json(indent=2, ensure_ascii=False)
        Path(path).write_text(json_str)

    @classmethod
    def load(cls, path: str | Path) -> "Document":
        return cls.model_validate_json(Path(path).read_text())

