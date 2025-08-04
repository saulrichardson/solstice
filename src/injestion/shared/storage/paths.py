"""Local disk storage helpers shared across ingestion stages.

All derived artefacts are stored below the project-level ``data/`` directory
using the structure::

    data/
      raw/               # (optional) original PDFs copied here
      scientific_cache/
        <doc>/pages/     page-NNN.png
        <doc>/layout/    layout.json
        <doc>/raw_layouts/    raw_layout_boxes.json
                              visualizations/  page_NNN_raw_layout.png
        <doc>/merged/    merged_boxes.json
        <doc>/reading_order/  reading_order.json
        <doc>/extracted/ content.json, figures/

Where ``<doc>`` is the sanitized PDF filename (without extension). Special 
characters are replaced with underscores to ensure filesystem compatibility.
If the filename is empty or invalid, falls back to using the first 8 
characters of the SHA-256 hash.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Root directories (created lazily when first used)
# ---------------------------------------------------------------------------


_DATA_DIR = Path(__file__).resolve().parents[3] / "data"

# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def ensure_dirs() -> None:
    """Create *data* root folders if they do not yet exist."""

    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def doc_id(pdf_path: os.PathLike | str) -> str:
    """Return a sanitized version of the PDF filename without extension."""
    
    path = Path(pdf_path)
    # Get filename without extension
    filename = path.stem
    
    # Sanitize filename: replace problematic characters with underscore
    # Keep alphanumeric, dash, underscore, and dot
    import re
    sanitized = re.sub(r'[^\w\-.]', '_', filename)
    
    # Ensure the derived identifier is safe.  When the *sanitised* filename is
    # empty (happens for paths like ``/tmp/.pdf``) **or** still begins with a
    # dot, we fall back to a stable eight-character prefix of a SHA-256 hash
    # rather than returning an illegal directory name.  The preferred source
    # for that hash is the *file contents* – it guarantees uniqueness for
    # different, but equally named, temporary files.
    #
    # However, callers frequently use :func:`doc_id` for *non-existing* paths
    # (e.g. to calculate where artefacts *will* be written later on).  Trying
    # to read such a file would raise *FileNotFoundError* and therefore break
    # perfectly valid workflows.  To make the helper robust we gracefully
    # fall back to hashing the *string representation* of the path when the
    # file is not yet available.
    if not sanitized or sanitized.startswith('.'):
        h = hashlib.sha256()

        try:
            with open(pdf_path, "rb") as fh:  # type: ignore[arg-type]
                for chunk in iter(lambda: fh.read(65536), b""):
                    h.update(chunk)
        except FileNotFoundError:
            # Use the path itself as a reasonably unique source – we still get
            # deterministic output for identical inputs and avoid blowing up
            # when the file is created later on in the pipeline.
            h.update(str(pdf_path).encode())

        return h.hexdigest()[:8]
    
    return sanitized


def stage_dir(stage: str, pdf_path: os.PathLike | str, cache_dir: os.PathLike | str) -> Path:
    """Return the cache directory for *stage* and *pdf_path* (created)."""

    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    directory = cache_dir / doc_id(pdf_path) / stage
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def pages_dir(pdf_path: os.PathLike | str, cache_dir: os.PathLike | str) -> Path:
    """Directory where rasterised page images are stored."""

    return stage_dir("pages", pdf_path, cache_dir)


def extracted_content_path(pdf_path: os.PathLike | str, cache_dir: os.PathLike | str) -> Path:
    """Path to the final extracted content JSON for *pdf_path*."""
    
    return stage_dir("extracted", pdf_path, cache_dir) / "content.json"


# ---------------------------------------------------------------------------
# Tiny JSON helpers (no external deps)
# ---------------------------------------------------------------------------


def save_json(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())
