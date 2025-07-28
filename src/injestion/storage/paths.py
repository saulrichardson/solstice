"""Local disk storage helpers shared across ingestion stages.

All derived artefacts are stored below the project-level ``data/`` directory
using the structure::

    data/
      raw/               # (optional) original PDFs copied here
      cache/
        pages/<doc>/     page-NNN.png
        layout/<doc>/    layout.json
        raw_layouts/<doc>/    raw_layout_boxes.json
                              visualizations/  page_NNN_raw_layout.png
        merged/<doc>/    merged_boxes.json
        reading_order/<doc>/  reading_order.json
        extracted/<doc>/ content.json, figures/

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
_CACHE_DIR = _DATA_DIR / "cache"

# ---------------------------------------------------------------------------
# Runtime configuration
# ---------------------------------------------------------------------------


def set_cache_root(cache_root: os.PathLike | str) -> None:  # noqa: D401 – simple setter
    """Override the root *cache* directory at runtime.

    The ingest CLI exposes an ``--output-dir`` flag allowing users to route all
    generated artefacts to a custom location.  We keep the default behaviour
    (``data/cache``) while letting callers switch to an alternative path *before*
    the first call to :func:`stage_dir` / :func:`pages_dir` / …  However, the
    function is idempotent and can also be called later – all subsequent calls
    to the helpers will respect the new directory.

    Parameters
    ----------
    cache_root
        Destination directory where pipeline artefacts will be written.
    """

    global _CACHE_DIR  # noqa: PLW0603 – allow reassignment of module-level var

    # Convert eagerly to Path – makes later operations cheaper.
    _CACHE_DIR = Path(cache_root)

    # Make sure the directory exists so that later helper calls succeed.
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def ensure_dirs() -> None:
    """Create *data* root folders if they do not yet exist."""

    for d in (_DATA_DIR, _CACHE_DIR):
        d.mkdir(parents=True, exist_ok=True)


def doc_id(pdf_path: os.PathLike | str) -> str:
    """Return a sanitized version of the PDF filename without extension."""
    
    path = Path(pdf_path)
    # Get filename without extension
    filename = path.stem
    
    # Sanitize filename: replace problematic characters with underscore
    # Keep alphanumeric, dash, underscore, and dot
    import re
    sanitized = re.sub(r'[^\w\-.]', '_', filename)
    
    # Ensure it's not empty and doesn't start with a dot
    if not sanitized or sanitized.startswith('.'):
        # Fallback to hash if filename is problematic
        h = hashlib.sha256()
        with open(pdf_path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()[:8]
    
    return sanitized


def stage_dir(stage: str, pdf_path: os.PathLike | str) -> Path:
    """Return the cache directory for *stage* and *pdf_path* (created)."""

    ensure_dirs()
    directory = _CACHE_DIR / doc_id(pdf_path) / stage
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def pages_dir(pdf_path: os.PathLike | str) -> Path:
    """Directory where rasterised page images are stored."""

    return stage_dir("pages", pdf_path)


def extracted_content_path(pdf_path: os.PathLike | str) -> Path:
    """Path to the final extracted content JSON for *pdf_path*."""
    
    return stage_dir("extracted", pdf_path) / "content.json"


# ---------------------------------------------------------------------------
# Tiny JSON helpers (no external deps)
# ---------------------------------------------------------------------------


def save_json(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())
