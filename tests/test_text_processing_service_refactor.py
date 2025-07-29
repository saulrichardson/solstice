"""Tests demonstrating improved testability of TextProcessingService."""

import unittest
from unittest.mock import Mock
from src.injestion.processing.text_processing_service import TextProcessingService, ProcessingResult


class TestTextProcessingServiceRefactor(unittest.TestCase):
    """Test the refactored TextProcessingService with dependency injection."""
    
    def test_singleton_still_works(self):
        """Test that singleton behavior is preserved for backward compatibility."""
        service1 = TextProcessingService()
        service2 = TextProcessingService()
        self.assertIs(service1, service2)
        
        # Should have default processors
        processors = service1.get_processor_info()
        self.assertIn('post_extraction_clean', processors)
        self.assertIn('spacing_fix', processors)
    
    def test_custom_processors_for_testing(self):
        """Test that we can create instances with custom processors for testing."""
        # Create a mock processor
        mock_processor = Mock(return_value="PROCESSED TEXT")
        
        # Create service with custom processor
        service = TextProcessingService([('mock_processor', mock_processor)])
        
        # Verify it uses our mock
        result = service.process("input text")
        self.assertEqual(result.text, "PROCESSED TEXT")
        self.assertEqual(result.modifications, ['mock_processor'])
        mock_processor.assert_called_once_with("input text")
    
    def test_multiple_mock_processors(self):
        """Test chaining multiple mock processors."""
        # Create processors that modify text in specific ways
        upper_processor = Mock(side_effect=lambda x: x.upper())
        reverse_processor = Mock(side_effect=lambda x: x[::-1])
        
        # Create service with both processors
        service = TextProcessingService([
            ('uppercase', upper_processor),
            ('reverse', reverse_processor)
        ])
        
        # Process text
        result = service.process("hello")
        
        # Should be uppercase then reversed
        self.assertEqual(result.text, "OLLEH")
        self.assertEqual(result.modifications, ['uppercase', 'reverse'])
    
    def test_processor_error_handling(self):
        """Test that processor errors are handled gracefully."""
        # Create a processor that raises an exception
        failing_processor = Mock(side_effect=Exception("Processor failed"))
        working_processor = Mock(return_value="processed")
        
        service = TextProcessingService([
            ('failing', failing_processor),
            ('working', working_processor)
        ])
        
        # Should continue with working processor despite failure
        result = service.process("test")
        self.assertEqual(result.text, "processed")
        self.assertEqual(result.modifications, ['working'])
    
    def test_no_modifications_tracking(self):
        """Test tracking when processors don't modify text."""
        # Processor that returns input unchanged
        identity_processor = Mock(side_effect=lambda x: x)
        
        service = TextProcessingService([('identity', identity_processor)])
        
        result = service.process("unchanged text")
        self.assertEqual(result.text, "unchanged text")
        self.assertEqual(result.modifications, [])  # No modifications
        self.assertFalse(result.was_modified)


if __name__ == '__main__':
    unittest.main()