#!/usr/bin/env python3
"""Test different layout detection models"""

import sys
import os
from pathlib import Path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import layoutparser as lp
from pdf2image import convert_from_path
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Available pre-trained models in LayoutParser
AVAILABLE_MODELS = {
    "PubLayNet": {
        "config": "lp://PubLayNet/mask_rcnn_R_50_FPN_3x/config",
        "label_map": {0: "Text", 1: "Title", 2: "List", 3: "Table", 4: "Figure"},
        "description": "Trained on scientific papers"
    },
    "PrimaLayout": {
        "config": "lp://PrimaLayout/mask_rcnn_R_50_FPN_3x/config", 
        "label_map": {0: "Background", 1: "TextRegion", 2: "ImageRegion", 3: "TableRegion", 4: "MathsRegion", 5: "SeparatorRegion", 6: "OtherRegion"},
        "description": "Trained on diverse document types"
    },
    "NewspaperNavigator": {
        "config": "lp://NewspaperNavigator/faster_rcnn_R_50_FPN_3x/config",
        "label_map": {0: "Photograph", 1: "Illustration", 2: "Map", 3: "Comics/Cartoon", 4: "Editorial Cartoon", 5: "Headline", 6: "Advertisement"},
        "description": "Trained on historical newspapers"
    },
    "TableBank": {
        "config": "lp://TableBank/faster_rcnn_R_50_FPN_3x/config",
        "label_map": {0: "Table"},
        "description": "Specialized for table detection"
    },
    "MFD": {
        "config": "lp://MFD/faster_rcnn_R_50_FPN_3x/config",
        "label_map": {0: "Figure"},
        "description": "Mathematical Formula Detection"
    }
}

def test_model(image, model_name, model_info):
    """Test a specific model"""
    print(f"\n{'='*60}")
    print(f"Testing: {model_name}")
    print(f"Description: {model_info['description']}")
    print(f"{'='*60}")
    
    try:
        # Initialize model
        model = lp.Detectron2LayoutModel(
            model_info['config'],
            extra_config=[
                "MODEL.ROI_HEADS.SCORE_THRESH_TEST", 0.1,
            ],
            label_map=model_info['label_map']
        )
        
        # Run detection
        layout = model.detect(image)
        
        # Analyze results
        print(f"\nDetected {len(layout)} boxes:")
        by_type = {}
        for box in layout:
            by_type.setdefault(str(box.type), []).append(box)
        
        for box_type, boxes in sorted(by_type.items()):
            print(f"  - {box_type}: {len(boxes)} boxes")
        
        # Create visualization
        fig, ax = plt.subplots(1, 1, figsize=(10, 14))
        ax.imshow(image)
        
        # Define colors
        colors = plt.cm.tab10(range(len(model_info['label_map'])))
        color_map = {label: colors[i] for i, label in enumerate(model_info['label_map'].values())}
        
        for i, box in enumerate(layout):
            rect = patches.Rectangle(
                (box.block.x_1, box.block.y_1),
                box.block.x_2 - box.block.x_1,
                box.block.y_2 - box.block.y_1,
                linewidth=2,
                edgecolor=color_map.get(str(box.type), 'black'),
                facecolor='none',
                alpha=0.8
            )
            ax.add_patch(rect)
            
            # Add label
            ax.text(
                box.block.x_1 + 5,
                box.block.y_1 + 30,
                f"{box.type}",
                color='white',
                fontsize=10,
                bbox=dict(boxstyle="round,pad=0.3", 
                         facecolor=color_map.get(str(box.type), 'black'), 
                         alpha=0.8)
            )
        
        ax.set_xlim(0, image.width)
        ax.set_ylim(image.height, 0)
        ax.axis('off')
        plt.title(f"{model_name} - {len(layout)} detections")
        plt.tight_layout()
        
        output_path = f"flublok_model_{model_name.lower().replace(' ', '_')}.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"\nVisualization saved to: {output_path}")
        
        return layout
        
    except Exception as e:
        print(f"\nError testing {model_name}: {str(e)}")
        return None

def main():
    pdf_path = Path("/Users/saul/projects/solstice/solstice/data/marketing_slide/FlublokOnePage.pdf")
    
    print(f"Testing different models on: {pdf_path.name}")
    
    # Convert PDF to image
    images = convert_from_path(str(pdf_path), dpi=400)
    image = images[0]
    
    # Test each available model
    results = {}
    for model_name, model_info in AVAILABLE_MODELS.items():
        if model_name in ["PubLayNet", "PrimaLayout", "NewspaperNavigator"]:  # Test most relevant ones
            layout = test_model(image, model_name, model_info)
            if layout:
                results[model_name] = layout
    
    # Summary comparison
    print(f"\n{'='*60}")
    print("SUMMARY COMPARISON")
    print(f"{'='*60}")
    
    for model_name, layout in results.items():
        if layout:
            text_like_count = 0
            for box in layout:
                box_type = str(box.type).lower()
                if any(word in box_type for word in ['text', 'title', 'headline', 'caption']):
                    text_like_count += 1
            
            print(f"\n{model_name}:")
            print(f"  Total boxes: {len(layout)}")
            print(f"  Text-like boxes: {text_like_count}")

if __name__ == "__main__":
    main()