"""Compatibility shim that exposes the original *injestion* package under the
canonical *ingestion* name.

The codebase historically misspelled the package as ``injestion``.  To avoid
breaking downstream users we continue to ship the old import path **and** a
light-weight forwarder so that

    >>> import ingestion

gives access to the exact same module instance as

    >>> import src.injestion

The wrapper must sit at ``src/ingestion`` (rather than the project root) to be
discoverable via the default *PYTHONPATH* adjustments performed in the test
runner.
"""

from __future__ import annotations

import importlib
import sys

# Import the real implementation living under the historical name and make it
# available as *ingestion* in ``sys.modules`` so that subsequent imports find
# the module instantly without going through this wrapper again.
_injestion = importlib.import_module("src.injestion")
sys.modules[__name__] = _injestion

# Re-export public attributes to satisfy `from ingestion import …` statements.
globals().update(_injestion.__dict__)

