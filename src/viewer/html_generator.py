"""Generate unified HTML views of multiple extracted documents."""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import shutil
import base64

from .aggregator import DocumentAggregator, ExtractedDocument

logger = logging.getLogger(__name__)


class UnifiedHTMLGenerator:
    """Generates a unified HTML view of multiple extracted documents."""
    
    def __init__(self, aggregator: DocumentAggregator):
        self.aggregator = aggregator
        
    def generate_unified_site(self, output_dir: Path, include_images: bool = True) -> Path:
        """Generate a complete static HTML site with all documents.
        
        Args:
            output_dir: Directory to save the generated site
            include_images: Whether to include images in the output
            
        Returns:
            Path to the generated index.html
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (output_dir / "documents").mkdir(exist_ok=True)
        (output_dir / "assets").mkdir(exist_ok=True)
        (output_dir / "assets" / "figures").mkdir(exist_ok=True)
        
        # Generate main files
        self._generate_css(output_dir / "style.css")
        self._generate_javascript(output_dir / "search.js")
        self._generate_index(output_dir / "index.html")
        
        # Generate individual document pages
        for doc in self.aggregator.documents:
            self._generate_document_page(doc, output_dir / "documents" / f"{doc.name}.html", include_images)
            
            # Copy images if requested
            if include_images:
                self._copy_document_images(doc, output_dir / "assets" / "figures")
        
        # Generate search index
        self._generate_search_index(output_dir / "search-index.json")
        
        logger.info(f"Generated unified site at {output_dir}")
        return output_dir / "index.html"
    
    def generate_single_page_html(self, output_path: Path, include_images: bool = True) -> Path:
        """Generate a single HTML file with all documents.
        
        Args:
            output_path: Path to save the HTML file
            include_images: Whether to embed images as base64
            
        Returns:
            Path to the generated HTML file
        """
        html_parts = []
        
        # HTML header with embedded CSS
        html_parts.append(self._get_single_page_header())
        
        # Navigation
        html_parts.append(self._generate_navigation_html())
        
        # Main content
        html_parts.append('<div class="main-content">')
        
        # Table of contents
        html_parts.append(self._generate_toc_html())
        
        # All documents
        html_parts.append('<div class="documents-container">')
        
        for doc in self.aggregator.documents:
            html_parts.append(self._generate_document_section(doc, include_images, embed_base64=True))
        
        html_parts.append('</div>') # documents-container
        html_parts.append('</div>') # main-content
        
        # Footer
        html_parts.append(self._generate_footer_html())
        
        # Embedded JavaScript
        html_parts.append(self._get_embedded_javascript())
        
        # Close HTML
        html_parts.append('</body></html>')
        
        # Write file
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text('\n'.join(html_parts))
        
        logger.info(f"Generated single-page HTML at {output_path}")
        return output_path
    
    def _get_single_page_header(self) -> str:
        """Generate HTML header with embedded CSS for single page."""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Solstice Document Viewer</title>
    <style>
        ''' + self._get_css_content() + '''
    </style>
</head>
<body>'''
    
    def _get_css_content(self) -> str:
        """Get CSS content for styling."""
        return '''
        /* Global Styles */
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 0;
            background: #f5f5f5;
            color: #333;
        }
        
        /* Navigation */
        .navbar {
            background: #2c3e50;
            color: white;
            padding: 1rem 2rem;
            position: sticky;
            top: 0;
            z-index: 1000;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .navbar h1 {
            margin: 0;
            font-size: 1.5rem;
        }
        
        .navbar .stats {
            font-size: 0.9rem;
            opacity: 0.8;
            margin-top: 0.5rem;
        }
        
        /* Main Layout */
        .main-content {
            max-width: 1200px;
            margin: 2rem auto;
            padding: 0 2rem;
        }
        
        /* Table of Contents */
        .toc {
            background: white;
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        
        .toc h2 {
            margin-top: 0;
            color: #2c3e50;
        }
        
        .toc-list {
            list-style: none;
            padding: 0;
        }
        
        .toc-list li {
            padding: 0.5rem 0;
            border-bottom: 1px solid #eee;
        }
        
        .toc-list li:last-child {
            border-bottom: none;
        }
        
        .toc-list a {
            color: #3498db;
            text-decoration: none;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .toc-list a:hover {
            color: #2980b9;
        }
        
        .doc-meta {
            font-size: 0.85rem;
            color: #666;
        }
        
        /* Document Sections */
        .document-section {
            background: white;
            border-radius: 8px;
            padding: 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        
        .document-header {
            border-bottom: 2px solid #ecf0f1;
            padding-bottom: 1rem;
            margin-bottom: 2rem;
        }
        
        .document-header h2 {
            margin: 0 0 0.5rem 0;
            color: #2c3e50;
        }
        
        .document-stats {
            display: flex;
            gap: 2rem;
            font-size: 0.9rem;
            color: #666;
        }
        
        /* Page Sections */
        .page-section {
            margin-bottom: 3rem;
            padding-bottom: 2rem;
            border-bottom: 1px solid #ecf0f1;
        }
        
        .page-section:last-child {
            border-bottom: none;
        }
        
        .page-header {
            background: #ecf0f1;
            padding: 0.5rem 1rem;
            margin: -1rem -1rem 1rem -1rem;
            font-weight: 600;
            color: #34495e;
        }
        
        /* Content Blocks */
        .content-block {
            margin: 1rem 0;
        }
        
        .block-title {
            font-size: 1.2rem;
            font-weight: 600;
            margin: 1.5rem 0 0.5rem 0;
            color: #2c3e50;
        }
        
        .block-text {
            line-height: 1.6;
            margin: 0.5rem 0;
        }
        
        .block-list {
            margin: 0.5rem 0;
            padding-left: 1.5rem;
        }
        
        /* Figures and Tables */
        .figure-block, .table-block {
            margin: 2rem 0;
            text-align: center;
        }
        
        .figure-block img, .table-block img {
            max-width: 100%;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .figure-caption, .table-caption {
            margin-top: 0.5rem;
            font-style: italic;
            color: #666;
            font-size: 0.9rem;
        }
        
        /* Search */
        .search-box {
            margin: 2rem 0;
            position: relative;
        }
        
        .search-box input {
            width: 100%;
            padding: 0.75rem 1rem;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 1rem;
        }
        
        .search-results {
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: white;
            border: 1px solid #ddd;
            border-top: none;
            border-radius: 0 0 4px 4px;
            max-height: 400px;
            overflow-y: auto;
            display: none;
            z-index: 100;
        }
        
        .search-result {
            padding: 0.75rem 1rem;
            border-bottom: 1px solid #eee;
            cursor: pointer;
        }
        
        .search-result:hover {
            background: #f8f9fa;
        }
        
        .search-result-doc {
            font-weight: 600;
            color: #2c3e50;
            font-size: 0.85rem;
        }
        
        .search-result-preview {
            font-size: 0.9rem;
            color: #666;
            margin-top: 0.25rem;
        }
        
        /* Footer */
        .footer {
            background: #34495e;
            color: white;
            padding: 2rem;
            text-align: center;
            margin-top: 4rem;
        }
        
        .footer a {
            color: #3498db;
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .main-content {
                padding: 0 1rem;
            }
            
            .document-section {
                padding: 1rem;
            }
            
            .document-stats {
                flex-direction: column;
                gap: 0.5rem;
            }
        }
        
        /* Print Styles */
        @media print {
            .navbar, .toc, .search-box, .footer {
                display: none;
            }
            
            .document-section {
                page-break-inside: avoid;
                box-shadow: none;
                border: 1px solid #ddd;
            }
            
            .page-section {
                page-break-inside: avoid;
            }
        }
        '''
    
    def _generate_navigation_html(self) -> str:
        """Generate navigation HTML."""
        stats = self.aggregator.get_statistics()
        return f'''
        <nav class="navbar">
            <h1>Solstice Document Viewer</h1>
            <div class="stats">
                {stats['total_documents']} documents • 
                {stats['total_pages']} pages • 
                {stats['total_blocks']} blocks • 
                {stats['total_figures']} figures • 
                {stats['total_tables']} tables
            </div>
        </nav>
        '''
    
    def _generate_toc_html(self) -> str:
        """Generate table of contents HTML."""
        html = ['<div class="toc">']
        html.append('<h2>Documents</h2>')
        html.append('<ul class="toc-list">')
        
        for doc in self.aggregator.documents:
            doc_stats = {
                'pages': doc.metadata.get('total_pages', 0),
                'figures': sum(1 for b in doc.blocks if b.get('role') == 'Figure'),
                'tables': sum(1 for b in doc.blocks if b.get('role') == 'Table')
            }
            
            html.append(f'''
            <li>
                <a href="#doc-{doc.name}">
                    <span>{doc.name}</span>
                    <span class="doc-meta">
                        {doc_stats['pages']} pages, 
                        {doc_stats['figures']} figures, 
                        {doc_stats['tables']} tables
                    </span>
                </a>
            </li>
            ''')
        
        html.append('</ul>')
        html.append('</div>')
        
        return '\n'.join(html)
    
    def _generate_document_section(self, doc: ExtractedDocument, include_images: bool = True, embed_base64: bool = False) -> str:
        """Generate HTML for a single document section."""
        html = [f'<div class="document-section" id="doc-{doc.name}">']
        
        # Header
        doc_stats = {
            'pages': doc.metadata.get('total_pages', 0),
            'blocks': len(doc.blocks),
            'figures': sum(1 for b in doc.blocks if b.get('role') == 'Figure'),
            'tables': sum(1 for b in doc.blocks if b.get('role') == 'Table'),
            'text_blocks': sum(1 for b in doc.blocks if b.get('role') in ['Text', 'Title', 'List'])
        }
        
        html.append(f'''
        <div class="document-header">
            <h2>{doc.name}</h2>
            <div class="document-stats">
                <span>{doc_stats['pages']} pages</span>
                <span>{doc_stats['text_blocks']} text blocks</span>
                <span>{doc_stats['figures']} figures</span>
                <span>{doc_stats['tables']} tables</span>
            </div>
        </div>
        ''')
        
        # Content by page
        from collections import defaultdict
        blocks_by_page = defaultdict(list)
        for block in doc.blocks:
            page = block.get('page_index', 0)
            blocks_by_page[page].append(block)
        
        # Process each page
        for page in sorted(blocks_by_page.keys()):
            html.append(f'<div class="page-section">')
            html.append(f'<div class="page-header">Page {page + 1}</div>')
            
            # Get blocks in reading order
            page_blocks = blocks_by_page[page]
            if 'reading_order' in doc.content and page < len(doc.content['reading_order']):
                ordered_ids = doc.content['reading_order'][page]
                blocks_dict = {b['id']: b for b in page_blocks}
                ordered_blocks = [blocks_dict[bid] for bid in ordered_ids if bid in blocks_dict]
                
                # Verify all IDs were found (they should be after normalization)
                if len(ordered_blocks) != len(ordered_ids):
                    missing = set(ordered_ids) - set(bid for bid in ordered_ids if bid in blocks_dict)
                    logger.warning(f"Missing block IDs in {doc.name} page {page}: {missing}")
            else:
                # No reading order - shouldn't happen after normalization
                logger.warning(f"No reading order found for {doc.name} page {page}")
                ordered_blocks = page_blocks
            
            # Render each block
            for block in ordered_blocks:
                html.append(self._render_block(block, doc, include_images, embed_base64))
            
            html.append('</div>') # page-section
        
        html.append('</div>') # document-section
        
        return '\n'.join(html)
    
    def _render_block(self, block: Dict[str, Any], doc: ExtractedDocument, include_images: bool = True, embed_base64: bool = False) -> str:
        """Render a single content block as HTML."""
        role = block.get('role', '')
        text = block.get('text', '')
        
        if role == 'Title':
            return f'<h3 class="block-title">{text}</h3>'
        
        elif role == 'Text':
            # Preserve line breaks
            formatted_text = text.replace('\n', '<br>')
            return f'<div class="block-text">{formatted_text}</div>'
        
        elif role == 'List':
            return f'<div class="block-list">{text}</div>'
        
        elif role in ['Figure', 'Table']:
            html = [f'<div class="{role.lower()}-block">']
            
            if include_images and block.get('image_path'):
                if embed_base64:
                    # Embed as base64
                    img_path = doc.path / "extracted" / block['image_path']
                    if img_path.exists():
                        try:
                            with open(img_path, 'rb') as f:
                                img_data = base64.b64encode(f.read()).decode()
                            img_ext = img_path.suffix[1:]  # Remove dot
                            html.append(f'<img src="data:image/{img_ext};base64,{img_data}" alt="{text}">')
                        except Exception as e:
                            logger.error(f"Failed to embed image {img_path}: {e}")
                            html.append(f'<div class="{role.lower()}-caption">[Image not available]</div>')
                else:
                    # Link to image file
                    img_url = f"../assets/figures/{doc.name}_{Path(block['image_path']).name}"
                    html.append(f'<img src="{img_url}" alt="{text}">')
            
            if text:
                html.append(f'<div class="{role.lower()}-caption">{text}</div>')
            
            html.append('</div>')
            return '\n'.join(html)
        
        else:
            # Unknown block type
            return f'<div class="content-block">[{role}] {text}</div>'
    
    def _generate_footer_html(self) -> str:
        """Generate footer HTML."""
        return f'''
        <footer class="footer">
            <p>Generated by Solstice Document Viewer on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><a href="https://github.com/solstice-ai/solstice">Solstice on GitHub</a></p>
        </footer>
        '''
    
    def _get_embedded_javascript(self) -> str:
        """Get embedded JavaScript for interactivity."""
        return '''
        <script>
        // Simple search functionality
        document.addEventListener('DOMContentLoaded', function() {
            // Smooth scrolling for TOC links
            document.querySelectorAll('.toc-list a').forEach(link => {
                link.addEventListener('click', function(e) {
                    e.preventDefault();
                    const targetId = this.getAttribute('href').substring(1);
                    const targetElement = document.getElementById(targetId);
                    if (targetElement) {
                        targetElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }
                });
            });
            
            // Print functionality
            window.addEventListener('keydown', function(e) {
                if (e.ctrlKey && e.key === 'p') {
                    window.print();
                }
            });
        });
        </script>
        '''
    
    def _generate_css(self, output_path: Path):
        """Generate CSS file."""
        output_path.write_text(self._get_css_content())
    
    def _generate_javascript(self, output_path: Path):
        """Generate JavaScript file for search functionality."""
        js_content = '''
        // Document search functionality
        class DocumentSearch {
            constructor() {
                this.searchIndex = null;
                this.loadSearchIndex();
                this.setupEventListeners();
            }
            
            async loadSearchIndex() {
                try {
                    const response = await fetch('../search-index.json');
                    this.searchIndex = await response.json();
                } catch (error) {
                    console.error('Failed to load search index:', error);
                }
            }
            
            setupEventListeners() {
                const searchInput = document.getElementById('search-input');
                if (searchInput) {
                    searchInput.addEventListener('input', (e) => this.handleSearch(e.target.value));
                }
            }
            
            handleSearch(query) {
                if (!query || query.length < 2) {
                    this.hideResults();
                    return;
                }
                
                const results = this.search(query);
                this.displayResults(results);
            }
            
            search(query) {
                if (!this.searchIndex) return [];
                
                const lowerQuery = query.toLowerCase();
                const results = [];
                
                for (const item of this.searchIndex) {
                    if (item.text.toLowerCase().includes(lowerQuery)) {
                        results.push({
                            ...item,
                            preview: this.getPreview(item.text, query)
                        });
                    }
                }
                
                return results.slice(0, 20); // Limit to 20 results
            }
            
            getPreview(text, query) {
                const index = text.toLowerCase().indexOf(query.toLowerCase());
                if (index === -1) return text.substring(0, 100) + '...';
                
                const start = Math.max(0, index - 50);
                const end = Math.min(text.length, index + query.length + 50);
                
                let preview = text.substring(start, end);
                if (start > 0) preview = '...' + preview;
                if (end < text.length) preview = preview + '...';
                
                // Highlight the match
                const regex = new RegExp(query, 'gi');
                preview = preview.replace(regex, '<strong>$&</strong>');
                
                return preview;
            }
            
            displayResults(results) {
                const resultsContainer = document.getElementById('search-results');
                if (!resultsContainer) return;
                
                if (results.length === 0) {
                    resultsContainer.innerHTML = '<div class="search-result">No results found</div>';
                } else {
                    resultsContainer.innerHTML = results.map(result => `
                        <div class="search-result" onclick="navigateToResult('${result.document}', '${result.block_id}')">
                            <div class="search-result-doc">${result.document} - Page ${result.page + 1}</div>
                            <div class="search-result-preview">${result.preview}</div>
                        </div>
                    `).join('');
                }
                
                resultsContainer.style.display = 'block';
            }
            
            hideResults() {
                const resultsContainer = document.getElementById('search-results');
                if (resultsContainer) {
                    resultsContainer.style.display = 'none';
                }
            }
        }
        
        // Navigation function
        function navigateToResult(document, blockId) {
            window.location.href = `documents/${document}.html#block-${blockId}`;
        }
        
        // Initialize search on page load
        document.addEventListener('DOMContentLoaded', () => {
            new DocumentSearch();
        });
        '''
        
        output_path.write_text(js_content)
    
    def _generate_index(self, output_path: Path):
        """Generate index.html."""
        stats = self.aggregator.get_statistics()
        
        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Solstice Document Viewer</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <nav class="navbar">
        <h1>Solstice Document Viewer</h1>
        <div class="stats">
            {stats['total_documents']} documents • 
            {stats['total_pages']} pages • 
            {stats['total_blocks']} blocks
        </div>
    </nav>
    
    <div class="main-content">
        <div class="search-box">
            <input type="text" id="search-input" placeholder="Search across all documents...">
            <div id="search-results" class="search-results"></div>
        </div>
        
        <div class="toc">
            <h2>Available Documents</h2>
            <ul class="toc-list">
'''
        
        for doc_stat in stats['documents']:
            html += f'''
                <li>
                    <a href="documents/{doc_stat['name']}.html">
                        <span>{doc_stat['name']}</span>
                        <span class="doc-meta">
                            {doc_stat['pages']} pages, 
                            {doc_stat['figures']} figures, 
                            {doc_stat['tables']} tables
                        </span>
                    </a>
                </li>
            '''
        
        html += '''
            </ul>
        </div>
        
        <div class="document-section">
            <h2>Summary Statistics</h2>
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="background: #ecf0f1;">
                        <th style="padding: 0.5rem; text-align: left;">Document</th>
                        <th style="padding: 0.5rem; text-align: center;">Pages</th>
                        <th style="padding: 0.5rem; text-align: center;">Text Blocks</th>
                        <th style="padding: 0.5rem; text-align: center;">Figures</th>
                        <th style="padding: 0.5rem; text-align: center;">Tables</th>
                    </tr>
                </thead>
                <tbody>
'''
        
        for doc_stat in stats['documents']:
            html += f'''
                <tr>
                    <td style="padding: 0.5rem;">{doc_stat['name']}</td>
                    <td style="padding: 0.5rem; text-align: center;">{doc_stat['pages']}</td>
                    <td style="padding: 0.5rem; text-align: center;">{doc_stat['text_blocks']}</td>
                    <td style="padding: 0.5rem; text-align: center;">{doc_stat['figures']}</td>
                    <td style="padding: 0.5rem; text-align: center;">{doc_stat['tables']}</td>
                </tr>
            '''
        
        html += f'''
                </tbody>
                <tfoot>
                    <tr style="background: #ecf0f1; font-weight: bold;">
                        <td style="padding: 0.5rem;">Total</td>
                        <td style="padding: 0.5rem; text-align: center;">{stats['total_pages']}</td>
                        <td style="padding: 0.5rem; text-align: center;">{stats['total_blocks']}</td>
                        <td style="padding: 0.5rem; text-align: center;">{stats['total_figures']}</td>
                        <td style="padding: 0.5rem; text-align: center;">{stats['total_tables']}</td>
                    </tr>
                </tfoot>
            </table>
        </div>
    </div>
    
    <footer class="footer">
        <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </footer>
    
    <script src="search.js"></script>
</body>
</html>
'''
        
        output_path.write_text(html)
    
    def _generate_document_page(self, doc: ExtractedDocument, output_path: Path, include_images: bool = True):
        """Generate individual document page."""
        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{doc.name} - Solstice Document Viewer</title>
    <link rel="stylesheet" href="../style.css">
</head>
<body>
    <nav class="navbar">
        <h1><a href="../index.html" style="color: white; text-decoration: none;">Solstice Document Viewer</a> / {doc.name}</h1>
    </nav>
    
    <div class="main-content">
        {self._generate_document_section(doc, include_images, embed_base64=False)}
    </div>
    
    <footer class="footer">
        <p><a href="../index.html">Back to Document List</a></p>
    </footer>
</body>
</html>
'''
        
        output_path.write_text(html)
    
    def _copy_document_images(self, doc: ExtractedDocument, output_dir: Path):
        """Copy document images to output directory."""
        for fig in doc.figures:
            if fig['absolute_path'] and fig['absolute_path'].exists():
                dest_name = f"{doc.name}_{fig['absolute_path'].name}"
                dest_path = output_dir / dest_name
                try:
                    shutil.copy2(fig['absolute_path'], dest_path)
                except Exception as e:
                    logger.error(f"Failed to copy image {fig['absolute_path']}: {e}")
    
    def _generate_search_index(self, output_path: Path):
        """Generate search index for JavaScript search."""
        search_index = []
        
        for doc in self.aggregator.documents:
            for block in doc.blocks:
                if block.get('text'):
                    search_index.append({
                        'document': doc.name,
                        'page': block.get('page_index', 0),
                        'block_id': block.get('id', ''),
                        'role': block.get('role', ''),
                        'text': block.get('text', '')
                    })
        
        with open(output_path, 'w') as f:
            json.dump(search_index, f)
