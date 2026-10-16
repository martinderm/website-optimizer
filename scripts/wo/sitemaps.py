"""Reading a sitemap, whichever shape it arrived in.

A sitemap is not always a sitemap. WordPress Core (`/wp-sitemap.xml`) and Yoast
(`/sitemap_index.xml`) both emit a *sitemap index*: a list of further sitemap
files rather than of pages. Reading an index as a page list is a wrong answer and
not a degraded one — the caller would then treat the XML files as though they
were the pages (D37).

This module holds the **syntax**: what a `<loc>` looks like, how an index is
recognised, and which filenames the convention actually uses. The syntax is the
same question for everyone and lives here once.

The **control flow** deliberately does not. Two callers ask different things:

- the live crawl wants *which URLs should I render*, capped by `max_pages`, with
  a fallback chain and a loud failure when a configured sitemap is unusable;
- `crawler-files` wants *what does this sitemap list, all of it, and could it be
  read at all*, where a cap would turn every page beyond it into a false finding.

Those differ in their errors, their limits and their sources — a build directory
reads the file, a crawl fetches it. Sharing the loop would mean one of them
carrying the other's contract.
"""

from __future__ import annotations

import re

# Filenames the sitemap convention actually uses. WordPress Core and Yoast - by
# far the two commonest sitemap producers on WordPress - disagree about both the
# name and the extension, which is why the list is a list.
KNOWN_NAMES = (
    "/wp-sitemap.xml",      # WordPress Core, since 5.5
    "/sitemap_index.xml",   # Yoast SEO
    "/sitemap.xml",         # generic, and what a hand-written site uses
    "/sitemap-index.xml",   # Rank Math and others
)

# `xml.etree` is stdlib and would be the obvious parser; a regex is used instead
# because a sitemap served with a wrong content type or an unexpected namespace
# prefix should not abort the caller, and `<loc>` values are plain text that
# cannot fail on shape.
_LOC = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>", re.IGNORECASE)
_INDEX_ROOT = re.compile(r"<sitemapindex\b", re.IGNORECASE)


def locs(body: str) -> list[str]:
    """Every `<loc>` value in a sitemap document, in document order."""
    return _LOC.findall(body)


def is_index(body: str) -> bool:
    """Whether this document lists sitemaps rather than pages."""
    return bool(_INDEX_ROOT.search(body))


def looks_like_markup(body: str) -> bool:
    """Whether the body is a sitemap at all.

    A host that answers every path with its own HTML page — a soft 404, or a
    catch-all route — returns 200 and a document with no `<loc>` and no root
    element. That is the case `locs()` alone cannot tell from a sitemap that
    happens to list nothing, and the two mean opposite things: one is a broken
    sitemap, the other is an empty one.
    """
    stripped = body.lstrip()
    return stripped.startswith("<?xml") or "<urlset" in body.lower() or is_index(body)
