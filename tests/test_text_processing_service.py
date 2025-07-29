"""Unit tests for the text processing service."""

import pytest
from unittest.mock import patch, MagicMock
import time

from src.injestion.processing.text_processing_service import (
    TextProcessingService, 
    ProcessingResult,
    text_processor,
    process_text
)


class TestTextProcessingService:
    """Test suite for TextProcessingService."""
    
    def test_singleton_pattern(self):
        """Test that TextProcessingService follows singleton pattern."""
        service1 = TextProcessingService()
        service2 = TextProcessingService()
        assert service1 is service2
        assert service1 is text_processor
    
    def test_process_empty_text(self):
        """Test processing of empty or very short text."""
        # Empty text
        result = text_processor.process("")
        assert result.text == ""
        assert result.original_text == ""
        assert result.modifications == []
        assert result.processing_time == 0.0
        
        # Very short text
        result = text_processor.process("Hi")
        assert result.text == "Hi"
        assert result.modifications == []
    
    def test_process_with_context(self):
        """Test processing with context information."""
        context = {
            'pdf_path': '/path/to/test.pdf',
            'page_num': 5,
            'bbox': (100, 200, 300, 400)
        }
        
        result = text_processor.process("Test text", context=context)
        assert result.metadata['context'] == context
    
    def test_process_simple_interface(self):
        """Test the simple string interface."""
        # Should return just the processed text
        text = "Some test text"
        processed = text_processor.process_simple(text)
        assert isinstance(processed, str)
        
        # Function interface
        processed2 = process_text(text)
        assert processed == processed2
    
    def test_processing_result_properties(self):
        """Test ProcessingResult properties."""
        result = ProcessingResult(
            text="modified",
            original_text="original",
            modifications=['spacing_fix'],
            processing_time=0.01
        )
        assert result.was_modified is True
        
        result2 = ProcessingResult(
            text="same",
            original_text="same",
            modifications=[],
            processing_time=0.01
        )
        assert result2.was_modified is False
    
    def test_get_processor_info(self):
        """Test getting processor information."""
        processors = text_processor.get_processor_info()
        assert isinstance(processors, list)
        # Should have at least spacing_fix if WordNinja is available
        # or empty list if not
    
    def test_is_available(self):
        """Test service availability check."""
        # Service should indicate if it has processors
        available = text_processor.is_available()
        assert isinstance(available, bool)
    
    @patch('src.injestion.processing.text_processing_service.logger')
    def test_error_handling(self, mock_logger):
        """Test error handling in processors."""
        # Create a service with a failing processor
        service = TextProcessingService()
        service._processors = [
            ('failing_processor', lambda x: 1/0)  # Will raise ZeroDivisionError
        ]
        
        result = service.process("Test text")
        # Should continue despite error
        assert result.text == "Test text"  # Unchanged
        assert result.modifications == []
        mock_logger.error.assert_called()
    
    @patch('src.injestion.processing.text_processing_service.logger')
    def test_slow_processing_warning(self, mock_logger):
        """Test warning for slow processing."""
        # Create a service with a slow processor
        def slow_processor(text):
            time.sleep(0.2)
            return text
        
        service = TextProcessingService()
        service._processors = [('slow_processor', slow_processor)]
        
        result = service.process("Test text")
        assert result.processing_time > 0.1
        mock_logger.warning.assert_called()
    
    def test_modification_tracking(self):
        """Test that modifications are properly tracked."""
        # Create a service with a modifying processor
        def uppercase_processor(text):
            return text.upper()
        
        service = TextProcessingService()
        service._processors = [('uppercase', uppercase_processor)]
        
        result = service.process("test text")
        assert result.text == "TEST TEXT"
        assert result.original_text == "test text"
        assert 'uppercase' in result.modifications
    
    def test_multiple_processors(self):
        """Test multiple processors in sequence."""
        # Create a service with multiple processors
        service = TextProcessingService()
        service._processors = [
            ('add_prefix', lambda x: f"PREFIX: {x}"),
            ('add_suffix', lambda x: f"{x} :SUFFIX")
        ]
        
        result = service.process("test")
        assert result.text == "PREFIX: test :SUFFIX"
        assert result.modifications == ['add_prefix', 'add_suffix']


class TestIntegrationWithSpacingFixer:
    """Integration tests with the actual spacing fixer."""
    
    @pytest.mark.skipif(
        'spacing_fix' not in text_processor.get_processor_info(),
        reason="WordNinja/spacing fixer not available"
    )
    def test_spacing_fix_integration(self):
        """Test integration with actual spacing fixer."""
        # Test known spacing issues
        test_cases = [
            ("Thesehighlightsdonot", "These highlights do not"),
            ("18yearsandolder", "18 years and older"),
        ]
        
        for input_text, expected_start in test_cases:
            result = text_processor.process(input_text)
            assert result.was_modified
            assert 'spacing_fix' in result.modifications
            # Check that it starts with expected (might have more text)
            assert result.text.startswith(expected_start)