"""Links capability: the internal link graph of a built site.

Reads the build directory rather than a single page, because a link is a relation
between two pages and no single-page view can see one. Three questions, all of
them graph questions:

    link.target_missing   a link points at a URL the build does not serve
    link.unreachable      no internal link reaches a built page from the home page
    link.depth            a page sits four or more clicks from the home page

**Static only, and it refuses rather than pretending.** A graph needs to know
every page the site serves. A live crawl sees the pages inside its limit and
nothing else, so every page beyond the limit would read as unreachable and every
link to it as broken — a graph of the crawl, not of the site. That is D32's
failure with a graph attached, so `run()` raises instead of producing it.

**Anchor text is not read.** `Page.links` carries the target and nothing else: the
words inside an `<a>` are authored prose, and the extractor holds no prose (D13).
The consequence is stated rather than hidden — `references/internal-linking.md`
gives anchor-text guidance this tool cannot check, and says so next to it.

**One finding per missing target, not one per linking page.** A broken link in a
site-wide template is one defect on one URL, and reporting it once per page turns
a single fixable line into a screenful of identical criticals — the failure D38
named. Findings for the two graph questions are per page, because there the page
*is* the subject.
"""

from __future__ import annotations

import posixpath
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from ... import pages as pages_module
from ...errors import CapabilityError
from ...report import TOOL_NAME, TOOL_VERSION

CRITICAL = "critical"
WARNING = "warning"
REPORT_VERSION = "1"

# The click distance at which `references/internal-linking.md` says crawling
# thins out. The rule fires at this depth, so it names the pages the reference is
# talking about rather than every page on a deep site.
DEPTH_LIMIT = 4

# Schemes that are a link but never a link between two pages of this site.
NON_PAGE_SCHEMES = ("mailto:", "tel:", "sms:", "javascript:", "data:", "ftp:", "file:")


def _finding(rule_id, severity, message, observed, expected, subject, location):
    return {
        "rule_id": rule_id, "severity": severity, "message": message,
        "observed": observed, "expected": expected, "subject": subject,
        "location": location,
    }


# --- URL handling ----------------------------------------------------------

def _key(path: str) -> str:
    """The lookup key for a URL path.

    A static server answers one file under several spellings: `/about`,
    `/about/` and `/about/index.html` are the same page. They collapse to one key
    so the graph has one node per page instead of three, and so a link written
    either way resolves the same.
    """
    path = unquote(path.split("#", 1)[0].split("?", 1)[0])
    if not path.startswith("/"):
        path = "/" + path
    return posixpath.normpath(path)


def _bare_host(netloc: str) -> str:
    """A host without userinfo, port or a leading `www.`.

    The `www` strip is deliberate and mirrors D38: the commonest misconfiguration
    is a site that canonicalises to `www` while its config names the apex. An
    absolute link across those two spellings is a link to the same site, and
    treating it as external would make the graph quietly miss it.
    """
    host = netloc.rsplit("@", 1)[-1].split(":")[0].strip().lower()
    return host[4:] if host.startswith("www.") else host


def target_of(href: str, page_source: str, host: str) -> str | None:
    """The site-relative path a link points at, or None if it is not one.

    None is the answer for everything that is not a link between two pages of
    this site: an external host, an in-page fragment, a `mailto:`, and the empty
    `href` a template leaves behind. That is not a defect being ignored — none of
    them is a broken internal link.
    """
    raw = (href or "").strip()
    if not raw or raw.startswith("#"):
        return None
    if raw.lower().startswith(NON_PAGE_SCHEMES):
        return None

    split = urlsplit(raw)
    if split.scheme and split.scheme not in ("http", "https"):
        return None

    if split.netloc:
        if _bare_host(split.netloc) != _bare_host(host):
            return None
        return _key(split.path or "/")

    if not split.path:
        return None  # a bare `?query`, or a fragment that survives the strip
    if split.path.startswith("/"):
        return _key(split.path)

    # A relative link resolves against the directory of the page that holds it.
    base = posixpath.dirname("/" + page_source)
    return _key(posixpath.join(base, split.path))


def build_served(root: Path) -> set[str]:
    """Every URL path the build answers, under every spelling a static server
    accepts.

    Files are included, not only pages: a link to a PDF is a real link and its
    target has to exist too. Built from the directory rather than from the
    audited page set, so a target excluded from the audit by `ignore_path` still
    counts as existing — it is un-audited, not absent.
    """
    served: set[str] = set()
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        served.add(_key("/" + rel))
        if rel.endswith("/index.html"):
            served.add(_key("/" + rel[: -len("index.html")]))
        elif rel == "index.html":
            served.add("/")
        elif rel.endswith(".html"):
            served.add(_key("/" + rel[: -len(".html")]))
    return served


def _page_aliases(source: str) -> set[str]:
    """The keys that name one built page, so a link can be tied to it.

    These are the same spellings `build_served` accepts, and they have to stay
    that way: one function decides whether a link resolves, this one decides
    which page it resolves to. An alias the first accepts and the second misses
    is a link that exists and leads nowhere in the graph.
    """
    if source == "index.html":
        return {"/", _key("/index.html")}
    if source.endswith("/index.html"):
        return {_key("/" + source), _key("/" + source[: -len("index.html")])}
    aliases = {_key("/" + source)}
    if source.endswith(".html"):
        aliases.add(_key("/" + source[: -len(".html")]))
    return aliases


def _page_alias_map(page_list) -> dict[str, str]:
    """One page per key. First page wins a contested key.

    A build holding both `a.html` and `a/index.html` gives `/a` two pages; the
    graph follows whichever comes first and does not report the collision. Hugo
    and WordPress do not produce that pair, so this is a named limit rather than
    a rule — see the README.
    """
    aliases: dict[str, str] = {}
    for page in page_list:
        for alias in _page_aliases(page.source):
            aliases.setdefault(alias, page.source)
    return aliases


def _distances(start: str, edges: dict[str, set[str]]) -> dict[str, int]:
    """Clicks from the home page to every page an internal link reaches."""
    distances = {start: 0}
    queue = deque([start])
    while queue:
        current = queue.popleft()
        for nxt in edges.get(current, ()):
            if nxt not in distances:
                distances[nxt] = distances[current] + 1
                queue.append(nxt)
    return distances


# --- the graph -------------------------------------------------------------

def audit_pages(page_list, served: set[str], host: str) -> dict[str, Any]:
    """Run the three graph rules over a page set and the URL space it lives in."""
    findings: list[dict] = []
    aliases = _page_alias_map(page_list)

    missing: dict[str, list[tuple[str, str]]] = {}
    edges: dict[str, set[str]] = {}
    internal_links = 0

    for page in page_list:
        for link in page.links:
            target = target_of(link["href"], page.source, host)
            if target is None:
                continue
            internal_links += 1
            if target in served:
                other = aliases.get(target)
                if other is not None:
                    edges.setdefault(page.source, set()).add(other)
            else:
                missing.setdefault(target, []).append((page.source, link["href"]))

    for target in sorted(missing):
        referrers = sorted({source for source, _ in missing[target]})
        shown = ", ".join(referrers[:3])
        extra = f" and {len(referrers) - 3} more" if len(referrers) > 3 else ""
        findings.append(_finding(
            "link.target_missing", CRITICAL,
            f"{len(referrers)} page(s) link to {target}, which the build does not "
            f"serve: {shown}{extra}.",
            missing[target][0][1], "a URL the build output serves",
            target, "body > a[href]"))

    unreachable: list[str] = []
    deep: list[tuple[str, int]] = []
    start = aliases.get("/")
    if start is not None:
        # No home page means no root to measure from. That is a build that cannot
        # answer the question, and inventing an answer would report every page as
        # an orphan.
        distances = _distances(start, edges)
        for page in page_list:
            if page.source == start or page.is_404:
                continue
            if page.source not in distances:
                unreachable.append(page.source)
            elif distances[page.source] >= DEPTH_LIMIT:
                deep.append((page.source, distances[page.source]))

    for source in sorted(unreachable):
        findings.append(_finding(
            "link.unreachable", WARNING,
            f"{source} is in the build but no internal link reaches it from the "
            f"home page. Either something should link to it, or it does not belong "
            f"in the build.",
            None, "reachable from /", source, "link graph > inbound"))

    for source, distance in sorted(deep):
        findings.append(_finding(
            "link.depth", WARNING,
            f"{source} is {distance} clicks from the home page. Pages at "
            f"{DEPTH_LIMIT} or more are crawled less often.",
            distance, f"< {DEPTH_LIMIT}", source, "link graph > depth"))

    return {
        "findings": findings,
        "internal_links": internal_links,
        "broken_targets": len(missing),
        "unreachable_pages": len(unreachable),
        "deep_pages": len(deep),
    }


CHECKS: tuple[str, ...] = (
    "link.target_missing",
    "link.unreachable",
    "link.depth",
)


def run(config, live: bool = False, run: str | None = None, **_ignored) -> dict[str, Any]:
    """Audit the internal link graph of the configured build output."""
    if live:
        raise CapabilityError(
            "The link graph needs the whole build; a crawl only ever sees part of "
            "a site.\n\n"
            "A live crawl reads the pages inside its limit, so every page beyond "
            "that limit would read as unreachable and every link to it as broken. "
            "That report would describe the crawl, not the site.\n\n"
            "Run it against built output instead:\n"
            "  python scripts/wo.py links"
        )

    page_set = pages_module.resolve(config, live=False)
    root = pages_module.find_static_dir(config.static_dir)
    result = audit_pages(page_set.pages, build_served(root), config.domain)

    findings = result["findings"]
    critical = sum(1 for f in findings if f["severity"] == CRITICAL)

    return {
        "report_version": REPORT_VERSION,
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "crawl_mode": page_set.mode,
        "site": {"url": config.site_url, "domain": config.domain},
        "capability": "links",
        "source": page_set.source,
        "rules_run": list(CHECKS),
        "summary": {
            "audited_pages": len(page_set.pages),
            "ignored_pages": page_set.ignored,
            "internal_links": result["internal_links"],
            "broken_targets": result["broken_targets"],
            "unreachable_pages": result["unreachable_pages"],
            "deep_pages": result["deep_pages"],
            "total_critical_issues": critical,
            "total_warnings": len(findings) - critical,
        },
        "findings": findings,
    }
