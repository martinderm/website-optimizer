"""On-page capability: the signals that live inside a single page."""

from __future__ import annotations

from .audit import RULES, audit_page, run

__all__ = ["RULES", "audit_page", "run"]