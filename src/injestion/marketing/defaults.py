"""Default configuration values for marketing document processing.

Optimized for marketing materials, brochures, and complex layouts.
Uses PrimaLayout model with advanced box consolidation.
"""

# Cache and Output
CACHE_DIR = "data/marketing_cache"

# PDF Processing  
DETECTION_DPI = 400  # Balance between quality and speed

# Layout Detection (PrimaLayout specific)
SCORE_THRESHOLD = 0.15  # Lower to catch subtle design elements
NMS_THRESHOLD = 0.4     # Less aggressive NMS for marketing layouts

# Box Processing (Object-based approach)
EXPAND_BOXES = True       # Fix text cutoffs
BOX_PADDING = 10.0        # More padding for marketing elements

# Box Consolidation (Marketing-specific advanced merging)
MERGE_OVERLAPPING = True   # Apply advanced consolidation
MERGE_THRESHOLD = 0.2      # More aggressive merging for fragmented text

# Text Processing
APPLY_TEXT_PROCESSING = True  # Apply standard text processing

# Debug and Visualization
CREATE_VISUALIZATIONS = True      # Create layout visualizations
SAVE_INTERMEDIATE_STATES = False  # Save raw/merged layouts for debugging