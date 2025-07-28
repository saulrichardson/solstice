"""Local disk storage helpers shared across ingestion stages.

All derived artefacts are stored below the project-level ``data/`` directory
using the structure::

    data/
      raw/               # (optional) original PDFs copied here
      cache/
        pages/<doc>/     page-NNN.png
        layout/<doc>/    layout.json
        refine/<doc>/    refined.json
        ocr/<doc>/       ocr.json
        agent/<doc>/     reasoning.json  …
      docs/              # final, merged document objects

Where ``<doc>`` is the first 8 characters of the SHA-256 hash of the original
PDF bytes.  This guarantees a stable path for every document without risk of
name collisions.
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


_DATA_DIR = Path(__file__).resolve().parents[2] / "data"
_CACHE_DIR = _DATA_DIR / "cache"
_DOCS_DIR = _DATA_DIR / "docs"


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def ensure_dirs() -> None:
    """Create *data* root folders if they do not yet exist."""

    for d in (_DATA_DIR, _CACHE_DIR, _DOCS_DIR):
        d.mkdir(parents=True, exist_ok=True)


def doc_id(pdf_path: os.PathLike | str) -> str:
    """Return the first 8 hex digits of the SHA-256 hash of *pdf_path*."""

    h = hashlib.sha256()
    with open(pdf_path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:8]


def stage_dir(stage: str, pdf_path: os.PathLike | str) -> Path:
    """Return the cache directory for *stage* and *pdf_path* (created)."""

    ensure_dirs()
    directory = _CACHE_DIR / stage / doc_id(pdf_path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def pages_dir(pdf_path: os.PathLike | str) -> Path:
    """Directory where rasterised page images are stored."""

    return stage_dir("pages", pdf_path)


def final_doc_path(pdf_path: os.PathLike | str) -> Path:
    """Path to the final assembled JSON document for *pdf_path*."""

    ensure_dirs()
    return _DOCS_DIR / f"{doc_id(pdf_path)}.json"


# ---------------------------------------------------------------------------
# Tiny JSON helpers (no external deps)
# ---------------------------------------------------------------------------


def save_json(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())

