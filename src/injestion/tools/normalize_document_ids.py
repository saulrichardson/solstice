"""Normalize document IDs to use consistent block_X_XXX format.

This tool updates existing documents to use a consistent ID format,
making the system cleaner and easier to debug.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple
import argparse
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def normalize_document(content_path: Path, backup: bool = True) -> bool:
    """Normalize IDs in a single document to block_X_XXX format.
    
    Args:
        content_path: Path to content.json
        backup: Whether to save original with timestamp
        
    Returns:
        True if normalized, False if already normalized
    """
    # Load document
    with open(content_path, 'r') as f:
        doc_data = json.load(f)
    
    blocks = doc_data.get('blocks', [])
    reading_order = doc_data.get('reading_order', [])
    
    if not blocks:
        logger.info(f"No blocks in {content_path}")
        return False
    
    # Check if already normalized
    all_normalized = all(
        block.get('id', '').startswith('block_') 
        for block in blocks
    )
    
    if all_normalized:
        logger.info(f"Already normalized: {content_path.parent.parent.name}")
        return False
    
    # Create backup if requested
    if backup:
        backup_path = content_path.with_suffix(f'.backup_{datetime.now():%Y%m%d_%H%M%S}.json')
        with open(backup_path, 'w') as f:
            json.dump(doc_data, f, indent=2)
        logger.info(f"Created backup: {backup_path.name}")
    
    # Build ID mapping: old_id -> new_id
    id_mapping = {}
    normalized_blocks = []
    
    # Group blocks by page for consistent numbering
    blocks_by_page = {}
    for block in blocks:
        page = block.get('page_index', 0)
        if page not in blocks_by_page:
            blocks_by_page[page] = []
        blocks_by_page[page].append(block)
    
    # Assign new IDs maintaining page grouping
    for page_idx in sorted(blocks_by_page.keys()):
        page_blocks = blocks_by_page[page_idx]
        
        # Sort by y-position (top to bottom) then x-position (left to right)
        # to assign IDs in a logical order
        def spatial_key(block):
            bbox = block.get('bbox', [0, 0, 0, 0])
            return (-bbox[1], bbox[0])  # -y for top-to-bottom
        
        sorted_blocks = sorted(page_blocks, key=spatial_key)
        
        for idx, block in enumerate(sorted_blocks):
            old_id = block['id']
            new_id = f"block_{page_idx}_{idx:03d}"
            
            # Update mapping
            id_mapping[old_id] = new_id
            
            # Create updated block
            new_block = block.copy()
            new_block['id'] = new_id
            
            # Add normalization metadata
            if 'metadata' not in new_block:
                new_block['metadata'] = {}
            new_block['metadata']['original_id'] = old_id
            new_block['metadata']['normalized'] = True
            
            normalized_blocks.append(new_block)
    
    # Update reading order with new IDs
    normalized_reading_order = []
    for page_order in reading_order:
        new_page_order = []
        for old_id in page_order:
            if old_id in id_mapping:
                new_page_order.append(id_mapping[old_id])
            else:
                logger.warning(f"Reading order ID not found in mapping: {old_id}")
        normalized_reading_order.append(new_page_order)
    
    # Update document
    doc_data['blocks'] = normalized_blocks
    doc_data['reading_order'] = normalized_reading_order
    
    # Add normalization metadata
    if 'metadata' not in doc_data:
        doc_data['metadata'] = {}
    doc_data['metadata']['ids_normalized'] = True
    doc_data['metadata']['normalization_date'] = datetime.now().isoformat()
    doc_data['metadata']['id_mapping_count'] = len(id_mapping)
    
    # Save normalized document
    with open(content_path, 'w') as f:
        json.dump(doc_data, f, indent=2)
    
    logger.info(f"Normalized {len(id_mapping)} IDs in {content_path.parent.parent.name}")
    return True


def normalize_all_documents(cache_dir: Path, backup: bool = True) -> Dict[str, int]:
    """Normalize IDs in all documents.
    
    Args:
        cache_dir: Path to cache directory
        backup: Whether to create backups
        
    Returns:
        Statistics about normalization
    """
    stats = {
        'total': 0,
        'normalized': 0,
        'already_normalized': 0,
        'errors': 0
    }
    
    for doc_dir in cache_dir.iterdir():
        if not doc_dir.is_dir():
            continue
        
        content_path = doc_dir / "extracted" / "content.json"
        if not content_path.exists():
            continue
        
        stats['total'] += 1
        
        try:
            if normalize_document(content_path, backup=backup):
                stats['normalized'] += 1
            else:
                stats['already_normalized'] += 1
        except Exception as e:
            logger.error(f"Error normalizing {doc_dir.name}: {e}")
            stats['errors'] += 1
    
    return stats


def check_normalization(cache_dir: Path) -> Dict[str, Dict]:
    """Check normalization status of all documents.
    
    Returns:
        Dict mapping document names to their ID statistics
    """
    results = {}
    
    for doc_dir in cache_dir.iterdir():
        if not doc_dir.is_dir():
            continue
        
        content_path = doc_dir / "extracted" / "content.json"
        if not content_path.exists():
            continue
        
        try:
            with open(content_path, 'r') as f:
                doc_data = json.load(f)
            
            blocks = doc_data.get('blocks', [])
            
            # Count ID types
            id_types = {
                'block_': 0,
                'det_': 0,
                'mrg_': 0,
                'other': 0
            }
            
            for block in blocks:
                block_id = block.get('id', '')
                if block_id.startswith('block_'):
                    id_types['block_'] += 1
                elif block_id.startswith('det_'):
                    id_types['det_'] += 1
                elif block_id.startswith('mrg_'):
                    id_types['mrg_'] += 1
                else:
                    id_types['other'] += 1
            
            results[doc_dir.name] = {
                'total_blocks': len(blocks),
                'id_types': id_types,
                'normalized': id_types['block_'] == len(blocks),
                'has_metadata': 'ids_normalized' in doc_data.get('metadata', {})
            }
            
        except Exception as e:
            results[doc_dir.name] = {'error': str(e)}
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Normalize document IDs to consistent block_X_XXX format"
    )
    parser.add_argument(
        '--cache-dir',
        type=Path,
        default=Path('data/cache'),
        help='Path to cache directory'
    )
    parser.add_argument(
        '--check-only',
        action='store_true',
        help='Only check normalization status, do not modify'
    )
    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='Do not create backup files'
    )
    parser.add_argument(
        '--document',
        type=str,
        help='Normalize only a specific document'
    )
    
    args = parser.parse_args()
    
    if args.check_only:
        # Check normalization status
        logger.info("Checking normalization status...")
        results = check_normalization(args.cache_dir)
        
        print("\nNormalization Status:")
        print("-" * 60)
        
        for doc_name, info in sorted(results.items()):
            if 'error' in info:
                print(f"{doc_name}: ERROR - {info['error']}")
            else:
                status = "✓ Normalized" if info['normalized'] else "✗ Mixed IDs"
                print(f"{doc_name}: {status}")
                if not info['normalized']:
                    print(f"  - block_: {info['id_types']['block_']}")
                    print(f"  - det_: {info['id_types']['det_']}")
                    print(f"  - mrg_: {info['id_types']['mrg_']}")
                    if info['id_types']['other'] > 0:
                        print(f"  - other: {info['id_types']['other']}")
    
    elif args.document:
        # Normalize specific document
        content_path = args.cache_dir / args.document / "extracted" / "content.json"
        if not content_path.exists():
            logger.error(f"Document not found: {args.document}")
            return
        
        if normalize_document(content_path, backup=not args.no_backup):
            logger.info(f"Successfully normalized {args.document}")
        else:
            logger.info(f"{args.document} was already normalized")
    
    else:
        # Normalize all documents
        logger.info("Normalizing all documents...")
        stats = normalize_all_documents(args.cache_dir, backup=not args.no_backup)
        
        print(f"\nResults:")
        print(f"  Total documents: {stats['total']}")
        print(f"  Normalized: {stats['normalized']}")
        print(f"  Already normalized: {stats['already_normalized']}")
        print(f"  Errors: {stats['errors']}")


if __name__ == '__main__':
    main()