"""Processing sub-package for *injestion*.

This package now only hosts actively maintained code.  Deprecated helpers have
been moved to :pymod:`injestion.attic` and are **not** re-exported here to keep
the public surface minimal.
"""

from .box import Box

__all__: list[str] = ["Box"]
