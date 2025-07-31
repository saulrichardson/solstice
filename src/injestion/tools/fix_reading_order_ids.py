"""Tool to fix reading order IDs in existing extracted documents.

This script updates existing content.json files to ensure reading_order
arrays contain IDs that actually exist in the blocks array.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Set
import argparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fix_document_reading_order(content_path: Path) -> bool:
    """Fix reading order in a single document.
    
    Args:
        content_path: Path to content.json
        
    Returns:
        True if fixed, False if already correct
    """
    # Load document
    with open(content_path, 'r') as f:
        doc_data = json.load(f)
    
    blocks = doc_data.get('blocks', [])
    reading_order = doc_data.get('reading_order', [])
    
    if not blocks or not reading_order:
        logger.info(f"No blocks or reading order in {content_path}")
        return False
    
    # Build ID mappings
    blocks_by_page = {}
    block_ids = set()
    
    for block in blocks:
        page_idx = block.get('page_index', 0)
        block_id = block.get('id')
        
        if page_idx not in blocks_by_page:
            blocks_by_page[page_idx] = []
        blocks_by_page[page_idx].append(block)
        block_ids.add(block_id)
    
    # Check if reading order needs fixing
    needs_fix = False
    for page_idx, page_order in enumerate(reading_order):
        for ro_id in page_order:
            if ro_id not in block_ids:
                needs_fix = True
                logger.warning(f"Page {page_idx}: ID '{ro_id}' not found in blocks")
                break
    
    if not needs_fix:
        logger.info(f"Reading order already correct in {content_path}")
        return False
    
    # Fix reading order by using spatial ordering
    logger.info(f"Fixing reading order in {content_path}")
    new_reading_order = []
    
    for page_idx in range(len(reading_order)):
        page_blocks = blocks_by_page.get(page_idx, [])
        
        # Sort by spatial position (top-to-bottom, left-to-right)
        def spatial_sort_key(block):
            bbox = block.get('bbox', [0, 0, 0, 0])
            # In PDF coordinates, higher y is up, so negate for top-to-bottom
            return (-bbox[1], bbox[0])
        
        sorted_blocks = sorted(page_blocks, key=spatial_sort_key)
        page_order = [block['id'] for block in sorted_blocks]
        new_reading_order.append(page_order)
    
    # Update document
    doc_data['reading_order'] = new_reading_order
    
    # Add metadata about the fix
    if 'metadata' not in doc_data:
        doc_data['metadata'] = {}
    doc_data['metadata']['reading_order_fixed'] = True
    doc_data['metadata']['reading_order_fix_method'] = 'spatial_sorting'
    
    # Save fixed document
    with open(content_path, 'w') as f:
        json.dump(doc_data, f, indent=2)
    
    logger.info(f"Fixed reading order for {content_path.parent.parent.name}")
    return True


def fix_all_documents(cache_dir: Path) -> Dict[str, int]:
    """Fix reading order in all documents in cache.
    
    Args:
        cache_dir: Path to cache directory
        
    Returns:
        Statistics about fixes
    """
    stats = {
        'total': 0,
        'fixed': 0,
        'already_correct': 0,
        'errors': 0
    }
    
    # Find all content.json files
    for doc_dir in cache_dir.iterdir():
        if not doc_dir.is_dir():
            continue
        
        content_path = doc_dir / "extracted" / "content.json"
        if not content_path.exists():
            continue
        
        stats['total'] += 1
        
        try:
            if fix_document_reading_order(content_path):
                stats['fixed'] += 1
            else:
                stats['already_correct'] += 1
        except Exception as e:
            logger.error(f"Error fixing {content_path}: {e}")
            stats['errors'] += 1
    
    return stats


def validate_all_documents(cache_dir: Path) -> Dict[str, List[str]]:
    """Validate that all documents have consistent IDs.
    
    Args:
        cache_dir: Path to cache directory
        
    Returns:
        Dict mapping document names to list of issues
    """
    issues = {}
    
    for doc_dir in cache_dir.iterdir():
        if not doc_dir.is_dir():
            continue
        
        content_path = doc_dir / "extracted" / "content.json"
        if not content_path.exists():
            continue
        
        doc_issues = []
        
        try:
            with open(content_path, 'r') as f:
                doc_data = json.load(f)
            
            blocks = doc_data.get('blocks', [])
            reading_order = doc_data.get('reading_order', [])
            
            # Collect all block IDs
            block_ids = {block.get('id') for block in blocks}
            
            # Check if we have reading_order at all
            if not reading_order:
                doc_issues.append("No reading_order array found")
            else:
                # Check reading order
                for page_idx, page_order in enumerate(reading_order):
                    if isinstance(page_order, list):
                        for ro_id in page_order:
                            if ro_id not in block_ids:
                                doc_issues.append(
                                    f"Page {page_idx}: Reading order ID '{ro_id}' not in blocks"
                                )
            
            # Check for duplicate IDs
            id_counts = {}
            for block in blocks:
                block_id = block.get('id')
                id_counts[block_id] = id_counts.get(block_id, 0) + 1
            
            for block_id, count in id_counts.items():
                if count > 1:
                    doc_issues.append(f"Duplicate block ID: '{block_id}' appears {count} times")
            
            if doc_issues:
                issues[doc_dir.name] = doc_issues
                
        except Exception as e:
            issues[doc_dir.name] = [f"Error reading document: {e}"]
    
    return issues


def main():
    parser = argparse.ArgumentParser(
        description="Fix reading order IDs in extracted documents"
    )
    parser.add_argument(
        '--cache-dir',
        type=Path,
        default=Path('data/scientific_cache'),
        help='Path to cache directory'
    )
    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Only validate, do not fix'
    )
    parser.add_argument(
        '--document',
        type=str,
        help='Fix only a specific document'
    )
    
    args = parser.parse_args()
    
    if args.validate_only:
        # Validate all documents
        logger.info("Validating all documents...")
        issues = validate_all_documents(args.cache_dir)
        
        if not issues:
            logger.info("All documents have consistent IDs!")
        else:
            logger.warning(f"Found issues in {len(issues)} documents:")
            for doc_name, doc_issues in issues.items():
                print(f"\n{doc_name}:")
                for issue in doc_issues:
                    print(f"  - {issue}")
    
    elif args.document:
        # Fix specific document
        content_path = args.cache_dir / args.document / "extracted" / "content.json"
        if not content_path.exists():
            logger.error(f"Document not found: {args.document}")
            return
        
        if fix_document_reading_order(content_path):
            logger.info(f"Fixed {args.document}")
        else:
            logger.info(f"{args.document} already has correct reading order")
    
    else:
        # Fix all documents
        logger.info("Fixing reading order in all documents...")
        stats = fix_all_documents(args.cache_dir)
        
        print(f"\nResults:")
        print(f"  Total documents: {stats['total']}")
        print(f"  Fixed: {stats['fixed']}")
        print(f"  Already correct: {stats['already_correct']}")
        print(f"  Errors: {stats['errors']}")


if __name__ == '__main__':
    main()