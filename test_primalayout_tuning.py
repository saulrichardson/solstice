#!/usr/bin/env python3
"""Demonstrate PrimaLayout tuning parameters"""

import sys
import os
from pathlib import Path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import layoutparser as lp
from pdf2image import convert_from_path

def demonstrate_parameters():
    """Show all tunable parameters for PrimaLayout"""
    
    print("PrimaLayout Configuration Options")
    print("=" * 60)
    
    # 1. SCORE THRESHOLD
    print("\n1. SCORE THRESHOLD (MODEL.ROI_HEADS.SCORE_THRESH_TEST)")
    print("   - Controls minimum confidence for detections")
    print("   - Range: 0.0 to 1.0")
    print("   - Lower = more detections (including low confidence)")
    print("   - Higher = fewer detections (only high confidence)")
    print("   - Default: 0.5")
    print("   - Recommended: 0.1-0.3 for marketing docs")
    
    # 2. NMS THRESHOLD  
    print("\n2. NMS THRESHOLD (MODEL.ROI_HEADS.NMS_THRESH_TEST)")
    print("   - Non-Maximum Suppression - controls overlapping boxes")
    print("   - Range: 0.0 to 1.0")
    print("   - Lower = aggressive suppression (fewer overlaps)")
    print("   - Higher = permissive (allows more overlaps)")
    print("   - Default: 0.5")
    print("   - Recommended: 0.3-0.5 for dense layouts")
    
    # 3. DETECTIONS PER IMAGE
    print("\n3. MAX DETECTIONS (MODEL.TEST.DETECTIONS_PER_IMAGE)")
    print("   - Maximum number of detections per page")
    print("   - Default: 100")
    print("   - Increase for complex documents")
    
    # 4. BOX REGRESSION WEIGHTS
    print("\n4. BOX REGRESSION (MODEL.ROI_BOX_HEAD.BBOX_REG_WEIGHTS)")
    print("   - Fine-tune bounding box coordinates")
    print("   - Default: (10.0, 10.0, 5.0, 5.0)")
    print("   - Adjust if boxes are consistently too large/small")
    
    # 5. MASK THRESHOLD
    print("\n5. MASK THRESHOLD (MODEL.ROI_MASK_HEAD.SCORE_THRESH_TEST)")
    print("   - For pixel-level segmentation masks")
    print("   - Default: 0.5")
    
    print("\n" + "=" * 60)
    print("EXAMPLE CONFIGURATIONS")
    print("=" * 60)

def test_configurations(pdf_path):
    """Test different PrimaLayout configurations"""
    
    images = convert_from_path(str(pdf_path), dpi=400)
    image = images[0]
    
    configs = [
        {
            "name": "Conservative (High Precision)",
            "settings": [
                ["MODEL.ROI_HEADS.SCORE_THRESH_TEST", 0.5],
                ["MODEL.ROI_HEADS.NMS_THRESH_TEST", 0.3],
                ["MODEL.TEST.DETECTIONS_PER_IMAGE", 50]
            ]
        },
        {
            "name": "Balanced (Recommended)",
            "settings": [
                ["MODEL.ROI_HEADS.SCORE_THRESH_TEST", 0.2],
                ["MODEL.ROI_HEADS.NMS_THRESH_TEST", 0.4],
                ["MODEL.TEST.DETECTIONS_PER_IMAGE", 100]
            ]
        },
        {
            "name": "Aggressive (High Recall)",
            "settings": [
                ["MODEL.ROI_HEADS.SCORE_THRESH_TEST", 0.05],
                ["MODEL.ROI_HEADS.NMS_THRESH_TEST", 0.6],
                ["MODEL.TEST.DETECTIONS_PER_IMAGE", 200]
            ]
        },
        {
            "name": "Marketing Optimized",
            "settings": [
                ["MODEL.ROI_HEADS.SCORE_THRESH_TEST", 0.15],
                ["MODEL.ROI_HEADS.NMS_THRESH_TEST", 0.4],
                ["MODEL.TEST.DETECTIONS_PER_IMAGE", 150],
                # Allow smaller text regions
                ["MODEL.ROI_HEADS.SCORE_THRESH_TEST", 0.1],
            ]
        }
    ]
    
    print("\nTesting configurations on:", pdf_path.name)
    print("-" * 60)
    
    for config in configs:
        print(f"\n{config['name']}:")
        
        # Initialize model with settings
        # Flatten the settings list for extra_config
        extra_config_flat = []
        for setting in config['settings']:
            extra_config_flat.extend(setting)
        
        model = lp.Detectron2LayoutModel(
            "lp://PrimaLayout/mask_rcnn_R_50_FPN_3x/config",
            extra_config=extra_config_flat,
            label_map={
                0: "Background",
                1: "TextRegion", 
                2: "ImageRegion",
                3: "TableRegion",
                4: "MathsRegion",
                5: "SeparatorRegion",
                6: "OtherRegion"
            }
        )
        
        # Run detection
        layout = model.detect(image)
        
        # Report results
        by_type = {}
        for box in layout:
            by_type.setdefault(str(box.type), []).append(box)
        
        print(f"  Total detections: {len(layout)}")
        for box_type, boxes in sorted(by_type.items()):
            if box_type != "Background":
                print(f"    {box_type}: {len(boxes)}")
        
        # Calculate coverage
        text_boxes = by_type.get("TextRegion", [])
        if text_boxes:
            avg_score = sum(b.score for b in text_boxes) / len(text_boxes)
            print(f"  Average TextRegion confidence: {avg_score:.2f}")

def main():
    # Show parameter documentation
    demonstrate_parameters()
    
    # Test on marketing PDF
    pdf_path = Path("/Users/saul/projects/solstice/solstice/data/marketing_slide/FlublokOnePage.pdf")
    if pdf_path.exists():
        test_configurations(pdf_path)

if __name__ == "__main__":
    main()