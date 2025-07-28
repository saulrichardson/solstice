"""Detect high-level layout regions on page images using LayoutParser.

This module provides a single entrypoint that takes PIL images as input and
returns detected layout boxes. No PDF or rasterization logic is included here.

Typical usage:
    from injestion.processing.layout_detector import LayoutDetectionPipeline
    pipeline = LayoutDetectionPipeline()
    layouts = pipeline.detect_images(images)

Each element in `layouts` is a list of `layoutparser.Layout` objects for the
corresponding page image.
"""

from __future__ import annotations

from typing import Iterable, List, Sequence
import layoutparser as lp


class LayoutDetectionPipeline:
    """Detect high-level layout regions on each page image."""

    #: Default mask RCNN model trained on PubLayNet
    DEFAULT_CONFIG: str = "lp://PubLayNet/mask_rcnn_R_50_FPN_3x/config"

    def __init__(
        self,
        model: lp.LayoutModel | None = None,
        score_threshold: float = 0.5,
    ):
        """Initialize pipeline with an optional preloaded model.

        Parameters
        ----------
        model
            Pre-initialized LayoutParser model instance. If None, a default
            PubLayNet model is loaded lazily on first use.
        score_threshold
            Minimum confidence threshold for detections.
        """
        self._model = model
        self._score_threshold = score_threshold

    def detect_images(self, images: Iterable) -> List[Sequence[lp.Layout]]:
        """Run layout detection on a sequence of page images."""
        model = self._ensure_model()
        return [model.detect(image) for image in images]

    def _ensure_model(self) -> lp.LayoutModel:
        if self._model is None:
            # Lazy import to avoid forcing torch/detectron2 on import.
            self._model = lp.Detectron2LayoutModel(
                self.DEFAULT_CONFIG,
                extra_config=[
                    "MODEL.ROI_HEADS.SCORE_THRESH_TEST",
                    self._score_threshold,
                ],
                label_map={
                    0: "Text",
                    1: "Title",
                    2: "List",
                    3: "Table",
                    4: "Figure",
                },
            )
        return self._model

