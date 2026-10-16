"""Crawler-files capability: the documents a site publishes about itself.

`robots.txt`, the XML sitemap and `llms.txt` are the site describing itself to
crawlers. They are also the three documents nobody reads until something has gone
wrong for months: a `Disallow: /` left over from a staging lock looks exactly like
a healthy site, and a sitemap that silently stopped being generated looks exactly
like a site with nothing to index.

**Two sources, one set of rules.** In static mode these are files in the build
output; in live mode they are three URLs. The rules above them cannot tell the
difference, which is the same arrangement `pages` gives the page-reading
capabilities (D33) — here applied to the three documents rather than to the pages.

**Two rules need a build and drop out of a live run**, exactly as
`icon.file_missing` does in `images`: whether a *built page* is missing from the
sitemap, and whether a *sitemap URL* is served, are answers about the build. A
live run is still worth making — a `Disallow: /` is worth finding on any site —
so unlike `links` this capability does not refuse; it reports less and says which
rules it ran.

**No coverage claim is made from a sitemap that could not be read.** A sitemap
that fails to parse, or that a soft 404 answered with an HTML page, would make
every page on the site look absent from it. That is the loudest wrong answer this
capability could produce, so the coverage rules are skipped whenever the sitemap
was not read, and a separate rule reports the sitemap itself.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urljoin

from ... import pages as pages_module
from ... import sitemaps, urls
from ...report import TOOL_NAME, TOOL_VERSION

CRITICAL = "critical"
WARNING = "warning"
REPORT_VERSION = "1"

# Three or four requests, so this is a constant rather than a config entry.
# `redirects` made its timeout configurable because a site can have hundreds of
# rules; here there is nothing to tune.
TIMEOUT_SECONDS = 10

# Paths that are delivery rather than content. Blocking them stops a crawler
# rendering the page, and a page that cannot be rendered cannot be indexed.
ASSET_PREFIXES = (
    "/css", "/js", "/images", "/img", "/media", "/assets", "/fonts",
    "/static", "/uploads",
)

# Rules that answer a question about the build. Absent from a live run's
# `rules_run`, because a rule that cannot run must never read as one that found
# nothing.
STATIC_ONLY = ("sitemap.absent_page", "sitemap.unsupported_url")

CHECKS: tuple[str, ...] = (
    "robots.missing",
    "robots.blocks_site",
    "robots.blocks_asset",
    "robots.sitemap_missing",
    "sitemap.missing",
    "sitemap.unreadable",
    "sitemap.empty",
    "sitemap.absent_page",
    "sitemap.unsupported_url",
    "llms.missing",
    "llms.empty",
)


def _finding(rule_id, severity, message, observed, expected, subject, location):
    return {
        "rule_id": rule_id, "severity": severity, "message": message,
        "observed": observed, "expected": expected, "subject": subject,
        "location": location,
    }


def active_checks(live: bool) -> tuple[str, ...]:
    """The rules that can run against the chosen source."""
    if not live:
        return CHECKS
    return tuple(check for check in CHECKS if check not in STATIC_ONLY)


# --- robots.txt ------------------------------------------------------------

def groups(text: str) -> list[tuple[list[str], list[tuple[str, str]]]]:
    """The directive groups in a robots.txt, in file order.

    Each group is its user-agents and its rules. The shape matters because
    `Disallow: /` means something different under `User-agent: *` than under
    `User-agent: Googlebot`, and flattening the file would lose exactly that.
    """
    parsed: list[tuple[list[str], list[tuple[str, str]]]] = []
    agents: list[str] = []
    rules: list[tuple[str, str]] = []

    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        field, _, value = line.partition(":")
        field = field.strip().lower()
        value = value.strip()
        if field == "user-agent":
            if agents and rules:
                parsed.append((agents, rules))
                agents, rules = [], []
            agents.append(value.lower())
        elif field in ("disallow", "allow"):
            rules.append((field, value))

    if agents or rules:
        parsed.append((agents, rules))
    return parsed


def sitemap_directives(text: str) -> list[str]:
    """`Sitemap:` values, in file order. The site naming its own sitemap."""
    found: list[str] = []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if line.lower().startswith("sitemap:"):
            value = line.split(":", 1)[1].strip()
            if value:
                found.append(value)
    return found


def locks_out_everyone(text: str) -> bool:
    """Whether the file tells every crawler to stay out."""
    for agents, rules in groups(text):
        if "*" not in agents:
            continue
        if any(field == "disallow" and value in ("/", "*") for field, value in rules):
            return True
    return False


def blocked_assets(text: str) -> list[str]:
    """Disallow rules that cut off delivery rather than content."""
    blocked: list[str] = []
    for _agents, rules in groups(text):
        for field, value in rules:
            if field != "disallow":
                continue
            # `/` and `*` block everything and belong to the site rule; naming
            # them here as nine blocked asset paths would bury that finding.
            if value in ("", "/", "*"):
                continue
            prefix = "/" + value.lstrip("/").rstrip("/").lstrip("/")
            if any(prefix == p or prefix.startswith(p + "/") for p in ASSET_PREFIXES):
                blocked.append(value)
    return blocked


# --- sitemap ---------------------------------------------------------------

def read_sitemap(text: str, read_url: Callable[[str], str | None] | None,
                 max_index: int = 50, max_depth: int = 2) -> tuple[list[str], str | None]:
    """Every URL a sitemap lists, following an index when there is one.

    Returns the URLs and a problem: `None`, `"unreadable"` when the document is
    not a sitemap at all or none of an index's children could be read, or
    `"empty"` when it is a sitemap that lists nothing. The two are different
    defects and the caller reports them differently.
    """
    if text is None:
        return [], None

    root_locs = sitemaps.locs(text)
    if not root_locs:
        if not sitemaps.looks_like_markup(text):
            return [], "unreadable"
        return [], "empty"

    if not sitemaps.is_index(text):
        return root_locs, None

    if read_url is None:
        return [], "unreadable"

    collected: list[str] = []
    read_any = False
    seen: set[str] = set()
    queue: list[tuple[str, int]] = [(loc, 1) for loc in root_locs]

    while queue and len(seen) < max_index:
        current, depth = queue.pop(0)
        if current in seen:
            continue
        seen.add(current)
        body = read_url(current)
        if not body:
            continue
        read_any = True
        entries = sitemaps.locs(body)
        if not entries:
            continue
        if sitemaps.is_index(body):
            if depth < max_depth:
                queue.extend((loc, depth + 1) for loc in entries)
            continue
        collected.extend(entries)

    if not read_any:
        return [], "unreadable"
    return collected, None


def audit_sources(*, robots: str | None, sitemap: str | None, llms: str | None,
                  read_url: Callable[[str], str | None] | None = None,
                  pages: list | None = None, served: set[str] | None = None,
                  host: str = "") -> dict[str, Any]:
    """Run every rule over the three documents.

    `pages` and `served` are the build's answers; pass `None` for either when
    there is no build, and the two rules that need one stay silent rather than
    guessing.
    """
    findings: list[dict] = []

    # --- robots.txt
    if robots is None:
        findings.append(_finding(
            "robots.missing", WARNING,
            "No robots.txt. Nothing is blocked by it, and nothing is guided by it "
            "either — in particular the sitemap is not discoverable through it.",
            None, "a robots.txt", "robots.txt", "site root"))
    else:
        if locks_out_everyone(robots):
            findings.append(_finding(
                "robots.blocks_site", CRITICAL,
                "robots.txt disallows the whole site for every crawler. The site "
                "looks healthy and cannot be indexed. The usual cause is a staging "
                "lock that was never lifted.",
                "/", "crawlable", "robots.txt", "robots.txt > Disallow"))
        for value in blocked_assets(robots):
            findings.append(_finding(
                "robots.blocks_asset", WARNING,
                f"robots.txt disallows '{value}', which is delivery rather than "
                f"content. A crawler that cannot fetch the CSS or the images cannot "
                f"render the page, and a page it cannot render is not indexed well.",
                value, "assets crawlable", "robots.txt", "robots.txt > Disallow"))
        if not sitemap_directives(robots):
            findings.append(_finding(
                "robots.sitemap_missing", WARNING,
                "robots.txt names no sitemap. The `Sitemap:` line is the cheapest "
                "indexing win there is: it is how a crawler finds the sitemap "
                "without anyone submitting it.",
                0, ">= 1 Sitemap: line", "robots.txt", "robots.txt"))

    # --- sitemap
    found = sitemap is not None
    sitemap_urls: list[str] = []
    problem: str | None = None
    if sitemap is None:
        findings.append(_finding(
            "sitemap.missing", WARNING,
            "No XML sitemap. Crawling still happens through links, but a sitemap is "
            "how a crawler learns about pages nothing links to yet.",
            None, "a sitemap", "sitemap.xml", "site root"))
    else:
        sitemap_urls, problem = read_sitemap(sitemap, read_url)
        if problem == "unreadable":
            findings.append(_finding(
                "sitemap.unreadable", CRITICAL,
                "The sitemap is not a sitemap: it was found, and it contains no "
                "`<loc>` entries and no sitemap root element. A host answering every "
                "path with its own page produces exactly this.",
                None, "<urlset> or <sitemapindex>", "sitemap.xml", "sitemap"))
        elif problem == "empty" or not sitemap_urls:
            findings.append(_finding(
                "sitemap.empty", CRITICAL,
                "The sitemap lists no URLs. It parses, and it says the site has "
                "nothing to index.",
                0, ">= 1 URL", "sitemap.xml", "sitemap"))

    # Coverage is claimed only from a sitemap that was actually read. Reporting
    # every page as absent because the sitemap failed to parse would be the
    # loudest wrong answer available here.
    covered = found and problem is None and bool(sitemap_urls)

    if covered and served is not None:
        for url in sitemap_urls:
            path = urls.path_of(url, host)
            if path is None:
                findings.append(_finding(
                    "sitemap.unsupported_url", CRITICAL,
                    f"The sitemap lists {url}, which is on another host. A sitemap "
                    f"may only list URLs of the site it belongs to.",
                    url, "a URL on this host", url, "sitemap > loc"))
            elif path not in served:
                findings.append(_finding(
                    "sitemap.unsupported_url", CRITICAL,
                    f"The sitemap lists {url}, which the build does not serve. A "
                    f"sitemap that names a 404 asks a crawler to fetch a page that "
                    f"does not exist.",
                    url, "a URL the build output serves", url, "sitemap > loc"))

    if covered and pages is not None:
        listed = {k for k in (urls.path_of(u, host) for u in sitemap_urls) if k}
        for page in pages:
            if page.is_404:
                continue
            if page.robots and "noindex" in page.robots.lower():
                continue
            if not (urls.page_urls(page.source) & listed):
                findings.append(_finding(
                    "sitemap.absent_page", WARNING,
                    f"{page.source} is built but appears in no sitemap. Either it "
                    f"should be listed, or it is not meant to be indexed and should "
                    f"say so with a noindex.",
                    None, "listed in the sitemap", page.source, "sitemap"))

    # --- llms.txt
    if llms is None:
        findings.append(_finding(
            "llms.missing", WARNING,
            "No llms.txt. It is a young convention rather than a standard, and no "
            "crawler needs it — but a site that wants an assistant to read the "
            "right pages has nothing to point at without one.",
            None, "an llms.txt", "llms.txt", "site root"))
    elif "](" not in llms:
        findings.append(_finding(
            "llms.empty", WARNING,
            "llms.txt contains no links. The convention is a list of the pages "
            "worth reading; a file without one says nothing.",
            0, ">= 1 link", "llms.txt", "llms.txt"))

    return {
        "findings": findings,
        "sitemap_found": found,
        "sitemap_urls": len(sitemap_urls),
        "robots_found": robots is not None,
        "llms_found": llms is not None,
        "checked_pages": len(pages) if (covered and pages is not None) else 0,
    }


# --- sources ---------------------------------------------------------------

def _read_build_file(root: Path, url: str, host: str) -> str | None:
    """A sitemap URL, read as a file in the build output."""
    key = urls.path_of(url, host)
    if key is None:
        return None
    candidate = root / key.lstrip("/")
    if candidate.is_file():
        return candidate.read_text(encoding="utf-8", errors="replace")
    return None


def _fetch(url: str) -> str | None:
    """A document over HTTP, or None. Absence is a result here, not an error."""
    import urllib.request

    try:
        request = urllib.request.Request(
            url, headers={"User-Agent": f"Mozilla/5.0 (compatible; {TOOL_NAME}/{TOOL_VERSION})"}
        )
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return response.read().decode("utf-8", "replace")
    except Exception:  # noqa: BLE001 - any failure means "not readable", which is a finding
        return None


def _first_sitemap(directives: list[str], read: Callable[[str], str | None],
                   absolute: Callable[[str], str]) -> tuple[str, str] | None:
    """The site's sitemap, found the way D37 says: robots first, then convention."""
    for value in directives:
        url = absolute(value)
        body = read(url)
        if body is not None:
            return url, body
    for name in sitemaps.KNOWN_NAMES:
        url = absolute(name)
        body = read(url)
        if body is not None:
            return url, body
    return None


def run(config, live: bool = False, run: str | None = None, **_ignored) -> dict[str, Any]:
    """Read the three documents from the build output, or from the live site."""
    if live:
        read_url = _fetch
        robots = _fetch(config.site_url.rstrip("/") + "/robots.txt")
        llms = _fetch(config.site_url.rstrip("/") + "/llms.txt")
        found = _first_sitemap(
            sitemap_directives(robots or "") if robots else [],
            _fetch, lambda u: u if "://" in u else urljoin(config.site_url.rstrip("/") + "/", u.lstrip("/")),
        )
        source = {"kind": "live_site", "path": None}
        pages, served, ignored = None, None, 0
    else:
        page_set = pages_module.resolve(config, live=False)
        root = pages_module.find_static_dir(config.static_dir)
        read_url = lambda url: _read_build_file(root, url, config.domain)  # noqa: E731
        robots = _read_build_file(root, "/robots.txt", config.domain)
        llms = _read_build_file(root, "/llms.txt", config.domain)
        found = _first_sitemap(
            sitemap_directives(robots or "") if robots else [],
            read_url, lambda u: u,
        )
        source = page_set.source
        pages, served, ignored = page_set.pages, urls.served(root), page_set.ignored

    result = audit_sources(
        robots=robots,
        sitemap=found[1] if found else None,
        llms=llms,
        read_url=read_url,
        pages=pages,
        served=served,
        host=config.domain,
    )

    findings = result["findings"]
    critical = sum(1 for f in findings if f["severity"] == CRITICAL)

    return {
        "report_version": REPORT_VERSION,
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "crawl_mode": "live" if live else "static",
        "site": {"url": config.site_url, "domain": config.domain},
        "capability": "crawler-files",
        "source": source,
        "rules_run": list(active_checks(live)),
        "summary": {
            "robots_found": result["robots_found"],
            "sitemap_found": result["sitemap_found"],
            "sitemap_urls": result["sitemap_urls"],
            "llms_found": result["llms_found"],
            "checked_pages": result["checked_pages"] if not live else 0,
            "total_critical_issues": critical,
            "total_warnings": len(findings) - critical,
        },
        "findings": findings,
    }
