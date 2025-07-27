"""
DPI-safe ingestion wrapper that ensures consistent handling throughout the pipeline.

This module provides a high-level interface that automatically handles DPI 
consistency and provides built-in visualization capabilities.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Union, List, Dict, Any
import logging

from .pipeline import ingest_pdf
from .layout_pipeline import LayoutDetectionPipeline
from .agent.refine_layout import RefinedPage
from .utils.visualization import LayoutVisualizer, add_dpi_metadata_to_results

logger = logging.getLogger(__name__)


class SafeIngestionPipeline:
    """DPI-safe wrapper for the complete ingestion pipeline."""
    
    def __init__(self, detection_dpi: int = 200):
        """
        Initialize safe ingestion pipeline.
        
        Args:
            detection_dpi: DPI for all detection operations (default: 200)
        """
        self.detection_dpi = detection_dpi
        self.visualizer = LayoutVisualizer(detection_dpi=detection_dpi)
        logger.info(f"Initialized SafeIngestionPipeline with DPI: {detection_dpi}")
    
    def process_pdf(
        self, 
        pdf_path: Union[str, Path],
        use_llm_refinement: bool = True,
        save_results: Optional[Union[str, Path]] = None,
        save_visualizations: bool = False,
        visualization_dir: Optional[Union[str, Path]] = None,
        visualization_dpi: int = 150
    ) -> Union[List[RefinedPage], List[Dict[str, Any]]]:
        """
        Process PDF with guaranteed DPI consistency.
        
        Args:
            pdf_path: Path to PDF file
            use_llm_refinement: Whether to use LLM refinement (requires API key)
            save_results: Path to save JSON results (with DPI metadata)
            save_visualizations: Whether to create visualization images
            visualization_dir: Directory for visualization outputs
            visualization_dpi: DPI for visualization images (default: 150)
            
        Returns:
            List of processed pages (RefinedPage objects or dict format)
        """
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        # Process with consistent DPI
        if use_llm_refinement:
            logger.info("Processing with LLM refinement...")
            refined_pages = ingest_pdf(pdf_path, detection_dpi=self.detection_dpi)
            results = self._refined_to_dict(refined_pages)
        else:
            logger.info("Processing with detection only (no LLM)...")
            detector = LayoutDetectionPipeline(detection_dpi=self.detection_dpi)
            layouts = detector.process_pdf(pdf_path)
            results = self._layouts_to_dict(layouts)
        
        # Add DPI metadata
        results = add_dpi_metadata_to_results(results, dpi=self.detection_dpi)
        
        # Save results if requested
        if save_results:
            save_path = Path(save_results)
            with open(save_path, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"Saved results to {save_path}")
        
        # Create visualizations if requested
        if save_visualizations:
            self._create_visualizations(
                pdf_path, 
                results, 
                visualization_dir or "layout_visualizations_safe",
                visualization_dpi
            )
        
        return refined_pages if use_llm_refinement else results
    
    def visualize_results(
        self,
        pdf_path: Union[str, Path],
        results_path: Union[str, Path],
        output_dir: Union[str, Path] = "visualizations",
        visualization_dpi: int = 150,
        pages: Optional[List[int]] = None
    ) -> None:
        """
        Create visualizations from saved results with automatic DPI handling.
        
        Args:
            pdf_path: Path to original PDF
            results_path: Path to JSON results file
            output_dir: Directory for output images
            visualization_dpi: DPI for output images
            pages: Specific pages to visualize (None = all)
        """
        with open(results_path, 'r') as f:
            results = json.load(f)
        
        self._create_visualizations(
            pdf_path,
            results,
            output_dir,
            visualization_dpi,
            pages
        )
    
    def _create_visualizations(
        self,
        pdf_path: Path,
        results: Union[List, Dict],
        output_dir: Union[str, Path],
        visualization_dpi: int,
        pages: Optional[List[int]] = None
    ) -> None:
        """Create visualization images with DPI scaling."""
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        
        # Determine pages to visualize
        if isinstance(results, list):
            total_pages = len(results)
            page_list = pages or list(range(1, min(total_pages + 1, 11)))  # First 10 by default
        else:
            page_list = [1]  # Single page result
        
        for page_num in page_list:
            try:
                output_path = output_dir / f"page_{page_num:02d}.png"
                self.visualizer.visualize_layout(
                    pdf_path=pdf_path,
                    layout_data=results,
                    page_num=page_num,
                    visualization_dpi=visualization_dpi,
                    output_path=output_path
                )
                logger.info(f"Created visualization for page {page_num}")
            except Exception as e:
                logger.error(f"Failed to visualize page {page_num}: {e}")
    
    def _refined_to_dict(self, refined_pages: List[RefinedPage]) -> List[Dict[str, Any]]:
        """Convert RefinedPage objects to dictionary format."""
        results = []
        for page in refined_pages:
            page_dict = {
                "page": page.page_index + 1,
                "detection_dpi": page.detection_dpi,
                "elements": [
                    {
                        "id": box.id,
                        "type": box.label,
                        "bbox": {
                            "x1": box.bbox[0],
                            "y1": box.bbox[1],
                            "x2": box.bbox[2],
                            "y2": box.bbox[3]
                        },
                        "score": box.score
                    }
                    for box in page.boxes
                ],
                "reading_order": page.reading_order
            }
            results.append(page_dict)
        return results
    
    def _layouts_to_dict(self, layouts: List) -> List[Dict[str, Any]]:
        """Convert layoutparser results to dictionary format."""
        results = []
        for page_idx, page_layout in enumerate(layouts):
            page_dict = {
                "page": page_idx + 1,
                "detection_dpi": self.detection_dpi,
                "elements": [
                    {
                        "type": str(elem.type) if elem.type else "Unknown",
                        "bbox": {
                            "x1": float(elem.block.x_1),
                            "y1": float(elem.block.y_1),
                            "x2": float(elem.block.x_2),
                            "y2": float(elem.block.y_2)
                        },
                        "score": float(elem.score) if elem.score else 0.0
                    }
                    for elem in page_layout
                ]
            }
            results.append(page_dict)
        return results


# Convenience function for quick processing
def process_pdf_safely(
    pdf_path: Union[str, Path],
    output_dir: Union[str, Path] = "output",
    detection_dpi: int = 200,
    visualization_dpi: int = 150,
    use_llm: bool = True
) -> Path:
    """
    Process PDF with all safety features enabled.
    
    Returns:
        Path to the results JSON file
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    pipeline = SafeIngestionPipeline(detection_dpi=detection_dpi)
    
    results_path = output_dir / "results.json"
    viz_dir = output_dir / "visualizations"
    
    pipeline.process_pdf(
        pdf_path=pdf_path,
        use_llm_refinement=use_llm,
        save_results=results_path,
        save_visualizations=True,
        visualization_dir=viz_dir,
        visualization_dpi=visualization_dpi
    )
    
    print(f"Processing complete!")
    print(f"Results saved to: {results_path}")
    print(f"Visualizations saved to: {viz_dir}/")
    
    return results_path


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python safe_ingestion.py <pdf_path> [--no-llm]")
        sys.exit(1)
    
    pdf_file = sys.argv[1]
    use_llm = "--no-llm" not in sys.argv
    
    process_pdf_safely(pdf_file, use_llm=use_llm)