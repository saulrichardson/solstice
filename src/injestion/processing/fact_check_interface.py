"""Interface between document extraction and fact-checking.

This module provides methods to prepare extracted documents for fact-checking,
handling both text and image content appropriately.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
import base64

from ..models.document import Document, Block


class FactCheckInterface:
    """Prepare extracted documents for fact-checking."""
    
    def __init__(self, document: Document):
        """Initialize with an extracted document."""
        self.document = document
        self._blocks_by_page = self._organize_blocks_by_page()
    
    def _organize_blocks_by_page(self) -> Dict[int, Dict[str, Block]]:
        """Organize blocks by page for efficient access."""
        blocks_by_page = {}
        for block in self.document.blocks:
            if block.page_index not in blocks_by_page:
                blocks_by_page[block.page_index] = {}
            blocks_by_page[block.page_index][block.id] = block
        return blocks_by_page
    
    def get_full_text(self, include_figure_descriptions: bool = True) -> str:
        """Get the full document text in reading order.
        
        Args:
            include_figure_descriptions: Whether to include figure/table placeholder text
            
        Returns:
            Complete document text as a single string
        """
        text_parts = []
        
        # Process each page in order
        for page_idx in range(len(self.document.reading_order)):
            # Add page separator for context
            if page_idx > 0:
                text_parts.append(f"\n\n[Page {page_idx + 1}]\n")
            
            # Get reading order for this page
            page_order = self.document.reading_order[page_idx]
            page_blocks = self._blocks_by_page.get(page_idx, {})
            
            # Process blocks in reading order
            for block_id in page_order:
                if block_id not in page_blocks:
                    continue
                
                block = page_blocks[block_id]
                
                # Handle different block types
                if block.role in ['Text', 'Title', 'List']:
                    if block.text:
                        text_parts.append(block.text)
                
                elif include_figure_descriptions and block.role in ['Figure', 'Table']:
                    # Add placeholder for visual content
                    if block.text:
                        text_parts.append(f"[{block.role}: {block.text}]")
                    else:
                        text_parts.append(f"[{block.role} on page {page_idx + 1}]")
        
        return '\n\n'.join(text_parts)
    
    def get_text_with_locations(self) -> List[Tuple[str, Dict]]:
        """Get document text with location metadata for each block.
        
        Returns:
            List of (text, metadata) tuples where metadata includes:
            - block_id: str
            - page_index: int
            - role: str
            - bbox: Tuple[float, float, float, float]
        """
        text_with_locations = []
        
        for page_idx in range(len(self.document.reading_order)):
            page_order = self.document.reading_order[page_idx]
            page_blocks = self._blocks_by_page.get(page_idx, {})
            
            for block_id in page_order:
                if block_id not in page_blocks:
                    continue
                
                block = page_blocks[block_id]
                
                if block.text:
                    metadata = {
                        'block_id': block.id,
                        'page_index': block.page_index,
                        'role': block.role,
                        'bbox': block.bbox
                    }
                    text_with_locations.append((block.text, metadata))
        
        return text_with_locations
    
    def get_figures_and_tables(self, include_images: bool = False) -> List[Dict]:
        """Get all figures and tables with their metadata.
        
        Args:
            include_images: If True, includes base64 encoded images in the response
        
        Returns:
            List of dicts with:
            - block_id: str
            - page_index: int
            - role: str ('Figure' or 'Table')
            - description: str (placeholder text)
            - image_path: Optional[str]
            - bbox: Tuple[float, float, float, float]
            - image_base64: Optional[str] (if include_images=True and image exists)
        """
        visual_elements = []
        
        for block in self.document.blocks:
            if block.role in ['Figure', 'Table']:
                element = {
                    'block_id': block.id,
                    'page_index': block.page_index,
                    'role': block.role,
                    'description': block.text or f"{block.role} on page {block.page_index + 1}",
                    'image_path': block.image_path,
                    'bbox': block.bbox
                }
                
                # Include base64 encoded image if requested
                if include_images and block.image_path:
                    # Construct full path - assume relative to cache directory
                    from pathlib import Path
                    cache_dir = Path(self.document.source_pdf).parent.parent / "cache"
                    doc_id = Path(self.document.source_pdf).stem
                    full_path = cache_dir / doc_id / "extracted" / block.image_path
                    
                    encoded = self.encode_image_for_llm(str(full_path))
                    if encoded:
                        element['image_base64'] = encoded
                
                visual_elements.append(element)
        
        return visual_elements
    
    def get_page_text(self, page_index: int, include_figures: bool = True) -> str:
        """Get text for a specific page.
        
        Args:
            page_index: 0-based page index
            include_figures: Whether to include figure/table descriptions
            
        Returns:
            Text content of the specified page
        """
        if page_index >= len(self.document.reading_order):
            return ""
        
        text_parts = []
        page_order = self.document.reading_order[page_index]
        page_blocks = self._blocks_by_page.get(page_index, {})
        
        for block_id in page_order:
            if block_id not in page_blocks:
                continue
            
            block = page_blocks[block_id]
            
            if block.role in ['Text', 'Title', 'List'] and block.text:
                text_parts.append(block.text)
            elif include_figures and block.role in ['Figure', 'Table'] and block.text:
                text_parts.append(f"[{block.role}: {block.text}]")
        
        return '\n\n'.join(text_parts)
    
    def find_text_location(self, text_snippet: str) -> Optional[Dict]:
        """Find the location of a text snippet in the document.
        
        Args:
            text_snippet: Text to search for
            
        Returns:
            Dict with location info or None if not found:
            - block_id: str
            - page_index: int
            - char_start: int (within block)
            - char_end: int (within block)
            - bbox: Tuple[float, float, float, float]
        """
        for block in self.document.blocks:
            if block.text and text_snippet in block.text:
                start = block.text.find(text_snippet)
                return {
                    'block_id': block.id,
                    'page_index': block.page_index,
                    'char_start': start,
                    'char_end': start + len(text_snippet),
                    'bbox': block.bbox
                }
        return None
    
    def encode_image_for_llm(self, image_path: str) -> Optional[str]:
        """Encode an image file as base64 for LLM consumption.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Base64 encoded string or None if file not found
        """
        path = Path(image_path)
        if not path.exists():
            return None
        
        with open(path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    
    def get_all_images(self) -> List[Dict]:
        """Get all figure and table images from the document.
        
        Returns:
            List of dicts with:
            - block_id: str
            - page_index: int
            - role: str ('Figure' or 'Table')
            - description: str
            - image_path: str (full path to image file)
            - image_exists: bool
        """
        images = []
        
        for block in self.document.blocks:
            if block.role in ['Figure', 'Table'] and block.image_path:
                # Construct full path
                from pathlib import Path
                cache_dir = Path(self.document.source_pdf).parent.parent / "cache"
                doc_id = Path(self.document.source_pdf).stem
                full_path = cache_dir / doc_id / "extracted" / block.image_path
                
                images.append({
                    'block_id': block.id,
                    'page_index': block.page_index,
                    'role': block.role,
                    'description': block.text or f"{block.role} on page {block.page_index + 1}",
                    'image_path': str(full_path),
                    'image_exists': full_path.exists()
                })
        
        return images
    
    def get_image_by_id(self, block_id: str) -> Optional[Dict]:
        """Get a specific image by block ID.
        
        Args:
            block_id: The block ID of the figure/table
            
        Returns:
            Dict with image info and base64 data, or None if not found:
            - block_id: str
            - page_index: int
            - role: str
            - description: str
            - image_base64: str
        """
        for block in self.document.blocks:
            if block.id == block_id and block.role in ['Figure', 'Table'] and block.image_path:
                from pathlib import Path
                cache_dir = Path(self.document.source_pdf).parent.parent / "cache"
                doc_id = Path(self.document.source_pdf).stem
                full_path = cache_dir / doc_id / "extracted" / block.image_path
                
                encoded = self.encode_image_for_llm(str(full_path))
                if encoded:
                    return {
                        'block_id': block.id,
                        'page_index': block.page_index,
                        'role': block.role,
                        'description': block.text or f"{block.role} on page {block.page_index + 1}",
                        'image_base64': encoded
                    }
        
        return None


def prepare_for_fact_checking(
    document: Document,
    include_visual_descriptions: bool = True
) -> Dict:
    """Prepare a document for fact-checking.
    
    Args:
        document: Extracted document
        include_visual_descriptions: Whether to include figure/table descriptions
        
    Returns:
        Dict with:
        - full_text: str (complete document text)
        - visual_elements: List[Dict] (figures and tables metadata)
        - page_count: int
        - source_pdf: str
    """
    interface = FactCheckInterface(document)
    
    return {
        'full_text': interface.get_full_text(include_visual_descriptions),
        'visual_elements': interface.get_figures_and_tables(),
        'page_count': len(document.reading_order),
        'source_pdf': document.source_pdf
    }