"""On-page capability: SEO and accessibility signals inside a single page.

Ported from `hugo-wizard/scripts/audit-site-seo.py`. Every rule keeps the
original message text so a parity check can compare findings exactly; the rule
set, its conditions and its severities are unchanged. Only the shape around them
changed: findings are atomic records instead of two loose lists of strings.

One capability per signal, one signal per finding. A rule sees a `Page` of
extracted fields and nothing else — in particular it never sees a verdict about
the page, which is what keeps a measurement from confirming a conclusion handed
to it (decision D15).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from ...page import Page, extract_page, iter_html_files
from ...report import TOOL_NAME, TOOL_VERSION

CRITICAL = "critical"
WARNING = "warning"

REPORT_VERSION = "1"


def _finding(
    rule_id: str,
    severity: str,
    message: str,
    observed: Any,
    expected: Any,
    page: str,
    location: str,
) -> dict[str, Any]:
    """One atomic observation. Never carries page prose beyond the value itself."""
    return {
        "rule_id": rule_id,
        "severity": severity,
        "message": message,
        "observed": observed,
        "expected": expected,
        "page": page,
        "location": location,
    }


# --- rules -----------------------------------------------------------------
# Each rule is a pure function of a Page. Order is fixed for stable reports.

def title_missing(page: Page) -> list[dict]:
    if not page.title_found or not page.title.strip():
        return [_finding("title.missing", CRITICAL, "Missing <title> tag",
                         None, "<title> present", page.source, "head > title")]
    return []


def description(page: Page) -> list[dict]:
    if not page.description:
        if page.is_404:
            return []
        return [_finding("description.missing", CRITICAL, "Missing meta description",
                         None, "meta[name=description]", page.source,
                         "head > meta[name=description]")]
    length = len(page.description)
    if length < 30:
        return [_finding("description.short", WARNING,
                         f"Meta description very short ({length} chars)",
                         length, ">= 30", page.source, "head > meta[name=description]")]
    if length > 300:
        return [_finding("description.long", WARNING,
                         f"Meta description unusually long ({length} chars)",
                         length, "<= 300", page.source, "head > meta[name=description]")]
    return []


def canonical(page: Page, site_url: str) -> list[dict]:
    if not page.canonical:
        if page.is_404:
            return []
        return [_finding("canonical.missing", CRITICAL, "Missing canonical link tag",
                         None, "link[rel=canonical]", page.source, "head > link[rel=canonical]")]
    if site_url:
        expected_base = site_url.rstrip("/")
        if not page.canonical.startswith(expected_base):
            return [_finding("canonical.mismatch", CRITICAL,
                             f"Canonical URL '{page.canonical}' does not match expected "
                             f"site base URL '{site_url}'",
                             page.canonical, expected_base, page.source,
                             "head > link[rel=canonical]")]
    return []


def lang_missing(page: Page) -> list[dict]:
    if not page.lang:
        return [_finding("lang.missing", CRITICAL, "Missing lang attribute on <html>",
                         None, "lang attribute", page.source, "html")]
    return []


def headings(page: Page) -> list[dict]:
    if page.h1_count == 0:
        return [_finding("h1.missing", CRITICAL, "Missing <h1> heading",
                         0, ">= 1", page.source, "body")]
    if page.h1_count > 1:
        return [_finding("h1.multiple", WARNING,
                         f"Multiple ({page.h1_count}) <h1> headings found",
                         page.h1_count, "1", page.source, "body")]
    return []


def open_graph(page: Page) -> list[dict]:
    findings = []
    if not page.og.get("og:title"):
        findings.append(_finding("og.title.missing", CRITICAL, "Missing og:title",
                                None, "meta[property=og:title]", page.source,
                                "head > meta[property=og:title]"))
    if not page.og.get("og:image"):
        findings.append(_finding("og.image.missing", CRITICAL, "Missing og:image",
                                None, "meta[property=og:image]", page.source,
                                "head > meta[property=og:image]"))
    if not page.og.get("og:description"):
        findings.append(_finding("og.description.missing", WARNING, "Missing og:description",
                                None, "meta[property=og:description]", page.source,
                                "head > meta[property=og:description]"))
    return findings


def twitter_card(page: Page) -> list[dict]:
    if not page.twitter.get("twitter:card"):
        return [_finding("twitter.card.missing", WARNING, "Missing twitter:card",
                         None, "meta[name=twitter:card]", page.source,
                         "head > meta[name=twitter:card]")]
    return []


def landmarks(page: Page) -> list[dict]:
    findings = []
    if not page.has_main:
        findings.append(_finding("main.missing", WARNING, "Missing <main> landmark",
                                False, True, page.source, "body > main"))
    if not page.has_skip_link:
        findings.append(_finding("skiplink.missing", WARNING, "Missing skip-link",
                                False, True, page.source, "body > a"))
    return findings


def image_alt(page: Page) -> list[dict]:
    if page.images_missing_alt > 0:
        return [_finding("img.alt.missing", CRITICAL,
                         f"{page.images_missing_alt}/{page.images_total} <img> missing alt attribute",
                         page.images_missing_alt, 0, page.source, "body > img")]
    return []


def robots_noindex(page: Page, ignore_noindex: bool) -> list[dict]:
    if page.robots and "noindex" in page.robots.lower() and not ignore_noindex:
        return [_finding("robots.noindex", WARNING,
                         f"Page marked as noindex: '{page.robots}'",
                         page.robots, "indexable", page.source, "head > meta[name=robots]")]
    return []


RULES: tuple[Callable[..., list[dict]], ...] = (
    title_missing,
    description,
    canonical,
    lang_missing,
    headings,
    open_graph,
    twitter_card,
    landmarks,
    image_alt,
    robots_noindex,
)


def audit_page(page: Page, site_url: str, ignore_noindex: bool = False) -> list[dict]:
    """Run every rule against one page and return atomic findings."""
    findings: list[dict] = []
    for rule in RULES:
        if rule is canonical:
            findings += rule(page, site_url)
        elif rule is robots_noindex:
            findings += rule(page, ignore_noindex)
        else:
            findings += rule(page)
    return findings


# --- directory audit -------------------------------------------------------

def find_static_dir(path: Path) -> Path:
    """Resolve `public/`, a bare HTML directory, or the path as given."""
    resolved = Path(path).resolve()
    if (resolved / "public").is_dir():
        return resolved / "public"
    if resolved.is_dir() and any(resolved.glob("*.html")):
        return resolved
    return resolved


def run(config, ignore_noindex: bool = False, pages: list[Path] | None = None) -> dict[str, Any]:
    """Audit a static output directory and return a report document."""
    target = find_static_dir(config.static_dir)
    if not target.exists():
        raise FileNotFoundError(
            f"Static output directory not found: {target}\n"
            f"Set [site] static_dir in site.optimizer.toml, or build the site first."
        )

    pattern = re.compile(config.ignore_path) if config.ignore_path else None
    html_files = pages if pages is not None else list(iter_html_files(target))

    findings: list[dict] = []
    page_records: list[dict] = []
    audited = 0
    ignored = 0

    for file_path in html_files:
        rel = Path(file_path).relative_to(target).as_posix()
        if pattern and pattern.search(rel):
            ignored += 1
            continue
        audited += 1
        page = extract_page(file_path, source_label=rel)
        findings += audit_page(page, config.site_url, ignore_noindex)
        page_records.append({
            "source": rel,
            "title": page.title,
            "canonical": page.canonical,
            "description_length": page.description_length,
            "og_image": page.og.get("og:image"),
            "schemas": page.schemas,
            "h1_count": page.h1_count,
        })

    critical = sum(1 for f in findings if f["severity"] == CRITICAL)
    pages_with_findings = len({f["page"] for f in findings})

    return {
        "report_version": REPORT_VERSION,
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "crawl_mode": config.crawl_mode,
        "site": {"url": config.site_url, "domain": config.domain},
        "source": {"kind": "static_dir", "path": _relative(target, config.workspace_root)},
        "summary": {
            "total_html_files": len(html_files),
            "audited_pages": audited,
            "ignored_pages": ignored,
            "clean_pages": audited - pages_with_findings,
            "pages_with_findings": pages_with_findings,
            "total_critical_issues": critical,
            "total_warnings": len(findings) - critical,
        },
        "pages": page_records,
        "findings": findings,
    }


def _relative(path: Path, root: Path) -> str:
    """Store workspace-relative paths so a report never leaks a local layout."""
    try:
        return Path(path).resolve().relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        return Path(path).name