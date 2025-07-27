#!/usr/bin/env python3
"""Test improved refinement that better handles list structures"""

import json
from pathlib import Path
from pdf2image import convert_from_path
from src.injestion.layout_pipeline import LayoutDetectionPipeline
from src.injestion.agent.refine_layout import Box, RefinedPage
from src.injestion.agent.llm_client_chat import call_llm
import uuid

# Better prompt that handles lists properly
IMPROVED_PROMPT = """You are a document layout expert analyzing PDF layout detection results.

CRITICAL RULES FOR LISTS:
1. If you see a large "List" bounding box containing multiple "Text" elements, these Text elements are likely individual list items
2. Each list item should have its own bounding box - do NOT create one large box for the entire list
3. Change the label of Text elements within a List region to "ListItem" if they appear to be list items
4. Remove overly broad List boxes that span entire columns or large regions

Your tasks:
1. Review all detected elements and their relationships
2. For elements labeled "List" with very large bounding boxes, check if there are Text elements inside
3. Convert those inner Text elements to "ListItem" with their original bounding boxes
4. Remove the overly broad List box
5. Merge only elements that are truly part of the same paragraph
6. Establish reading order

Return JSON matching this schema:
{
  "boxes": [{"id": "string", "bbox": [x1, y1, x2, y2], "label": "string", "score": 0-1}],
  "reading_order": ["id1", "id2", ...]
}

Valid labels: Text, Title, ListItem, Table, Figure"""

def test_improved_refinement():
    """Test refinement with better list handling"""
    pdf_path = Path("Liu et al. (2024).pdf")
    
    print("Testing improved layout refinement...")
    
    # Get raw detections
    pipeline = LayoutDetectionPipeline()
    layouts = pipeline.process_pdf(pdf_path)
    
    # Convert first page to image
    images = convert_from_path(pdf_path, first_page=1, last_page=1)
    page_image = images[0]  # This is already a PIL Image
    
    # Convert first page layout to Box format
    page_layout = layouts[0]
    boxes = [
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
    
    # Prepare the input with better context
    boxes_data = [
        {
            "id": b.id,
            "bbox": list(b.bbox),
            "label": b.label,
            "score": b.score
        }
        for b in boxes
    ]
    
    user_prompt = f"""
Detected boxes:
{json.dumps(boxes_data, indent=2)}

Analyze these boxes carefully. Note that there are overlapping List boxes with Text elements inside them.
The Text elements within List regions are likely individual list items and should be labeled as "ListItem".
Remove any overly broad List boxes and keep the individual items with proper labels.
"""
    
    # Get cropped images for each box
    image_blocks = [
        {"type": "image_url", "url": _crop_to_data_url(b.bbox, page_image), "detail": "low"}
        for b in boxes
    ]
    
    input_blocks = [
        {"type": "text", "text": user_prompt},
        *image_blocks,
    ]
    
    print(f"\nCalling GPT-4 with improved prompt...")
    
    try:
        reply = call_llm(
            system_prompt=IMPROVED_PROMPT,
            user_content=input_blocks,
            model="gpt-4o-mini",
            temperature=0.3,
        )
        
        refined = RefinedPage.model_validate_json(reply)
        
        print(f"\nImproved refinement complete!")
        print(f"Elements: {len(boxes)} → {len(refined.boxes)}")
        
        # Analyze the results
        label_counts = {}
        for box in refined.boxes:
            label_counts[box.label] = label_counts.get(box.label, 0) + 1
        
        print("\nElement types after refinement:")
        for label, count in sorted(label_counts.items()):
            print(f"  {label}: {count}")
        
        # Save results
        with open("improved_refinement_results.json", "w") as f:
            json.dump({
                "original_count": len(boxes),
                "refined_count": len(refined.boxes),
                "label_distribution": label_counts,
                "boxes": [
                    {
                        "id": box.id,
                        "label": box.label,
                        "bbox": list(box.bbox),
                        "score": box.score
                    }
                    for box in refined.boxes
                ],
                "reading_order": refined.reading_order
            }, f, indent=2)
        
        print("\nResults saved to improved_refinement_results.json")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

def _crop_to_data_url(bbox, page_image):
    """Helper to crop and encode image region"""
    import base64
    import io
    
    x1, y1, x2, y2 = map(int, bbox)
    # page_image is already a PIL Image from pdf2image
    crop = page_image.crop((x1, y1, x2, y2))
    buf = io.BytesIO()
    crop.save(buf, format="PNG")
    encoded = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{encoded}"

if __name__ == "__main__":
    test_improved_refinement()