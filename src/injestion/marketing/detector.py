"""Marketing-optimized layout detection using PrimaLayout."""

from __future__ import annotations

from typing import Iterable, List, Sequence
import layoutparser as lp


class MarketingLayoutDetector:
    """Layout detector optimized for marketing materials using PrimaLayout.
    
    This detector uses PrimaLayout which performs better on marketing documents
    compared to PubLayNet (which is trained on scientific papers).
    """
    
    # PrimaLayout model - trained on diverse document types
    DEFAULT_CONFIG = "lp://PrimaLayout/mask_rcnn_R_50_FPN_3x/config"
    
    # Marketing-optimized defaults
    DEFAULT_SCORE_THRESHOLD = 0.1   # Lower to catch subtle text
    DEFAULT_NMS_THRESHOLD = 0.3     # Less overlap to reduce duplicates
    DEFAULT_MAX_DETECTIONS = 150    # Marketing docs have many elements
    
    def __init__(
        self,
        model: lp.LayoutModel | None = None,
        score_threshold: float | None = None,
        nms_threshold: float | None = None,
        max_detections: int | None = None,
    ):
        """Initialize detector with marketing-optimized settings.
        
        Parameters
        ----------
        model
            Pre-initialized LayoutParser model. If None, PrimaLayout is loaded.
        score_threshold
            Minimum confidence for detections. Lower = more sensitive.
        nms_threshold
            Non-maximum suppression threshold. Higher = more overlaps allowed.
        max_detections
            Maximum detections per page.
        """
        self._model = model
        self._score_threshold = score_threshold or self.DEFAULT_SCORE_THRESHOLD
        self._nms_threshold = nms_threshold or self.DEFAULT_NMS_THRESHOLD
        self._max_detections = max_detections or self.DEFAULT_MAX_DETECTIONS
        
    def detect_images(self, images: Iterable) -> List[Sequence[lp.Layout]]:
        """Run layout detection on page images.
        
        Parameters
        ----------
        images
            Iterable of PIL images (one per page)
            
        Returns
        -------
        List of Layout objects for each page
        
        Raises
        ------
        RuntimeError
            If model initialization fails
        ValueError
            If images are invalid
        """
        try:
            model = self._ensure_model()
            results = []
            for i, image in enumerate(images):
                if image is None:
                    raise ValueError(f"Image at index {i} is None")
                results.append(model.detect(image))
            return results
        except Exception as e:
            raise RuntimeError(f"Layout detection failed: {e}") from e
    
    def _ensure_model(self) -> lp.LayoutModel:
        """Lazy load the PrimaLayout model with marketing-optimized config."""
        if self._model is None:
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
        return self._model