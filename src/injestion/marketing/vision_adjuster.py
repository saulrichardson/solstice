"""Vision LLM-based layout adjustment for marketing documents."""

from __future__ import annotations

import os
import json
from typing import List, Sequence, Dict, Any, Tuple
from dataclasses import dataclass, field
from PIL import Image
import layoutparser as lp
from openai import OpenAI


@dataclass
class MergeOperation:
    """Merge multiple layout boxes into one."""
    box_indices: List[int]
    new_type: str | None = None
    reason: str = ""


@dataclass
class ReclassifyOperation:
    """Change the type/label of a box."""
    box_index: int
    new_type: str
    reason: str = ""


@dataclass
class AdjustmentPlan:
    """Collection of adjustments to apply to layout."""
    merges: List[MergeOperation] = field(default_factory=list)
    reclassifications: List[ReclassifyOperation] = field(default_factory=list)


class MarketingVisionAdjuster:
    """Adjust layout detection results using vision LLM for marketing documents."""
    
    def __init__(self, vision_model: str = "gpt-4o", api_key: str | None = None):
        """Initialize with OpenAI vision model.
        
        Parameters
        ----------
        vision_model
            OpenAI model to use (must support vision)
        api_key
            OpenAI API key. If None, uses OPENAI_API_KEY env var
        """
        self.vision_model = vision_model
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        
    def adjust_layouts(
        self, 
        layouts: List[Sequence[lp.Layout]], 
        images: List[Image.Image]
    ) -> List[Sequence[lp.Layout]]:
        """Adjust layouts using vision LLM analysis.
        
        Parameters
        ----------
        layouts
            Layout detection results from detector
        images
            Original page images
            
        Returns
        -------
        Adjusted layouts with improved grouping and classification
        """
        adjusted_layouts = []
        
        for page_idx, (layout, image) in enumerate(zip(layouts, images)):
            # Generate adjustment plan using vision LLM
            plan = self._generate_adjustment_plan(layout, image)
            
            # Apply adjustments
            adjusted_layout = self._apply_adjustments(layout, plan)
            adjusted_layouts.append(adjusted_layout)
            
        return adjusted_layouts
    
    def _generate_adjustment_plan(
        self, 
        layout: Sequence[lp.Layout], 
        image: Image.Image
    ) -> AdjustmentPlan:
        """Use vision LLM to analyze and suggest adjustments."""
        
        # Serialize layout for LLM
        boxes_data = []
        for idx, box in enumerate(layout):
            boxes_data.append({
                "index": idx,
                "type": str(box.type),
                "bbox": [box.block.x_1, box.block.y_1, box.block.x_2, box.block.y_2],
                "score": float(box.score)
            })
        
        # Prepare prompt
        prompt = self._get_marketing_prompt(boxes_data)
        
        # Call vision API
        response = self.client.chat.completions.create(
            model=self.vision_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": self._image_to_base64(image)
                            }
                        }
                    ]
                }
            ],
            temperature=0.1,
            max_tokens=1000
        )
        
        # Parse response into adjustment plan
        return self._parse_adjustments(response.choices[0].message.content)
    
    def _get_marketing_prompt(self, boxes_data: List[Dict]) -> str:
        """Generate prompt for marketing document analysis."""
        return f"""Analyze this marketing document layout. I've detected {len(boxes_data)} regions.

Current detections:
{json.dumps(boxes_data, indent=2)}

Please identify:
1. Icon-text pairs that should be grouped together
2. Marketing headers vs body text vs disclaimers
3. Any misclassified regions (e.g., text detected as images)
4. Visual groupings that represent features or benefits

Return a JSON object with:
{{
    "merges": [
        {{
            "box_indices": [list of indices to merge],
            "new_type": "TextRegion" or other type,
            "reason": "why these should be merged"
        }}
    ],
    "reclassifications": [
        {{
            "box_index": index,
            "new_type": "new type",
            "reason": "why reclassify"
        }}
    ]
}}

Focus on making the layout semantically meaningful for downstream processing."""

    def _parse_adjustments(self, response: str) -> AdjustmentPlan:
        """Parse LLM response into adjustment plan."""
        try:
            # Extract JSON from response
            start = response.find("{")
            end = response.rfind("}") + 1
            json_str = response[start:end]
            data = json.loads(json_str)
            
            plan = AdjustmentPlan()
            
            # Parse merges
            for merge_data in data.get("merges", []):
                plan.merges.append(MergeOperation(
                    box_indices=merge_data["box_indices"],
                    new_type=merge_data.get("new_type"),
                    reason=merge_data.get("reason", "")
                ))
            
            # Parse reclassifications
            for reclass_data in data.get("reclassifications", []):
                plan.reclassifications.append(ReclassifyOperation(
                    box_index=reclass_data["box_index"],
                    new_type=reclass_data["new_type"],
                    reason=reclass_data.get("reason", "")
                ))
                
            return plan
            
        except Exception as e:
            print(f"Failed to parse adjustments: {e}")
            return AdjustmentPlan()  # Return empty plan on error
    
    def _apply_adjustments(
        self, 
        layout: Sequence[lp.Layout], 
        plan: AdjustmentPlan
    ) -> Sequence[lp.Layout]:
        """Apply adjustment plan to layout."""
        
        # Convert to list for manipulation
        layout_list = list(layout)
        
        # Track indices to remove after merging
        indices_to_remove = set()
        
        # Apply merges first
        for merge in plan.merges:
            if not merge.box_indices:
                continue
                
            # Get boxes to merge
            boxes_to_merge = [layout_list[i] for i in merge.box_indices 
                             if i < len(layout_list)]
            
            if len(boxes_to_merge) < 2:
                continue
            
            # Calculate merged bounding box
            x1 = min(box.block.x_1 for box in boxes_to_merge)
            y1 = min(box.block.y_1 for box in boxes_to_merge)
            x2 = max(box.block.x_2 for box in boxes_to_merge)
            y2 = max(box.block.y_2 for box in boxes_to_merge)
            
            # Create merged box
            merged_block = lp.Rectangle(x1, y1, x2, y2)
            merged_type = merge.new_type or boxes_to_merge[0].type
            avg_score = sum(box.score for box in boxes_to_merge) / len(boxes_to_merge)
            
            merged_element = lp.Layout([lp.TextBlock(
                merged_block,
                type=merged_type,
                score=avg_score
            )])
            
            # Replace first box with merged, mark others for removal
            first_idx = merge.box_indices[0]
            layout_list[first_idx] = merged_element[0]
            indices_to_remove.update(merge.box_indices[1:])
        
        # Remove merged boxes
        layout_list = [box for i, box in enumerate(layout_list) 
                      if i not in indices_to_remove]
        
        # Apply reclassifications
        for reclass in plan.reclassifications:
            if reclass.box_index < len(layout_list):
                box = layout_list[reclass.box_index]
                # Create new box with updated type
                new_box = lp.TextBlock(
                    box.block,
                    type=reclass.new_type,
                    score=box.score
                )
                layout_list[reclass.box_index] = new_box
        
        return lp.Layout(layout_list)
    
    def _image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL image to base64 for API."""
        import io
        import base64
        
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        image_data = buffer.getvalue()
        return f"data:image/png;base64,{base64.b64encode(image_data).decode()}"