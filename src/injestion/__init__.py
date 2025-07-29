"""Lightweight internal stand-in for the external *injestion* package.

The original library is not part of this repository, but several modules in
`src.fact_check` import `injestion.models.document.Document` and
`injestion.processing.fact_check_interface.FactCheckInterface`.

We provide minimal implementations so the codebase remains self-contained.
These stubs expose only the attributes & methods actually used downstream –
they are *not* full-featured replacements of the original library.
"""

from types import ModuleType
import sys
from importlib.util import module_from_spec, spec_from_loader


# ---------------------------------------------------------------------------
# Helper to create sub-modules on the fly so that `import injestion.models …`
# and `import injestion.processing …` work transparently.
# ---------------------------------------------------------------------------

def _ensure_submodule(name: str) -> ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    spec = spec_from_loader(name, loader=None)
    module = module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules[name] = module
    return module


# Create top-level sub-packages
models_pkg = _ensure_submodule("injestion.models")
processing_pkg = _ensure_submodule("injestion.processing")

# Create document submodule for full import path
document_module = _ensure_submodule("injestion.models.document")
fact_check_module = _ensure_submodule("injestion.processing.fact_check_interface")


# Import the actual Document and Block models
from .models.document import Document, Block
# Import the actual FactCheckInterface
from .processing.fact_check_interface import FactCheckInterface

# Set them in the submodules
models_pkg.Document = Document  # type: ignore[attr-defined]
models_pkg.Block = Block  # type: ignore[attr-defined]
document_module.Document = Document  # type: ignore[attr-defined]
document_module.Block = Block  # type: ignore[attr-defined]


# The FactCheckInterface is now imported from processing.fact_check_interface above


processing_pkg.FactCheckInterface = FactCheckInterface  # type: ignore[attr-defined]
fact_check_module.FactCheckInterface = FactCheckInterface  # type: ignore[attr-defined]


# Import the main pipeline function
from .pipeline import ingest_pdf

# Clean-up helpers from namespace
del module_from_spec, spec_from_loader, ModuleType, _ensure_submodule

__all__ = ["Document", "FactCheckInterface", "ingest_pdf"]

