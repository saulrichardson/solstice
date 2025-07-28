"""Utilities for working with PDF element catalogs."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

logger = logging.getLogger(__name__)


class CatalogReader:
    """Read and query PDF element catalogs."""
    
    def __init__(self, catalog_dir: Union[str, Path]):
        """Initialize catalog reader.
        
        Args:
            catalog_dir: Directory containing the catalog
        """
        self.catalog_dir = Path(catalog_dir)
        if not self.catalog_dir.exists():
            raise FileNotFoundError(f"Catalog directory not found: {catalog_dir}")
        
        # Load main catalog
        with open(self.catalog_dir / "catalog.json") as f:
            self.catalog = json.load(f)
        
        # Load element index
        with open(self.catalog_dir / "elements.json") as f:
            self.elements = json.load(f)
        
        # Load type index if available
        type_index_path = self.catalog_dir / "index_by_type.json"
        if type_index_path.exists():
            with open(type_index_path) as f:
                self.type_index = json.load(f)
        else:
            self.type_index = self._build_type_index()
    
    def _build_type_index(self) -> Dict[str, List[str]]:
        """Build index by element type."""
        index = {}
        for elem in self.elements:
            elem_type = elem.get('element_type', elem.get('type', 'unknown'))
            if elem_type not in index:
                index[elem_type] = []
            index[elem_type].append(elem['element_id'])
        return index
    
    def get_element(self, element_id: str) -> Optional[Dict[str, Any]]:
        """Get element by ID."""
        for elem in self.elements:
            if elem['element_id'] == element_id:
                return elem
        return None
    
    def get_elements_by_type(self, element_type: str) -> List[Dict[str, Any]]:
        """Get all elements of a specific type."""
        element_ids = self.type_index.get(element_type, [])
        return [self.get_element(eid) for eid in element_ids if self.get_element(eid)]
    
    def get_elements_by_page(self, page_num: int) -> List[Dict[str, Any]]:
        """Get all elements on a specific page."""
        return [elem for elem in self.elements if elem['page_num'] == page_num]
    
    def get_text_content(self, element_id: str) -> Optional[str]:
        """Get text content for an element."""
        # Try inline content first
        element = self.get_element(element_id)
        if element and element.get('content'):
            return element['content']
        
        # Try external text file
        text_file = self.catalog_dir / "text_content" / f"{element_id}.txt"
        if text_file.exists():
            with open(text_file, 'r', encoding='utf-8') as f:
                return f.read()
        
        return None
    
    def get_page_text(self, page_num: int) -> str:
        """Get all text content from a page in reading order."""
        elements = self.get_elements_by_page(page_num)
        # Sort by reading order
        elements.sort(key=lambda x: x.get('reading_order', 0))
        
        text_parts = []
        for elem in elements:
            content = self.get_text_content(elem['element_id'])
            if content:
                text_parts.append(content)
        
        return '\n\n'.join(text_parts)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get catalog statistics."""
        return self.catalog.get('statistics', {})
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get catalog metadata."""
        return self.catalog.get('metadata', {})


class CatalogExporter:
    """Export catalog data in various formats."""
    
    def __init__(self, catalog_reader: CatalogReader):
        """Initialize exporter with a catalog reader."""
        self.reader = catalog_reader
    
    def export_text(self, output_path: Union[str, Path], pages: Optional[List[int]] = None):
        """Export all text content to a single file.
        
        Args:
            output_path: Output file path
            pages: Specific pages to export (None = all)
        """
        output_path = Path(output_path)
        
        # Determine pages
        if pages is None:
            total_pages = self.reader.get_metadata().get('total_pages', 0)
            pages = list(range(1, total_pages + 1))
        
        # Collect text
        all_text = []
        for page_num in pages:
            page_text = self.reader.get_page_text(page_num)
            if page_text:
                all_text.append(f"--- Page {page_num} ---\n{page_text}")
        
        # Write output
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n\n'.join(all_text))
        
        logger.info(f"Exported text to: {output_path}")
    
    def export_elements_csv(self, output_path: Union[str, Path]):
        """Export element metadata to CSV.
        
        Args:
            output_path: Output CSV file path
        """
        import csv
        
        output_path = Path(output_path)
        
        # Define fields
        fields = [
            'element_id', 'page_num', 'element_type', 
            'reading_order', 'confidence', 'bbox_x1', 
            'bbox_y1', 'bbox_x2', 'bbox_y2', 'has_content'
        ]
        
        # Write CSV
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            
            for elem in self.reader.elements:
                bbox = elem.get('bbox', [0, 0, 0, 0])
                row = {
                    'element_id': elem['element_id'],
                    'page_num': elem['page_num'],
                    'element_type': elem.get('element_type', elem.get('type', '')),
                    'reading_order': elem.get('reading_order', 0),
                    'confidence': elem.get('confidence', 0),
                    'bbox_x1': bbox[0],
                    'bbox_y1': bbox[1],
                    'bbox_x2': bbox[2],
                    'bbox_y2': bbox[3],
                    'has_content': bool(elem.get('content') or self.reader.get_text_content(elem['element_id']))
                }
                writer.writerow(row)
        
        logger.info(f"Exported elements to CSV: {output_path}")


def load_catalog(catalog_dir: Union[str, Path]) -> CatalogReader:
    """Load a catalog for reading.
    
    Args:
        catalog_dir: Directory containing the catalog
        
    Returns:
        CatalogReader instance
    """
    return CatalogReader(catalog_dir)


def export_catalog_text(
    catalog_dir: Union[str, Path],
    output_path: Union[str, Path],
    pages: Optional[List[int]] = None
):
    """Export text from a catalog.
    
    Args:
        catalog_dir: Directory containing the catalog
        output_path: Output text file path
        pages: Specific pages to export (None = all)
    """
    reader = load_catalog(catalog_dir)
    exporter = CatalogExporter(reader)
    exporter.export_text(output_path, pages)