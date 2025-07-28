"""Document ingestion utilities.

This package provides PDF processing pipelines:

1. Catalog-based approach (RECOMMENDED):
   - Creates an index of all elements without extracting
   - Agents extract content on-demand
   - More efficient and flexible

2. Full extraction approach:
   - Extracts everything upfront
   - Good for simple use cases
"""

from .layout_pipeline import LayoutDetectionPipeline  # noqa: F401
from .complete_pipeline import CompletePDFIngestionPipeline, run_pipeline  # noqa: F401
from .catalog_pipeline import (  # noqa: F401
    PDFElementCatalog,
    OnDemandExtractor,
    SelectiveExtractionAgent,
    create_catalog
)
from .catalog_pipeline_v2 import (  # noqa: F401
    PDFElementCatalogV2,
    create_catalog_v2
)
from .catalog_pipeline_v3 import (  # noqa: F401
    PDFElementCatalogV3,
    create_catalog_v3
)
from .agent.visual_reordering_agent import VisualReorderingAgent  # noqa: F401

__all__ = [
    # Core components
    "LayoutDetectionPipeline",
    "VisualReorderingAgent",
    
    # Full extraction approach
    "CompletePDFIngestionPipeline",
    "run_pipeline",
    
    # Catalog-based approach (recommended)
    "PDFElementCatalog",
    "OnDemandExtractor", 
    "SelectiveExtractionAgent",
    "create_catalog",
    
    # Catalog V2 with text extraction
    "PDFElementCatalogV2",
    "create_catalog_v2",
    
    # Catalog V3 with fixed coordinate conversion
    "PDFElementCatalogV3",
    "create_catalog_v3",
]

# Import the complete catalog pipeline
try:
    from .catalog_pipeline_complete import (  # noqa: F401
        PDFElementCatalogComplete,
        create_catalog_complete
    )
    __all__.extend([
        "PDFElementCatalogComplete",
        "create_catalog_complete",
    ])
except ImportError:
    # If weighted merging dependencies are missing
    pass

# Import visualization components
try:
    from .visualizers import (  # noqa: F401
        CatalogVisualizer,
        create_catalog_visualization,
        create_simple_layout_view
    )
    __all__.extend([
        "CatalogVisualizer",
        "create_catalog_visualization",
        "create_simple_layout_view",
    ])
except ImportError:
    # If visualization dependencies are missing
    pass

# Import catalog utilities
try:
    from .catalog_utils import (  # noqa: F401
        CatalogReader,
        CatalogExporter,
        load_catalog,
        export_catalog_text
    )
    __all__.extend([
        "CatalogReader",
        "CatalogExporter",
        "load_catalog",
        "export_catalog_text",
    ])
except ImportError:
    # If catalog utility dependencies are missing
    pass

