# Injestion Directory Analysis

## Currently Used in Main Pipeline (`pipeline.py`)

### Core Components:
- `layout_pipeline.py` - LayoutDetectionPipeline (detectron2 wrapper)
- `document.py` - Block, Document models
- `storage.py` - File system organization
- `visualize_layout.py` - Visualization functionality
- `agent/merge_boxes_weighted.py` - smart_merge_and_resolve function
- `agent/refine_layout.py` - Box class only (not the LLM refinement)

## Multiple Pipeline Versions (Redundant/Confusing)

### Catalog Pipelines (5 versions!):
- `catalog_pipeline.py` - V1
- `catalog_pipeline_v2.py` - Added text extraction
- `catalog_pipeline_v3.py` - Fixed coordinate conversion
- `catalog_pipeline_v4.py` - Unknown improvements
- `catalog_pipeline_v5.py` - Full-page text extraction
- `catalog_pipeline_complete.py` - Uses weighted merging
- `catalog_pipeline_final.py` - Another "final" version

### Other Pipeline Variants:
- `pipeline_simple.py` - Uses refine_layout_simple
- `pipeline_vision.py` - Adds caption association
- `pipeline_extraction.py` - Has column detection (we copied from here!)
- `pipeline_extraction_vision.py` - Extraction + vision
- `complete_pipeline.py` - CompletePDFIngestionPipeline class
- `safe_ingestion.py` - Unknown safety wrapper

## Agent Components (Mixed LLM/Non-LLM)

### LLM-Based (Not needed anymore):
- `agent/refine_layout.py` - LLM refinement (REMOVED from pipeline)
- `agent/refine_layout_simple.py` - Simpler LLM refinement
- `agent/llm_client.py` - OpenAI client
- `agent/llm_client_chat.py` - Chat-based client
- `agent/caption_association.py` - LLM caption association
- `agent/caption_association_vision.py` - Vision-based caption

### Non-LLM (Still useful):
- `agent/merge_boxes.py` - Basic box merging
- `agent/merge_boxes_advanced.py` - Advanced merging
- `agent/merge_boxes_weighted.py` - Weighted merging (USED)
- `agent/visual_reordering.py` - Column-based ordering
- `agent/visual_reordering_agent.py` - Simple reordering (PARTIALLY USED)

## Extractors (For downstream text extraction):
- `extractors/component_extractors.py` - Routes to appropriate extractor
- `extractors/tatr_extractor.py` - Table structure extraction
- `extractors/table_formatter.py` - Table formatting

## Utilities:
- `catalog_utils.py` - Catalog reader/exporter
- `utils/visualization.py` - Unknown vis utils
- `visualizers/catalog_visualizer.py` - Catalog-specific viz
- `visualizers/simple_layout_viewer.py` - Simple viewer

## Recommendations:

### Keep (Essential):
1. `pipeline.py` - Main pipeline (our work)
2. `layout_pipeline.py` - Core detection
3. `document.py` - Data models
4. `storage.py` - File organization
5. `visualize_layout.py` - Visualization
6. `agent/merge_boxes*.py` - Box merging logic
7. `extractors/*` - For text extraction phase

### Consider Removing/Archiving:
1. All catalog pipeline versions (7 files!) - consolidate to one
2. All alternative pipeline versions - confusing
3. LLM agent components - no longer used
4. `safe_ingestion.py` - unclear purpose
5. `complete_pipeline.py` - redundant

### Refactor:
1. Move non-LLM utilities out of `agent/` directory
2. Consolidate visualization code
3. Create clear separation between:
   - Layout detection
   - Box processing (merging, ordering)
   - Text extraction
   - Visualization

## Directory Structure Proposal:
```
src/injestion/
├── __init__.py
├── pipeline.py              # Main entry point
├── core/
│   ├── detection.py        # Layout detection
│   ├── document.py         # Data models
│   └── storage.py          # File management
├── processing/
│   ├── merge_boxes.py      # All merging strategies
│   └── ordering.py         # Reading order logic
├── extraction/
│   ├── text_extractor.py   # Text extraction
│   └── table_extractor.py  # Table extraction
└── visualization/
    └── layout_viz.py       # All viz functionality
```