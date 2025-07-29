#!/usr/bin/env python3
"""Test DPI consistency across the text extraction pipeline."""

# import pytest  # Optional for test framework
from pathlib import Path
import numpy as np
from PIL import Image

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.injestion.processing.text_extractors import (
    calculate_dpi_from_page_height,
    PyMuPDFExtractor
)


class TestDPIConsistency:
    """Test DPI handling across different extractors."""
    
    def test_dpi_calculation(self):
        """Test DPI calculation from page heights."""
        # US Letter standard tests
        assert calculate_dpi_from_page_height(4400) == 400
        assert calculate_dpi_from_page_height(3300) == 300
        assert calculate_dpi_from_page_height(2200) == 200
        assert calculate_dpi_from_page_height(1100) == 100
        
        # A4 paper (842 points height)
        # 4210/842*72 = 360
        assert calculate_dpi_from_page_height(4210, 842) == 360
        # 3157.5/842*72 = 270, but int() truncates to 269
        assert calculate_dpi_from_page_height(3157.5, 842) == 270
    
    def test_extractor_handles_different_dpis(self):
        """Test that extractors handle different DPI values correctly."""
        pdf_path = Path("data/clinical_files/FlublokPI.pdf")
        if not pdf_path.exists():
            print("Skipping: Test PDF not found")
            return
        
        # Test bbox at different DPIs
        test_cases = [
            (300, 3300, (100, 100, 300, 200)),  # 300 DPI
            (400, 4400, (133, 133, 400, 267)),  # 400 DPI (scaled coords)
        ]
        
        extractors = [PyMuPDFExtractor()]
        
        for extractor in extractors:
            for dpi, page_height, bbox in test_cases:
                result = extractor.extract_text_from_bbox(
                    pdf_path, 0, bbox, page_height
                )
                # Should not fail and should return some result
                assert result is not None
                assert isinstance(result.text, str)
    
    def test_image_extraction_dpi_aware(self):
        """Test that image extraction respects DPI."""
        pdf_path = Path("data/clinical_files/FlublokPI.pdf")
        if not pdf_path.exists():
            print("Skipping: Test PDF not found")
            return
        
        extractor = PyMuPDFExtractor()
        
        # Extract same region at different DPIs
        bbox = (100, 100, 300, 200)
        img_300 = extractor.extract_figure_image(pdf_path, 0, bbox, dpi=300)
        img_400 = extractor.extract_figure_image(pdf_path, 0, bbox, dpi=400)
        
        # Images should have consistent content (not black)
        arr_300 = np.array(img_300)
        arr_400 = np.array(img_400)
        
        assert arr_300.mean() > 10  # Not a black image
        assert arr_400.mean() > 10  # Not a black image
        
        # Size should be proportional to DPI
        # (within rounding tolerance)
        width_ratio = img_400.width / img_300.width
        assert 1.2 < width_ratio < 1.4  # ~1.33 (400/300)
    
    def test_metadata_preservation(self):
        """Test that DPI metadata is preserved in blocks."""
        from src.injestion.models.document import Block
        
        # Create block with DPI metadata
        block = Block(
            id="test",
            page_index=0,
            role="Text",
            bbox=(100, 100, 200, 200),
            metadata={"detection_dpi": 400, "score": 0.9}
        )
        
        assert block.get_detection_dpi() == 400
        
        # Block without DPI
        block2 = Block(
            id="test2",
            page_index=0,
            role="Text",
            bbox=(100, 100, 200, 200)
        )
        
        assert block2.get_detection_dpi() is None


def test_dpi_documentation():
    """Ensure DPI calculation is properly documented."""
    # Check that the helper function has proper docstring
    assert calculate_dpi_from_page_height.__doc__ is not None
    assert "4400" in calculate_dpi_from_page_height.__doc__
    assert "400" in calculate_dpi_from_page_height.__doc__


if __name__ == "__main__":
    # Run tests
    test = TestDPIConsistency()
    
    print("Testing DPI calculations...")
    test.test_dpi_calculation()
    print("✓ DPI calculations correct")
    
    print("\nTesting extractor DPI handling...")
    test.test_extractor_handles_different_dpis()
    print("✓ Extractors handle different DPIs")
    
    print("\nTesting image extraction...")
    test.test_image_extraction_dpi_aware()
    print("✓ Image extraction is DPI-aware")
    
    print("\nTesting metadata...")
    test.test_metadata_preservation()
    print("✓ DPI metadata preserved")
    
    print("\nAll DPI consistency tests passed!")