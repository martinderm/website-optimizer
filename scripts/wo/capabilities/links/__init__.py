"""Links capability: the internal link graph of a built site."""

from __future__ import annotations

from .audit import CHECKS, audit_pages, build_served, run

__all__ = ["CHECKS", "audit_pages", "build_served", "run"]
