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
    "on-page": {
        "module": "wo.capabilities.on_page.audit",
        "schema": "on-page-report.schema.json",
    },
    "redirects": {
        "module": "wo.capabilities.redirects.audit",
        "schema": "redirects-report.schema.json",
    },
    # `compare` reads stored runs instead of auditing, so it is a workspace
    # operation rather than something a site opts into. Enabling it per site
    # would be paperwork with no meaning: it changes what the tool can do, not
    # what this site looks like.
    "compare": {
        "module": "wo.capabilities.compare.audit",
        "schema": "compare-report.schema.json",
        "meta": True,
    },
    "images": {
        "module": "wo.capabilities.images.audit",
        "schema": "images-report.schema.json",
    },
    # `links` reads build output only. A crawl sees the pages inside its limit,
    # so a graph drawn from one would report the crawl's reach as the site's
    # architecture; the capability raises rather than doing that (see its README).
    "links": {
        "module": "wo.capabilities.links.audit",
        "schema": "links-report.schema.json",
    },
    "schema": {
        "module": "wo.capabilities.schema.audit",
        "schema": "schema-report.schema.json",
    },
}

META = {name for name, entry in REGISTRY.items() if entry.get("meta")}

__all__ = ["REGISTRY", "META"]