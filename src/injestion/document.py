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
        Path(path).write_text(self.model_dump_json(indent=2, ensure_ascii=False))

    @classmethod
    def load(cls, path: str | Path) -> "Document":
        return cls.model_validate_json(Path(path).read_text())

