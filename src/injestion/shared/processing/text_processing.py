"""Simple text processing functions for the ingestion pipeline."""

import logging

logger = logging.getLogger(__name__)


def process_text(text: str) -> str:
    """Process text through all text processors.
    
    Applies text processing in this order:
    1. Post-extraction cleaner - fixes PDF artifacts, truncated words, ligatures
    2. SymSpell - medical-aware spell-checking and compound word splitting  
    3. WordNinja - fallback spacing fixes for remaining issues
    
    Args:
        text: The text to process
        
    Returns:
        Processed text string
    """
    # Skip processing for empty or very short text
    if not text or len(text.strip()) < 3:
        return text
    
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
                logger.debug(f"Processor '{name}' modified text (length: {len(text)} -> {len(processed)})")
                text = processed
        except Exception as e:
            logger.error(f"Error in {name} processor: {e}", exc_info=True)
            raise
    
    return text


# Single operating model - only one way to process text
# Use process_text() for all text processing needs