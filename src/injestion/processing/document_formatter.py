"""Generate human-readable versions of extracted documents."""

from pathlib import Path
from typing import Dict, List, Optional

from ..models.document import Document, Block


def generate_readable_document(
    document: Document,
    output_path: Path,
    include_images: bool = True,
    image_max_width: int = 600
) -> Path:
    """Generate a human-readable markdown document from extracted content.
    
    Args:
        document: Document with extracted content
        output_path: Path to save the readable document
        include_images: Whether to embed actual images or just show placeholders
        image_max_width: Maximum width for embedded images in pixels
        
    Returns:
        Path to the generated document
    """
    lines = []
    
    # Add document header
    lines.append("# Extracted Document\n")
    lines.append(f"**Source:** {document.source_pdf}\n")
    lines.append(f"**Pages:** {document.metadata.get('total_pages', 'Unknown')}\n")
    lines.append("---\n")
    
    # Process each page in reading order
    for page_idx in range(document.metadata.get('total_pages', 0)):
        lines.append(f"\n## Page {page_idx + 1}\n")
        
        # Get blocks for this page
        blocks_by_id = {b.id: b for b in document.blocks if b.page_index == page_idx}
        
        # Get reading order for this page
        if hasattr(document, 'reading_order') and page_idx < len(document.reading_order):
            reading_order = document.reading_order[page_idx]
        else:
            # Fallback: use all blocks for this page
            reading_order = list(blocks_by_id.keys())
        
        # Process blocks in reading order
        for block_id in reading_order:
            if block_id not in blocks_by_id:
                continue
                
            block = blocks_by_id[block_id]
            
            # Format based on block type
            if block.role == 'Title':
                # Make titles stand out
                lines.append(f"\n### {block.text}\n")
            
            elif block.role in ['Figure', 'Table']:
                # Handle figures and tables
                lines.append(f"\n**[{block.role.upper()}]**\n")
                
                if include_images and block.image_path:
                    # Get the full path to the image
                    # Assuming image_path is relative to the extracted folder
                    img_path = output_path.parent / block.image_path
                    
                    if img_path.exists():
                        # Embed image with markdown
                        lines.append(f"![{block.role} from page {page_idx + 1}]({block.image_path})\n")
                    else:
                        # Fallback if image not found
                        lines.append(f"*{block.text}*\n")
                else:
                    # Just show placeholder text
                    lines.append(f"*{block.text}*\n")
            
            elif block.role in ['Text', 'List']:
                # Regular text content
                if block.text:
                    lines.append(f"{block.text}\n")
            
            else:
                # Unknown block type
                if block.text:
                    lines.append(f"[{block.role}] {block.text}\n")
    
    # Add extraction metadata
    lines.append("\n---\n")
    lines.append("## Extraction Metadata\n")
    if 'extraction' in document.metadata:
        ext_meta = document.metadata['extraction']
        lines.append(f"- Text blocks: {ext_meta.get('text_blocks', 0)}\n")
        lines.append(f"- Figures/Tables: {ext_meta.get('figure_blocks', 0)}\n")
    
    # Write to file
    content = '\n'.join(lines)
    output_path.write_text(content)
    
    return output_path


def generate_text_only_document(
    document: Document,
    output_path: Path,
    include_placeholders: bool = True
) -> Path:
    """Generate a plain text version of the document.
    
    Args:
        document: Document with extracted content
        output_path: Path to save the text document
        include_placeholders: Whether to include figure/table placeholders
        
    Returns:
        Path to the generated document
    """
    lines = []
    
    # Add header
    lines.append("=" * 80)
    lines.append(f"EXTRACTED DOCUMENT: {document.source_pdf}")
    lines.append(f"Total Pages: {document.metadata.get('total_pages', 'Unknown')}")
    lines.append("=" * 80)
    
    # Process each page
    for page_idx in range(document.metadata.get('total_pages', 0)):
        lines.append(f"\n\n{'=' * 20} PAGE {page_idx + 1} {'=' * 20}\n")
        
        # Get blocks for this page
        blocks_by_id = {b.id: b for b in document.blocks if b.page_index == page_idx}
        
        # Get reading order
        if hasattr(document, 'reading_order') and page_idx < len(document.reading_order):
            reading_order = document.reading_order[page_idx]
        else:
            reading_order = list(blocks_by_id.keys())
        
        # Process blocks in order
        for block_id in reading_order:
            if block_id not in blocks_by_id:
                continue
                
            block = blocks_by_id[block_id]
            
            # Skip figures/tables if not including placeholders
            if not include_placeholders and block.role in ['Figure', 'Table']:
                continue
            
            # Add content
            if block.text:
                if block.role == 'Title':
                    lines.append(f"\n{block.text.upper()}\n")
                else:
                    lines.append(f"{block.text}\n")
    
    # Write to file
    content = '\n'.join(lines)
    output_path.write_text(content)
    
    return output_path


def generate_html_document(
    document: Document,
    output_path: Path,
    include_images: bool = True,
    image_max_width: int = 800
) -> Path:
    """Generate an HTML version of the document with embedded images.
    
    Args:
        document: Document with extracted content
        output_path: Path to save the HTML document
        include_images: Whether to embed actual images
        image_max_width: Maximum width for images in pixels
        
    Returns:
        Path to the generated document
    """
    html_parts = []
    
    # HTML header
    html_parts.append("""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Extracted Document</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; }
        h1, h2, h3 { color: #333; }
        .page { margin-bottom: 50px; border-bottom: 2px solid #ccc; padding-bottom: 30px; }
        .title { font-size: 1.3em; font-weight: bold; margin: 20px 0; }
        .text { margin: 15px 0; line-height: 1.6; }
        .figure { margin: 20px 0; text-align: center; }
        .figure img { max-width: 100%; height: auto; border: 1px solid #ddd; }
        .figure-caption { font-style: italic; color: #666; margin-top: 10px; }
        .metadata { background: #f5f5f5; padding: 15px; margin-top: 30px; }
    </style>
</head>
<body>
""")
    
    # Document header
    html_parts.append(f"<h1>Extracted Document</h1>")
    html_parts.append(f"<p><strong>Source:</strong> {document.source_pdf}</p>")
    html_parts.append(f"<p><strong>Total Pages:</strong> {document.metadata.get('total_pages', 'Unknown')}</p>")
    html_parts.append("<hr>")
    
    # Process each page
    for page_idx in range(document.metadata.get('total_pages', 0)):
        html_parts.append(f'<div class="page">')
        html_parts.append(f'<h2>Page {page_idx + 1}</h2>')
        
        # Get blocks and reading order
        blocks_by_id = {b.id: b for b in document.blocks if b.page_index == page_idx}
        
        if hasattr(document, 'reading_order') and page_idx < len(document.reading_order):
            reading_order = document.reading_order[page_idx]
        else:
            reading_order = list(blocks_by_id.keys())
        
        # Process blocks
        for block_id in reading_order:
            if block_id not in blocks_by_id:
                continue
                
            block = blocks_by_id[block_id]
            
            if block.role == 'Title':
                html_parts.append(f'<div class="title">{block.text}</div>')
            
            elif block.role in ['Figure', 'Table']:
                html_parts.append('<div class="figure">')
                
                if include_images and block.image_path:
                    html_parts.append(f'<img src="{block.image_path}" alt="{block.text}" style="max-width: {image_max_width}px;">')
                    html_parts.append(f'<div class="figure-caption">{block.text}</div>')
                else:
                    html_parts.append(f'<div class="figure-caption">{block.text}</div>')
                
                html_parts.append('</div>')
            
            elif block.role in ['Text', 'List']:
                if block.text:
                    # Preserve line breaks
                    formatted_text = block.text.replace('\n', '<br>')
                    html_parts.append(f'<div class="text">{formatted_text}</div>')
        
        html_parts.append('</div>')
    
    # Metadata
    html_parts.append('<div class="metadata">')
    html_parts.append('<h3>Extraction Metadata</h3>')
    if 'extraction' in document.metadata:
        ext_meta = document.metadata['extraction']
        html_parts.append(f"<p>Text blocks: {ext_meta.get('text_blocks', 0)}</p>")
        html_parts.append(f"<p>Figures/Tables: {ext_meta.get('figure_blocks', 0)}</p>")
    html_parts.append('</div>')
    
    # HTML footer
    html_parts.append("""
</body>
</html>
""")
    
    # Write to file
    html_content = '\n'.join(html_parts)
    output_path.write_text(html_content)
    
    return output_path