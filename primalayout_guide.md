# PrimaLayout Configuration Guide

## Key Tunable Parameters

### 1. **Score Threshold** (`MODEL.ROI_HEADS.SCORE_THRESH_TEST`)
- **What it does**: Minimum confidence score for a detection to be kept
- **Range**: 0.0 to 1.0
- **Effects**:
  - Lower (0.05-0.2): More detections, includes uncertain regions
  - Higher (0.5-0.8): Fewer detections, only confident ones
- **Recommended**: 0.1-0.2 for marketing documents

### 2. **NMS Threshold** (`MODEL.ROI_HEADS.NMS_THRESH_TEST`)
- **What it does**: Controls how overlapping boxes are handled
- **Range**: 0.0 to 1.0
- **Effects**:
  - Lower (0.1-0.3): Aggressive - removes more overlapping boxes
  - Higher (0.5-0.7): Permissive - keeps more overlapping boxes
- **Recommended**: 0.4-0.5 for dense layouts

### 3. **Max Detections** (`MODEL.TEST.DETECTIONS_PER_IMAGE`)
- **What it does**: Maximum number of regions detected per page
- **Default**: 100
- **When to increase**: Complex documents with many elements
- **Recommended**: 150-200 for marketing materials

## Example Configurations

### For Marketing Documents (like your Flublok PDF):
```python
model = lp.Detectron2LayoutModel(
    "lp://PrimaLayout/mask_rcnn_R_50_FPN_3x/config",
    extra_config=[
        "MODEL.ROI_HEADS.SCORE_THRESH_TEST", 0.15,  # Catch subtle text
        "MODEL.ROI_HEADS.NMS_THRESH_TEST", 0.4,     # Some overlap OK
        "MODEL.TEST.DETECTIONS_PER_IMAGE", 150      # Many elements
    ],
    label_map={
        1: "TextRegion", 
        2: "ImageRegion",
        3: "TableRegion",
        4: "MathsRegion",
        5: "SeparatorRegion",
        6: "OtherRegion"
    }
)
```

### For Clinical/Scientific Documents:
```python
model = lp.Detectron2LayoutModel(
    "lp://PrimaLayout/mask_rcnn_R_50_FPN_3x/config",
    extra_config=[
        "MODEL.ROI_HEADS.SCORE_THRESH_TEST", 0.3,   # More conservative
        "MODEL.ROI_HEADS.NMS_THRESH_TEST", 0.3,     # Less overlap
        "MODEL.TEST.DETECTIONS_PER_IMAGE", 100      # Standard
    ],
    label_map={...}
)
```

### For Dense/Complex Layouts:
```python
model = lp.Detectron2LayoutModel(
    "lp://PrimaLayout/mask_rcnn_R_50_FPN_3x/config",
    extra_config=[
        "MODEL.ROI_HEADS.SCORE_THRESH_TEST", 0.1,   # Very sensitive
        "MODEL.ROI_HEADS.NMS_THRESH_TEST", 0.6,     # Allow overlaps
        "MODEL.TEST.DETECTIONS_PER_IMAGE", 200      # Many regions
    ],
    label_map={...}
)
```

## Other Advanced Parameters

### Box Refinement
- `MODEL.ROI_BOX_HEAD.BBOX_REG_WEIGHTS`: Weights for box coordinate regression
- Default: `[10.0, 10.0, 5.0, 5.0]`
- Adjust if boxes are consistently too large/small

### Mask Generation
- `MODEL.ROI_MASK_HEAD.SCORE_THRESH_TEST`: Threshold for segmentation masks
- Only relevant if you need pixel-level masks (not just boxes)

### Architecture Settings
- `MODEL.BACKBONE.FREEZE_AT`: Which ResNet stages to freeze
- `MODEL.FPN.OUT_CHANNELS`: Feature pyramid network channels
- Generally don't need to change these

## Tips for Tuning

1. **Start with score threshold**: This has the biggest impact
2. **Visualize results**: Always check what's being detected
3. **Document-specific tuning**: Different document types need different settings
4. **Balance precision/recall**: Lower thresholds = more recall, higher = more precision

## Integration with Your Pipeline

Update your `LayoutDetectionPipeline`:

```python
class LayoutDetectionPipeline:
    DEFAULT_CONFIG = "lp://PrimaLayout/mask_rcnn_R_50_FPN_3x/config"  # Changed!
    
    def __init__(self, score_threshold=0.15, nms_threshold=0.4):
        self._score_threshold = score_threshold
        self._nms_threshold = nms_threshold
        
    def _ensure_model(self):
        self._model = lp.Detectron2LayoutModel(
            self.DEFAULT_CONFIG,
            extra_config=[
                "MODEL.ROI_HEADS.SCORE_THRESH_TEST", self._score_threshold,
                "MODEL.ROI_HEADS.NMS_THRESH_TEST", self._nms_threshold,
            ],
            label_map={
                1: "TextRegion",
                2: "ImageRegion", 
                3: "TableRegion",
                4: "MathsRegion",
                5: "SeparatorRegion",
                6: "OtherRegion"
            }
        )
```