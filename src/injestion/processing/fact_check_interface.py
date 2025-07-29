"""Fact check interface for document processing."""

from typing import List, Tuple, Dict, Any
from ..models.document import Document, Block


class FactCheckInterface:
    """Interface for fact-checking operations on documents."""
    
    def __init__(self, document: Document):
        self.document = document
    
    def get_full_text(self, *, include_figure_descriptions: bool = True, normalize: bool = True) -> str:
        """Get full document text with optional figure descriptions."""
        texts = []
        current_page = -1
        
        for page_idx, block_ids in enumerate(self.document.reading_order):
            # Add page separator
            if page_idx > current_page and current_page >= 0:
                texts.append(f"\n\n[Page {page_idx + 1}]\n")
            current_page = page_idx
            
            for block_id in block_ids:
                # Find block by ID
                block = next((b for b in self.document.blocks if b.id == block_id), None)
                if not block:
                    continue
                
                # Add text based on block type
                if block.text:
                    text = block.text
                    if normalize:
                        # Basic normalization
                        text = text.strip()
                    texts.append(text)
                    texts.append("\n\n")  # Add separator
                elif include_figure_descriptions and block.role == "figure" and block.metadata.get("description"):
                    texts.append(f"[Figure: {block.metadata['description']}]\n\n")
        
        return "".join(texts).strip()
    
    def get_text_with_locations(self, *, normalize: bool = True) -> List[Tuple[str, Dict[str, Any]]]:
        """Get text blocks with their location metadata."""
        results = []
        
        for page_idx, block_ids in enumerate(self.document.reading_order):
            for block_id in block_ids:
                # Find block by ID
                block = next((b for b in self.document.blocks if b.id == block_id), None)
                if not block or not block.text:
                    continue
                
                text = block.text
                if normalize:
                    text = text.strip()
                
                metadata = {
                    "page_index": page_idx,
                    "block_id": block.id,
                    "bbox": block.bbox,
                    "role": block.role
                }
                
                results.append((text, metadata))
        
        return results