"""Capability error base.

One exception type so the CLI can report any capability failure the same way.
Before this existed, `compare` raised its own `CompareError` and `redirects`
converted its parse error into a `FileNotFoundError`, which forced the entry
point into a second special case per capability — the kind of coupling that
grows with every capability added.
"""

from __future__ import annotations


class CapabilityError(Exception):
    """A capability could not run.

    The message must be actionable on its own: what is missing, and the command
    that would fix it. A traceback is not user guidance.
    """

    kind = "CapabilityError"


class ConfigError(CapabilityError):
    kind = "ConfigError"


class MappingError(CapabilityError):
    kind = "MappingError"


class CompareError(CapabilityError):
    kind = "NothingToCompare"


class CrawlError(CapabilityError):
    """A live crawl could not run.

    Separate from the other kinds because the fix is different: not a config
    value, but a missing browser, an unreachable host, or a page that never
    finished rendering. Each of those gets its own message from the crawl module.
    """

    kind = "CrawlError"