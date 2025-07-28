"""Pipeline helpers for detecting page layout regions in PDF documents.

The classes defined here wrap *LayoutParser* so that the rest of the codebase
does not have to depend on the external API directly.  At the moment we only
support the object-detection (bounding-box) stage – no OCR is attempted.

Typical usage
-------------
>>> from injestion.layout_pipeline import LayoutDetectionPipeline
>>> pipeline = LayoutDetectionPipeline()
>>> layouts = pipeline.process_pdf("/path/to/document.pdf")
Each element in *layouts* is a list of `layoutparser.Layout` objects for the
corresponding page.

The default model is the Detectron2 implementation trained on the PubLayNet
dataset which generally works well on scientific articles and business
documents.  You can swap it out by passing another LayoutParser LayoutModel
instance to the constructor.
"""

from __future__ import annotations

import pathlib
import tempfile
from typing import Iterable, List, Sequence

import layoutparser as lp
from pdf2image import convert_from_path

# NOTE: importing torch/detectron2 is intentionally delayed until the model is
# instantiated so that simply importing this module does not require a full
# deep-learning stack.  That keeps "light" tooling such as documentation builds
# functional even if CUDA / Detectron2 wheels are unavailable.


class LayoutDetectionPipeline:
    """Detect high-level layout regions on each page of a PDF document."""

    #: Using the standard mask_rcnn_R_50_FPN_3x model for reliability
    DEFAULT_CONFIG: str = "lp://PubLayNet/mask_rcnn_R_50_FPN_3x/config"
    
    #: Default DPI for PDF to image conversion and detection
    DEFAULT_DPI: int = 200

    def __init__(
        self,
        model: lp.LayoutModel | None = None,
        score_threshold: float = 0.5,
        detection_dpi: int = 200,
    ):  # noqa: D401 (simple verb phrase is fine here)
        """Create a new pipeline.

        Parameters
        ----------
        model
            Pre-initialised *layoutparser* model instance.  If *None* (the
            default) the canonical PubLayNet model is lazily instantiated when
            first used.
        score_threshold
            Minimum confidence required for a detection to be returned.  Passed
            to the Detectron2 model through the *extra_config* mechanism.
        detection_dpi
            DPI to use for PDF to image conversion. Default is 200 (pdf2image default).
            All detection coordinates will be relative to this DPI.
        """

        self._model = model  # may be None – will be created on first use
        self._score_threshold = score_threshold
        self._detection_dpi = detection_dpi

    # ---------------------------------------------------------------------
    # Public helpers
    # ---------------------------------------------------------------------

    def process_pdf(self, pdf_path: str | pathlib.Path) -> List[Sequence[lp.Layout]]:
        """Run layout detection on *pdf_path* and return results per page."""

        pdf_path = pathlib.Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(pdf_path)

        # pdf2image requires a path – we cannot stream directly from bytes
        images = list(_pdf_to_images(pdf_path, dpi=self._detection_dpi))

        model = self._ensure_model()

        layouts: List[Sequence[lp.Layout]] = []
        for image in images:
            layout = model.detect(image)
            layouts.append(layout)

        return layouts

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_model(self) -> lp.LayoutModel:
        if self._model is None:
            # Lazy import to avoid torch/detectron2 dependency during static
            # analysis or documentation builds.
            self._model = lp.Detectron2LayoutModel(  # type: ignore[assignment]
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


# -------------------------------------------------------------------------
# Utility functions
# -------------------------------------------------------------------------


def _pdf_to_images(pdf_path: pathlib.Path, dpi: int = 200) -> Iterable["Image.Image"]:  # noqa: ANN401
    """Convert *pdf_path* into a sequence of PIL images.*

    The conversion is done via the *pdf2image* library which is a thin wrapper
    around Poppler's *pdftocairo* utility.  We use `convert_from_path` instead
    of reading the PDF into memory to keep the surface small.
    
    Args:
        pdf_path: Path to PDF file
        dpi: DPI for conversion (default: 200, which is pdf2image's default)
    """

    # The Poppler stack occasionally fails when asked to read from arbitrary
    # working directories that might not be writeable.  We therefore make sure
    # that the temporary files end up in the system temp directory.
    with tempfile.TemporaryDirectory() as tmp:
        images = convert_from_path(str(pdf_path), output_folder=tmp, fmt="png", dpi=dpi)
    return images
