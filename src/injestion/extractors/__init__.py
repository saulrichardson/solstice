"""(Deprecated) extractor interfaces.

This package previously exposed TextExtractor, TableExtractor, FigureExtractor,
and ComponentRouter, all based on heavy third-party dependencies. The
functionality has been removed from the codebase – the module now exists only
to avoid import errors in downstream code while a proper migration path is put
in place.
"""

from __future__ import annotations

import warnings


def __getattr__(name: str):  # pragma: no cover
    warnings.warn(
        f"injestion.extractors.{name} was removed in the 2025-07 refactor.",
        DeprecationWarning,
        stacklevel=2,
    )
    raise AttributeError(name)


__all__: list[str] = []
