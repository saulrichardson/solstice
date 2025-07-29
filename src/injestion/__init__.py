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


# ---------------------------------------------------------------------------
# Minimal `Document` class – enough for fact-checking pipeline.
# ---------------------------------------------------------------------------


class Document:  # pylint: disable=too-few-public-methods
    """Extremely thin placeholder for the original PDF Document model."""

    def __init__(self, **data):
        self.__dict__.update(data)

        # Provide defaults for attributes referenced downstream
        self.source_pdf = getattr(self, "source_pdf", "unknown.pdf")
        self.reading_order = getattr(self, "reading_order", [])
        self.blocks = getattr(self, "blocks", [])


models_pkg.Document = Document  # type: ignore[attr-defined]
document_module.Document = Document  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Minimal `FactCheckInterface` – only the methods used by the pipeline.
# ---------------------------------------------------------------------------


class FactCheckInterface:  # pylint: disable=too-few-public-methods
    """Stub with API compatible surface for fact-checking helpers."""

    def __init__(self, document: Document):
        self.document = document

    # Downstream code calls these two methods.  We return basic values to
    # avoid breaking while still signalling that real extraction is absent.
    def get_full_text(self, *, include_figure_descriptions: bool = True, normalize: bool = True) -> str:  # noqa: D401,E501
        return ""

    def get_text_with_locations(self, *, normalize: bool = True):  # noqa: D401
        return []


processing_pkg.FactCheckInterface = FactCheckInterface  # type: ignore[attr-defined]
fact_check_module.FactCheckInterface = FactCheckInterface  # type: ignore[attr-defined]


# Clean-up helpers from namespace
del module_from_spec, spec_from_loader, ModuleType, _ensure_submodule

