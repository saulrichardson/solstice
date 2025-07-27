#!/usr/bin/env python3
"""Test abstract detection and proper handling of List vs Text conflicts."""

import json
import uuid
from pathlib import Path
from pdf2image import convert_from_path
from src.injestion.layout_pipeline import LayoutDetectionPipeline
from src.injestion.agent.refine_layout import Box
from src.injestion.agent.refine_layout_simple import refine_page_layout_simple
from src.injestion.agent.merge_boxes_weighted import calculate_box_weight
from src.injestion.agent.merge_boxes_advanced import get_box_area, get_overlap_area
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Rectangle


def find_list_text_conflicts(boxes):
    """Find all List-Text conflicts and analyze them."""
    conflicts = []
    
    for i, box1 in enumerate(boxes):
        for j, box2 in enumerate(boxes):
            if i >= j:
                continue
                
            # Only interested in List vs Text
            if not ((box1.label == "List" and box2.label == "Text") or 
                   (box1.label == "Text" and box2.label == "List")):
                continue
                
            overlap = get_overlap_area(box1.bbox, box2.bbox)
            if overlap > 0:
                area1 = get_box_area(box1.bbox)
                area2 = get_box_area(box2.bbox)
                
                conflicts.append({
                    'list_box': box1 if box1.label == "List" else box2,
                    'text_box': box2 if box1.label == "List" else box1,
                    'overlap_area': overlap,
                    'overlap_pct_list': overlap / area1 if box1.label == "List" else overlap / area2,
                    'overlap_pct_text': overlap / area2 if box1.label == "List" else overlap / area1,
                })
    
    return conflicts


def analyze_box_content(box, page_image):
    """Analyze a box's position and characteristics to guess its content type."""
    x1, y1, x2, y2 = box.bbox
    width = x2 - x1
    height = y2 - y1
    area = width * height
    aspect_ratio = width / height if height > 0 else 0
    
    # Position indicators
    page_height = page_image.height
    relative_y = y1 / page_height
    
    # Size indicators
    page_area = page_image.width * page_image.height
    area_ratio = area / page_area
    
    characteristics = {
        'position': {
            'y1': y1,
            'y2': y2,
            'relative_y': relative_y,
            'is_top_third': relative_y < 0.33,
            'is_middle_third': 0.33 <= relative_y < 0.66,
        },
        'dimensions': {
            'width': width,
            'height': height,
            'area': area,
            'area_ratio': area_ratio,
            'aspect_ratio': aspect_ratio,
        },
        'likely_content': guess_content_type(box, relative_y, area_ratio, aspect_ratio)
    }
    
    return characteristics


def guess_content_type(box, relative_y, area_ratio, aspect_ratio):
    """Guess what type of content this might be based on characteristics."""
    # Abstract heuristics
    if (0.15 < relative_y < 0.5 and  # Below title, upper half of page
        area_ratio > 0.05 and         # Substantial size
        aspect_ratio > 2.0 and        # Wide
        box.label in ["List", "Text"]):
        return "likely_abstract"
    
    # List heuristics - true lists are usually:
    # - Narrow (bullets/numbers take space)
    # - Multiple smaller items
    # - Not extremely wide
    if (box.label == "List" and
        aspect_ratio < 4.0):  # Not extremely wide
        return "likely_true_list"
    
    return "unknown"


def test_abstract_detection():
    """Analyze List vs Text conflicts to identify abstracts."""
    
    pdf_path = Path("Liu et al. (2024).pdf")
    if not pdf_path.exists():
        print(f"Error: {pdf_path} not found")
        return
    
    print("Analyzing List vs Text conflicts for abstract detection...")
    print("="*70)
    
    # Get detections
    pipeline = LayoutDetectionPipeline()
    layouts = pipeline.process_pdf(pdf_path)
    
    # Convert first page
    images = convert_from_path(pdf_path, first_page=1, last_page=1, dpi=200)
    page_image = images[0]
    
    # Convert to Box format
    page_layout = layouts[0]
    original_boxes = [
        Box(
            id=str(uuid.uuid4())[:8],
            bbox=(
                float(elem.block.x_1),
                float(elem.block.y_1),
                float(elem.block.x_2),
                float(elem.block.y_2),
            ),
            label=str(elem.type) if elem.type else "Unknown",
            score=float(elem.score or 0.0),
        )
        for elem in page_layout
    ]
    
    # Find List-Text conflicts
    conflicts = find_list_text_conflicts(original_boxes)
    
    print(f"\nFound {len(conflicts)} List-Text conflicts")
    
    # Analyze each conflict
    for i, conflict in enumerate(conflicts):
        list_box = conflict['list_box']
        text_box = conflict['text_box']
        
        print(f"\nConflict {i+1}:")
        print(f"  List box: score={list_box.score:.3f}")
        print(f"  Text box: score={text_box.score:.3f}")
        print(f"  Overlap: {conflict['overlap_pct_text']:.1%} of Text covered")
        
        # Analyze the List box characteristics
        list_analysis = analyze_box_content(list_box, page_image)
        print(f"\n  List box analysis:")
        print(f"    Position: y={list_analysis['position']['y1']:.0f} "
              f"(relative: {list_analysis['position']['relative_y']:.2f})")
        print(f"    Size: {list_analysis['dimensions']['width']:.0f}x"
              f"{list_analysis['dimensions']['height']:.0f}")
        print(f"    Area ratio: {list_analysis['dimensions']['area_ratio']:.3f}")
        print(f"    Aspect ratio: {list_analysis['dimensions']['aspect_ratio']:.1f}")
        print(f"    Content guess: {list_analysis['likely_content']}")
    
    # Test with adjusted weights for likely abstracts
    print("\n" + "="*70)
    print("Testing with abstract-aware weighting...")
    print("="*70)
    
    # Custom weight function that penalizes Lists that look like abstracts
    def abstract_aware_weight(box):
        base_weight = calculate_box_weight(box)
        
        # Check if this List might be an abstract
        if box.label == "List":
            analysis = analyze_box_content(box, page_image)
            if analysis['likely_content'] == "likely_abstract":
                # Penalize by 40%
                print(f"  Penalizing List box {box.id} (likely abstract)")
                return base_weight * 0.6
        
        return base_weight
    
    # Apply the custom logic
    from src.injestion.agent.merge_boxes import merge_overlapping_boxes
    
    # First merge same-type boxes
    merged = merge_overlapping_boxes(original_boxes, iou_threshold=0.1)
    
    # Then resolve conflicts with abstract awareness
    final_boxes = []
    processed = set()
    
    # Sort by abstract-aware weight
    weighted_boxes = [(i, box, abstract_aware_weight(box)) for i, box in enumerate(merged)]
    weighted_boxes.sort(key=lambda x: x[2], reverse=True)
    
    for idx, (i, box1, weight1) in enumerate(weighted_boxes):
        if i in processed:
            continue
            
        conflicts_found = []
        for j, box2, weight2 in weighted_boxes[idx+1:]:
            if j in processed or box1.label == box2.label:
                continue
                
            overlap = get_overlap_area(box1.bbox, box2.bbox)
            area2 = get_box_area(box2.bbox)
            
            if area2 > 0 and overlap / area2 > 0.7:
                conflicts_found.append(j)
        
        final_boxes.append(box1)
        processed.add(i)
        processed.update(conflicts_found)
    
    print(f"\nFinal result: {len(final_boxes)} boxes")
    
    # Check what survived in potential abstract areas
    for box in final_boxes:
        analysis = analyze_box_content(box, page_image)
        if analysis['likely_content'] in ['likely_abstract', 'likely_true_list']:
            print(f"  {box.label} in abstract area: {analysis['likely_content']}")
    
    # Create visualization
    output_dir = Path("abstract_detection_results")
    output_dir.mkdir(exist_ok=True)
    
    # Visualize the analysis
    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    ax.imshow(page_image)
    ax.set_title('Abstract Detection Analysis', fontsize=14)
    ax.axis('off')
    
    # Draw boxes with analysis
    color_map = {
        'Text': 'blue',
        'Title': 'red', 
        'List': 'green',
        'Table': 'purple',
        'Figure': 'orange'
    }
    
    for box in original_boxes:
        analysis = analyze_box_content(box, page_image)
        x1, y1, x2, y2 = box.bbox
        width = x2 - x1
        height = y2 - y1
        
        color = color_map.get(box.label, 'gray')
        
        # Special styling for likely abstracts
        if analysis['likely_content'] == 'likely_abstract':
            linestyle = '--'
            linewidth = 3
        else:
            linestyle = '-'
            linewidth = 2
        
        rect = Rectangle((x1, y1), width, height,
                        linewidth=linewidth, edgecolor=color,
                        facecolor='none', alpha=0.7, linestyle=linestyle)
        ax.add_patch(rect)
        
        # Label
        label_text = f"{box.label}\n{analysis['likely_content']}"
        ax.text(x1, y1-5, label_text,
                fontsize=8, color=color, weight='bold',
                bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.7))
    
    plt.tight_layout()
    plt.savefig(output_dir / "abstract_analysis.png", dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"\nVisualization saved to {output_dir}/")


if __name__ == "__main__":
    test_abstract_detection()