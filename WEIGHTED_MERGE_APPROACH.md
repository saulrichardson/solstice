# Weighted Merge Approach (Approach 4)

## Overview

The weighted merge approach is now the default method for processing PDFs without LLM refinement. It provides the best balance between merging overlapping detections and resolving conflicts intelligently.

## How It Works

### Step 1: Same-Type Merging
First, boxes of the same type that overlap are merged together:
- Multiple overlapping Text boxes → Single Text box
- Multiple overlapping List boxes → Single List box

### Step 2: Weighted Conflict Resolution
When the merging creates new overlaps between different types (e.g., Text vs List), conflicts are resolved using a weighted scoring system:

```
Weight Score = (0.7 × Confidence) + (0.3 × Normalized Area)
```

The box with the higher weight score wins the conflict.

## Why This Approach?

### Problem with Simple Priority
The type-based priority approach (List > Text) can preserve incorrect detections:
- If an abstract is wrongly detected as "List", it would always win
- No consideration of detection confidence

### Benefits of Weighted Scoring
- **Confidence matters**: A high-confidence Text detection can beat a low-confidence List
- **Area matters**: Larger boxes get slight preference (often more important content)
- **Balanced**: Not purely one factor, but a combination

## Usage

### Default Usage
```python
from src.injestion.pipeline_simple import ingest_pdf_simple

# Uses weighted resolution by default
pages = ingest_pdf_simple("document.pdf")
```

### Customization Options
```python
# Adjust the overlap threshold for merging
pages = ingest_pdf_simple(
    "document.pdf",
    overlap_threshold=0.3  # More aggressive merging
)

# Use different conflict resolution
pages = ingest_pdf_simple(
    "document.pdf",
    conflict_resolution="priority"  # Use type hierarchy instead
)

# Disable conflict resolution
pages = ingest_pdf_simple(
    "document.pdf",
    resolve_conflicts=False  # Just merge, don't resolve conflicts
)
```

## Comparison with Other Approaches

| Approach | Boxes | Conflicts | Behavior |
|----------|-------|-----------|----------|
| No merging | 12 | 9 | All original detections, many overlaps |
| Simple merge | 7 | 1 | Merges same-type, creates Text-List conflict |
| Priority resolution | 6 | 0 | List always wins over Text |
| **Weighted resolution** | 6 | 0 | **Best score wins (confidence + area)** |

## When to Use Each Strategy

- **weighted** (default): Best for most documents
- **priority**: When type hierarchy is reliable
- **confident**: When confidence scores are very reliable
- **larger**: When larger boxes are typically more important
- **No resolution**: When you want to handle conflicts manually

## Technical Details

### Weight Calculation
```python
def calculate_box_weight(box, confidence_weight=0.7, area_weight=0.3):
    area = (box.bbox[2] - box.bbox[0]) * (box.bbox[3] - box.bbox[1])
    normalized_area = min(area / (2000 * 2000), 1.0)  # Assume ~2000x2000 page
    
    score = (box.score * confidence_weight) + (normalized_area * area_weight)
    return score
```

### Conflict Resolution
1. Sort all boxes by weight score (highest first)
2. Process each box in order
3. If a box significantly overlaps (>70%) with a lower-weight box of different type:
   - Keep the higher-weight box
   - Remove the lower-weight box
4. Result: No cross-type overlaps remain

## Future Enhancements

Potential improvements to the weighted approach:
1. **Type-specific adjustments**: Penalize types that are often wrong
2. **Position-based weights**: Consider where on the page the box appears
3. **Aspect ratio considerations**: Wide boxes in abstract area might be Text, not List
4. **Machine learning**: Learn optimal weights from labeled data