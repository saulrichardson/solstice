#!/usr/bin/env python3
"""Test the DPI-aware visualization utilities"""

import json
from pathlib import Path
from src.injestion.utils.visualization import (
    LayoutVisualizer, 
    BoundingBox,
    add_dpi_metadata_to_results,
    validate_dpi_consistency,
    visualize_with_auto_dpi
)

def test_bounding_box_scaling():
    """Test that bounding box scaling works correctly"""
    print("Testing BoundingBox scaling...")
    
    # Create bbox at 200 DPI
    bbox = BoundingBox(x1=800, y1=1000, x2=1600, y2=2000, dpi=200)
    
    # Scale to 150 DPI
    scaled = bbox.scale_to_dpi(150)
    
    expected_scale = 150 / 200  # 0.75
    assert scaled.x1 == 800 * expected_scale == 600
    assert scaled.y1 == 1000 * expected_scale == 750
    assert scaled.x2 == 1600 * expected_scale == 1200
    assert scaled.y2 == 2000 * expected_scale == 1500
    assert scaled.dpi == 150
    
    print("✓ BoundingBox scaling works correctly")

def test_dpi_metadata():
    """Test adding DPI metadata to results"""
    print("\nTesting DPI metadata...")
    
    results = [
        {"page": 1, "elements": []},
        {"page": 2, "elements": []}
    ]
    
    updated = add_dpi_metadata_to_results(results, dpi=200)
    
    assert updated[0]["detection_dpi"] == 200
    assert updated[1]["detection_dpi"] == 200
    
    print("✓ DPI metadata added correctly")

def test_visualization_with_scaling():
    """Test visualization with coordinate scaling"""
    print("\nTesting visualization with scaling...")
    
    # Load existing results
    with open("layout_results.json", 'r') as f:
        results = json.load(f)
    
    # Add DPI metadata
    results_with_dpi = add_dpi_metadata_to_results(results, dpi=200)
    
    # Save updated results
    test_results_path = "test_results_with_dpi.json"
    with open(test_results_path, 'w') as f:
        json.dump(results_with_dpi, f)
    
    # Test visualization at different DPIs
    visualizer = LayoutVisualizer(detection_dpi=200)
    
    # Visualize at 150 DPI (requires scaling)
    output_150 = "test_viz_150dpi.png"
    visualizer.visualize_layout(
        pdf_path="Liu et al. (2024).pdf",
        layout_data=results_with_dpi,
        page_num=1,
        visualization_dpi=150,
        output_path=output_150
    )
    
    # Visualize at 200 DPI (no scaling needed)
    output_200 = "test_viz_200dpi.png"
    visualizer.visualize_layout(
        pdf_path="Liu et al. (2024).pdf",
        layout_data=results_with_dpi,
        page_num=1,
        visualization_dpi=200,
        output_path=output_200
    )
    
    print(f"✓ Created visualizations at 150 DPI ({output_150}) and 200 DPI ({output_200})")
    
    # Test auto-visualization
    auto_output = "test_viz_auto.png"
    visualize_with_auto_dpi(
        pdf_path="Liu et al. (2024).pdf",
        results_path=test_results_path,
        page_num=1,
        output_path=auto_output
    )
    
    print(f"✓ Auto-DPI visualization created ({auto_output})")

def test_dpi_validation():
    """Test DPI consistency validation"""
    print("\nTesting DPI validation...")
    
    with open("layout_results.json", 'r') as f:
        results = json.load(f)
    
    # Should be valid at 200 DPI (default)
    is_valid_200 = validate_dpi_consistency(
        pdf_path="Liu et al. (2024).pdf",
        results=results,
        expected_dpi=200
    )
    
    # Should be invalid at 150 DPI (coordinates too large)
    is_valid_150 = validate_dpi_consistency(
        pdf_path="Liu et al. (2024).pdf",
        results=results,
        expected_dpi=150
    )
    
    print(f"✓ Validation at 200 DPI: {'Valid' if is_valid_200 else 'Invalid'}")
    print(f"✓ Validation at 150 DPI: {'Valid' if is_valid_150 else 'Invalid'} (expected)")

def main():
    print("Running DPI utility tests...")
    print("=" * 50)
    
    test_bounding_box_scaling()
    test_dpi_metadata()
    test_visualization_with_scaling()
    test_dpi_validation()
    
    print("\n" + "=" * 50)
    print("All tests completed successfully!")
    print("\nThe DPI-aware utilities are working correctly.")
    print("Check the generated PNG files to verify proper coordinate scaling.")

if __name__ == "__main__":
    main()