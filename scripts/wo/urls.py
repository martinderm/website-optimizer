"""How a URL path and a build file name each other.

Two capabilities need this: `links` resolves a link target against the build,
and `crawler-files` resolves a sitemap URL against it. The question is identical —
*is this URL one the build serves, and which page is it* — and answering it twice
is how two answers start to disagree. They already did once: within `links`,
`build_served` accepted `/index.html` as a spelling of the home page and
`_page_aliases` did not, and only a guard caught it.

So the spellings live here, once, and a capability that needs them asks this
module rather than deriving its own.

A static server answers one file under several spellings. `/about`, `/about/`
and `/about/index.html` are one page, and a link written any of those three ways
resolves to it. `key()` collapses them to one string so the rest of the tool can
compare URLs instead of guessing.
"""

from __future__ import annotations

import posixpath
from pathlib import Path
from urllib.parse import unquote

INDEX = "index.html"


def key(path: str) -> str:
    """The lookup key for a URL path.

    Query and fragment are dropped, percent-encoding is decoded, and the result
    is normalised: `/about/?x=1#top` and `/about` both become `/about`.
    """
    path = unquote(path.split("#", 1)[0].split("?", 1)[0])
    if not path.startswith("/"):
        path = "/" + path
    return posixpath.normpath(path)


def served(root: Path) -> set[str]:
    """Every URL path the build answers, under every spelling a server accepts.

    Files are included, not only pages: a link to a PDF is a real link and its
    target has to exist too. Built from the directory rather than from the
    audited page set, so a target excluded from the audit by `ignore_path` still
    counts as existing — it is un-audited, not absent.
    """
    paths: set[str] = set()
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        paths.add(key("/" + rel))
        if rel == INDEX:
            paths.add("/")
        elif rel.endswith("/" + INDEX):
            paths.add(key("/" + rel[: -len(INDEX)]))
        elif rel.endswith(".html"):
            paths.add(key("/" + rel[: -len(".html")]))
    return paths


def page_urls(source: str) -> set[str]:
    """The keys that name one built page, so a URL can be tied to it.

    These are the same spellings `served()` accepts, and they have to stay that
    way: `served()` decides whether a URL resolves, this decides which page it
    resolves to. A key the first accepts and the second misses is a URL that
    exists and leads nowhere.
    """
    if source == INDEX:
        return {"/", key("/" + INDEX)}
    if source.endswith("/" + INDEX):
        return {key("/" + source), key("/" + source[: -len(INDEX)])}
    keys = {key("/" + source)}
    if source.endswith(".html"):
        keys.add(key("/" + source[: -len(".html")]))
    return keys


def path_of(url: str, host: str) -> str | None:
    """The site-relative path a URL names, or None when it names another site.

    Absolute and protocol-relative URLs are accepted when they point at this
    host, with or without `www` — a site canonicalising to one and configured as
    the other is one site, not two (D38). Anything on another host returns None,
    which is a fact about the URL rather than a defect in it.
    """
    raw = (url or "").strip()
    if not raw:
        return None
    if raw.startswith("//"):
        raw = "https:" + raw
    if "://" not in raw:
        return key(raw)
    scheme, rest = raw.split("://", 1)
    if scheme.lower() not in ("http", "https"):
        return None
    authority, _, path = rest.partition("/")
    if bare_host(authority) != bare_host(host):
        return None
    return key("/" + path)


def bare_host(authority: str) -> str:
    """A host without userinfo, port or a leading `www.`."""
    host = authority.rsplit("@", 1)[-1].split(":")[0].strip().lower()
    return host[4:] if host.startswith("www.") else host
