"""website-optimizer tooling.

One package, one entry point (`wo.py`), one capability per surface. The split
follows decision D2: running the entry point puts this directory on `sys.path`,
so capability packages import without path manipulation, and the pipeline order
lives in code instead of in folder numbering.
"""

from __future__ import annotations

__all__ = ["config", "envelope", "jsonschema", "page", "report"]