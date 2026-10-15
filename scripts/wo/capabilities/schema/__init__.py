"""Schema capability: JSON-LD structure and completeness.

No `RULES` tuple here: this capability's checks take a parsed block rather than a
`Page`, so they are not shaped like the on-page rules. `CHECKS` is the contract
`compare` relies on.
"""

from __future__ import annotations

from .audit import CHECKS, audit_page, run

__all__ = ["CHECKS", "audit_page", "run"]