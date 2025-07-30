"""Document aggregator for collecting and organizing multiple extracted documents."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


class ExtractedDocument:
    """Represents a single extracted document with its content and metadata."""
    
    def __init__(self, name: str, path: Path):
        self.name = name
        self.path = path
        self.content_json_path = path / "extracted" / "content.json"
        self.content = None
        self.metadata = {}
        self.blocks = []
        self.figures = []
        self._load_content()
    
    def _load_content(self):
        """Load the extracted content from JSON."""
        if not self.content_json_path.exists():
            logger.warning(f"No content.json found for {self.name}")
            return
        
        try:
            with open(self.content_json_path, 'r') as f:
                self.content = json.load(f)
                self.metadata = self.content.get('metadata', {})
                self.blocks = self.content.get('blocks', [])
                self._extract_figures()
        except Exception as e:
            logger.error(f"Failed to load content for {self.name}: {e}")
    
    def _extract_figures(self):
        """Extract all figures and tables from blocks."""
        for block in self.blocks:
            if block.get('role') in ['Figure', 'Table']:
                self.figures.append({
                    'id': block.get('id'),
                    'type': block.get('role'),
                    'text': block.get('text', ''),
                    'page': block.get('page_index', 0),
                    'image_path': block.get('image_path', ''),
                    'absolute_path': self.path / "extracted" / block.get('image_path', '') if block.get('image_path') else None
                })
    
    def get_text_content(self) -> str:
        """Get all text content in reading order."""
        text_blocks = []
        
        # Group blocks by page
        blocks_by_page = defaultdict(list)
        for block in self.blocks:
            page = block.get('page_index', 0)
            blocks_by_page[page].append(block)
        
        # Process in page order
        for page in sorted(blocks_by_page.keys()):
            page_blocks = blocks_by_page[page]
            # Use reading order if available
            if 'reading_order' in self.content and page < len(self.content['reading_order']):
                ordered_ids = self.content['reading_order'][page]
                blocks_dict = {b['id']: b for b in page_blocks}
                for block_id in ordered_ids:
                    if block_id in blocks_dict:
                        block = blocks_dict[block_id]
                        if block.get('text'):
                            text_blocks.append(block['text'])
            else:
                # No reading order found - this should not happen after normalization
                logger.warning(f"No reading order found for document {self.name} page {page}")
                # Use document order as fallback
                for block in page_blocks:
                    if block.get('text'):
                        text_blocks.append(block['text'])
        
        return '\n\n'.join(text_blocks)


class DocumentAggregator:
    """Aggregates multiple extracted documents for unified viewing."""
    
    def __init__(self, cache_dir: Path = Path("data/cache")):
        self.cache_dir = cache_dir
        self.documents: List[ExtractedDocument] = []
        self.scan_documents()
    
    def scan_documents(self) -> List[ExtractedDocument]:
        """Scan cache directory for all extracted documents."""
        self.documents = []
        
        if not self.cache_dir.exists():
            logger.warning(f"Cache directory {self.cache_dir} does not exist")
            return self.documents
        
        # Find all document directories with extracted content
        for doc_dir in self.cache_dir.iterdir():
            if doc_dir.is_dir():
                content_json = doc_dir / "extracted" / "content.json"
                if content_json.exists():
                    logger.info(f"Found extracted document: {doc_dir.name}")
                    doc = ExtractedDocument(doc_dir.name, doc_dir)
                    self.documents.append(doc)
        
        logger.info(f"Found {len(self.documents)} extracted documents")
        return self.documents
    
    def get_all_figures(self) -> List[Dict[str, Any]]:
        """Get all figures from all documents."""
        all_figures = []
        for doc in self.documents:
            for fig in doc.figures:
                fig_with_doc = fig.copy()
                fig_with_doc['document'] = doc.name
                all_figures.append(fig_with_doc)
        return all_figures
    
    def search_content(self, query: str, case_sensitive: bool = False) -> List[Dict[str, Any]]:
        """Search across all documents for matching content."""
        results = []
        
        if not case_sensitive:
            query = query.lower()
        
        for doc in self.documents:
            for block in doc.blocks:
                text = block.get('text', '')
                search_text = text if case_sensitive else text.lower()
                
                if query in search_text:
                    results.append({
                        'document': doc.name,
                        'page': block.get('page_index', 0),
                        'block_id': block.get('id'),
                        'role': block.get('role'),
                        'text': text,
                        'match_preview': self._get_match_preview(text, query, case_sensitive)
                    })
        
        return results
    
    def _get_match_preview(self, text: str, query: str, case_sensitive: bool = False) -> str:
        """Get a preview of text around the match."""
        search_text = text if case_sensitive else text.lower()
        search_query = query if case_sensitive else query.lower()
        
        idx = search_text.find(search_query)
        if idx == -1:
            return text[:100] + "..." if len(text) > 100 else text
        
        # Show 50 chars before and after
        start = max(0, idx - 50)
        end = min(len(text), idx + len(query) + 50)
        
        preview = text[start:end]
        if start > 0:
            preview = "..." + preview
        if end < len(text):
            preview = preview + "..."
        
        return preview
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about all documents."""
        stats = {
            'total_documents': len(self.documents),
            'total_pages': 0,
            'total_blocks': 0,
            'total_figures': 0,
            'total_tables': 0,
            'documents': []
        }
        
        for doc in self.documents:
            doc_stats = {
                'name': doc.name,
                'pages': doc.metadata.get('total_pages', 0),
                'blocks': len(doc.blocks),
                'figures': sum(1 for b in doc.blocks if b.get('role') == 'Figure'),
                'tables': sum(1 for b in doc.blocks if b.get('role') == 'Table'),
                'text_blocks': sum(1 for b in doc.blocks if b.get('role') in ['Text', 'Title', 'List'])
            }
            
            stats['total_pages'] += doc_stats['pages']
            stats['total_blocks'] += doc_stats['blocks']
            stats['total_figures'] += doc_stats['figures']
            stats['total_tables'] += doc_stats['tables']
            stats['documents'].append(doc_stats)
        
        return stats
    
    def export_combined_json(self, output_path: Path) -> Path:
        """Export all documents as a single JSON file."""
        combined = {
            'metadata': {
                'created_at': datetime.now().isoformat(),
                'source': 'DocumentAggregator',
                'total_documents': len(self.documents)
            },
            'documents': []
        }
        
        for doc in self.documents:
            if doc.content:
                combined['documents'].append({
                    'name': doc.name,
                    'path': str(doc.path),
                    'content': doc.content
                })
        
        with open(output_path, 'w') as f:
            json.dump(combined, f, indent=2)
        
        logger.info(f"Exported combined JSON to {output_path}")
        return output_path
