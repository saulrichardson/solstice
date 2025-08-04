"""Simple text processing functions for the ingestion pipeline."""

import logging
import time
from typing import Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Result of text processing with metadata."""
    text: str
    original_text: str
    modifications: List[str]
    processing_time: float
    metadata: Dict[str, Any] = None

    @property
    def was_modified(self) -> bool:
        """Check if text was modified during processing."""
        return len(self.modifications) > 0


def process_text(text: str, context: Dict[str, Any] = None) -> ProcessingResult:
    """Process text through all text processors.
    
    Applies text processing in this order:
    1. Post-extraction cleaner - fixes PDF artifacts, truncated words, ligatures
    2. SymSpell - medical-aware spell-checking and compound word splitting  
    3. WordNinja - fallback spacing fixes for remaining issues
    
    Args:
        text: The text to process
        context: Optional context information (pdf path, page number, etc.)
        
    Returns:
        ProcessingResult with processed text and metadata
    """
    start_time = time.time()
    original = text
    modifications = []
    metadata = {'context': context} if context else {}
    
    # Skip processing for empty or very short text
    if not text or len(text.strip()) < 3:
        return ProcessingResult(
            text=text,
            original_text=original,
            modifications=[],
            processing_time=0.0,
            metadata=metadata
        )
    
    # Import processors - this is fast, imports are cached
    from .text_extractors.post_extraction_cleaner import clean_extracted_text
    from .text_extractors.symspell_corrector_optimized import correct_medical_text_optimized
    from .text_extractors.final_spacing_fixer import fix_pdf_text_spacing
    
    # Apply processors in sequence
    processors = [
        ('post_extraction_clean', clean_extracted_text),
        ('symspell', correct_medical_text_optimized), 
        ('spacing_fix', fix_pdf_text_spacing)
    ]
    
    for name, processor in processors:
        try:
            processed = processor(text)
            
            if processed != text:
                modifications.append(name)
                logger.debug(f"Processor '{name}' modified text (length: {len(text)} -> {len(processed)})")
                text = processed
        except Exception as e:
            logger.error(f"Error in {name} processor: {e}", exc_info=True)
            raise
    
    processing_time = time.time() - start_time
    
    # Log slow processing
    if processing_time > 0.1:
        logger.warning(
            f"Slow text processing: {processing_time:.3f}s for {len(original)} chars "
            f"with processors: {', '.join(modifications)}"
        )
    
    return ProcessingResult(
        text=text,
        original_text=original,
        modifications=modifications,
        processing_time=processing_time,
        metadata=metadata
    )


def process_text_simple(text: str) -> str:
    """Simple interface that just returns processed text.
    
    Args:
        text: The text to process
        
    Returns:
        Processed text string
    """
    return process_text(text).text