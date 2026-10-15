"""Capability package: one folder, one job.

Each capability audits one bounded surface of a site and returns atomic
findings. Capabilities do not write, do not judge, and do not read each other's
conclusions.

Naming note: the package directory is `on_page` while the command the user types
is `on-page`. A hyphen is a valid command name and an invalid Python identifier,
so the identifier space uses the underscore and the interface keeps the hyphen.
"""

from __future__ import annotations

REGISTRY = {
    "on-page": "wo.capabilities.on_page.audit",
}

__all__ = ["REGISTRY"]