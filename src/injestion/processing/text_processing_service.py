"""Centralized text processing service for the ingestion pipeline."""

import logging
import time
import threading
from contextlib import contextmanager
from typing import Optional, List, Tuple, Callable, Dict, Any
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


class TextProcessingService:
    """Centralized text processing service for the ingestion pipeline.
    
    This service provides a single point for all text processing operations,
    including spacing fixes, punctuation normalization, and other text improvements.
    
    The service is implemented as a singleton to ensure consistent processing
    across the entire pipeline and to avoid multiple initializations of heavy
    processors like WordNinja.
    
    Text processors (in order):
    1. Post-extraction cleaner – fixes PDF artifacts, truncated words, ligatures.
    2. SymSpell – medical-aware spell-checking **and** compound/word segmentation.
    3. WordNinja – fallback splitter for the rare cases SymSpell leaves untouched.
    """
    
    _instance: Optional['TextProcessingService'] = None
    
    def __new__(cls, processors=None):
        """Singleton pattern for single instance when no processors are provided."""
        # If processors are provided, create a new instance (for testing)
        if processors is not None:
            return super().__new__(cls)
        # Otherwise, use singleton pattern
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, processors=None):
        """Initialize the service with all available processors.
        
        Args:
            processors: Optional list of (name, processor_func) tuples for testing
        """
        if hasattr(self, '_initialized') and processors is None:
            return
            
        self._initialized = True
        self._lock = threading.RLock()  # Use RLock to allow nested locking
        
        if processors is not None:
            # Use provided processors (for testing)
            self._processors = list(processors)
        else:
            # Initialize default processors
            self._processors: List[Tuple[str, Callable]] = []
            self._initialize_processors()

        # Keep an immutable copy of the *default* processor pipeline so that
        # we can restore it after ad-hoc mutations performed in test cases or
        # by external callers.  Direct assignments such as
        # `service._processors = [...]` replace the list on the singleton and
        # therefore leak into subsequent tests.  Storing a pristine reference
        # allows the `process()` method to reset the pipeline after each call
        # and thereby guarantee isolation without affecting existing public
        # behaviour.
        self._default_processors: Tuple[Tuple[str, Callable], ...] = tuple(self._processors)
        logger.info(f"TextProcessingService initialized with {len(self._processors)} processors")
    
    @contextmanager
    def temporary_processors(self, processors: List[Tuple[str, Callable]]):
        """Context manager for temporarily replacing processors.
        
        This provides a thread-safe way to temporarily modify the processor
        pipeline, ensuring automatic restoration even if an exception occurs.
        
        Args:
            processors: List of (name, processor_func) tuples to use temporarily
            
        Yields:
            None
            
        Example:
            with service.temporary_processors([('custom', my_processor)]):
                result = service.process("test text")
        """
        with self._lock:
            original_processors = self._processors
            try:
                self._processors = list(processors)
                yield
            finally:
                self._processors = original_processors
    
    def _initialize_processors(self):
        """Initialize all text processors in order."""
        # Post-extraction cleaning - fixes PDF extraction artifacts
        from .text_extractors.post_extraction_cleaner import clean_extracted_text
        self._processors.append(('post_extraction_clean', clean_extracted_text))
        logger.info("Initialized post-extraction cleaner")
        
        # ------------------------------------------------------------------
        # NOTE ON PROCESSOR ORDERING
        # ------------------------------------------------------------------
        # 2025-07 update: we now **run SymSpell _before_ WordNinja**.
        #
        # Reasons:
        # 1. SymSpell already performs word-segmentation during spelling
        #    correction (via `word_segmentation` / `lookup_compound`).
        # 2. Its dictionary is medical-aware, therefore produces safer splits
        #    than WordNinja's generic Google n-gram model.
        # 3. Avoids double work and the risk that WordNinja introduces splits
        #    that SymSpell then tries to "correct" again.
        #
        # WordNinja acts as a secondary processor for the rare cases
        # SymSpell leaves untouched (typically very long out-of-vocabulary
        # strings).
        # ------------------------------------------------------------------

        # SymSpell for spell-checking and compound splitting (runs first)
        from .text_extractors.symspell_corrector_optimized import correct_medical_text_optimized
        self._processors.append(('symspell', correct_medical_text_optimized))
        logger.info("Initialized optimized SymSpell corrector")

        # WordNinja spacing fixes – runs after SymSpell
        from .text_extractors.final_spacing_fixer import fix_pdf_text_spacing
        self._processors.append(('spacing_fix', fix_pdf_text_spacing))
        logger.info("Initialized spacing fix processor with WordNinja")
        
        # Future processors can be added here
        # Examples:
        # self._processors.append(('medical_terms', self._fix_medical_terms))
        # self._processors.append(('units', self._normalize_units))
        # self._processors.append(('abbreviations', self._expand_abbreviations))
    
    def process(self, text: str, context: Dict[str, Any] = None) -> ProcessingResult:
        """Process text through all registered processors.
        
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
        
        # Run through each processor with thread safety
        with self._lock:
            current_processors = list(self._processors)
        
        for name, processor in current_processors:
            try:
                processed = processor(text)
                
                # Validate processor output
                if not isinstance(processed, str):
                    logger.error(f"Processor '{name}' returned {type(processed).__name__} instead of string")
                    continue
                
                # Check for empty result on non-empty input
                if text.strip() and not processed.strip():
                    logger.warning(f"Processor '{name}' returned empty text from non-empty input")
                    continue
                
                if processed != text:
                    modifications.append(name)
                    logger.debug(f"Processor '{name}' modified text (length: {len(text)} -> {len(processed)})")
                    text = processed
            except Exception as e:
                logger.error(f"Error in {name} processor: {e}", exc_info=True)
                raise

        # ------------------------------------------------------------------
        # Ensure test isolation / global state hygiene (thread-safe)
        # ------------------------------------------------------------------
        # Some unit-tests purposefully replace `service._processors` with a
        # custom list to validate the modification-tracking logic.  Because
        # `TextProcessingService` is a singleton those changes persist across
        # tests and can inadvertently disable the real processors (most
        # notably the `spacing_fix` step powered by WordNinja).  To avoid
        # cross-test contamination we restore the processor pipeline to the
        # default configuration captured at initialization once the current
        # processing call has finished.
        with self._lock:
            if tuple(self._processors) != self._default_processors:
                self._processors = list(self._default_processors)
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
    
    def process_simple(self, text: str) -> str:
        """Simple interface that just returns processed text.
        
        Args:
            text: The text to process
            
        Returns:
            Processed text string
        """
        return self.process(text).text
    
    def get_processor_info(self) -> List[str]:
        """Get information about loaded processors.
        
        Returns:
            List of processor names
        """
        return [name for name, _ in self._processors]
    
    def is_available(self) -> bool:
        """Check if the service has any processors available.
        
        Returns:
            True if at least one processor is loaded
        """
        return len(self._processors) > 0


# Global singleton instance
text_processor = TextProcessingService()


# Simple function interface for backwards compatibility
def process_text(text: str) -> str:
    """Process text using the global service.
    
    This is a simple wrapper around the text processing service
    for cases where you just need the processed text without metadata.
    
    Args:
        text: The text to process
        
    Returns:
        Processed text string
    """
    return text_processor.process_simple(text)
