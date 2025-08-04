"""Default configuration values for scientific document processing.

Optimized for academic papers, clinical studies, and research documents.
Uses PubLayNet model with functional consolidation approach.
"""

# Cache and Output
CACHE_DIR = "data/scientific_cache"

# PDF Processing
DETECTION_DPI = 400  # Balance between quality and speed

# Layout Detection (PubLayNet specific)
SCORE_THRESHOLD = 0.2  # Conservative threshold for academic documents
NMS_THRESHOLD = 0.5    # Non-maximum suppression threshold

# Box Processing (Functional approach)
EXPAND_BOXES = True     # Prevent text cutoffs common in PDFs
BOX_PADDING = 5.0       # Pixels to expand in each direction

# Overlap Resolution (Scientific functional consolidation)
MERGE_OVERLAPPING = True          # Apply overlap resolution
MERGE_THRESHOLD = 0.1             # IoU threshold for merging same-type boxes
CONFIDENCE_WEIGHT = 0.7           # Weight for confidence in conflict resolution  
AREA_WEIGHT = 0.3                 # Weight for box area in conflict resolution
MINOR_OVERLAP_THRESHOLD = 0.10    # Overlaps below this are kept

# Text Processing
APPLY_TEXT_PROCESSING = True  # Apply medical-aware text cleaning

# Debug and Visualization
CREATE_VISUALIZATIONS = True      # Create layout visualizations
SAVE_INTERMEDIATE_STATES = False  # Save raw/merged layouts for debugging