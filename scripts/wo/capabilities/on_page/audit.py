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

from ... import pages as pages_module
from ...page import Page
from ...report import TOOL_NAME, TOOL_VERSION

# Re-exported. Path resolution now lives in `wo.pages` because three
# capabilities need it and one copy is the only way it stays one rule. Kept
# importable from here because the parity tests reach for it by this name, and
# moving a function should not silently break a caller that never changed.
find_static_dir = pages_module.find_static_dir

CRITICAL = "critical"
WARNING = "warning"

REPORT_VERSION = "1"


def _finding(
    rule_id: str,
    severity: str,
    message: str,
    observed: Any,
    expected: Any,
    subject: str,
    location: str,
) -> dict[str, Any]:
    """One atomic observation. Never carries page prose beyond the value itself."""
    return {
        "rule_id": rule_id,
        "severity": severity,
        "message": message,
        "observed": observed,
        "expected": expected,
        "subject": subject,
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
    if not site_url:
        return []

    expected_base = site_url.rstrip("/")
    if page.canonical.startswith(expected_base):
        return []

    # A different host is a different kind of thing from a different path.
    #
    # `www` versus the apex domain is the most common WordPress misconfiguration
    # there is, and it makes every page report a canonical mismatch at once. The
    # pages are not wrong: they all agree, and the disagreement is with the
    # configured site_url. Reporting that as a per-page critical defect buries a
    # configuration entry under twelve identical errors and trains the reader to
    # ignore the rule.
    expected = _urlparse(expected_base)
    actual = _urlparse(page.canonical)

    if actual.netloc and actual.netloc != expected.netloc:
        return [_finding(
            "canonical.host_differs", WARNING,
            f"Canonical points at host '{actual.netloc}' but site_url names "
            f"'{expected.netloc}'. The site canonicalises to one host; if that is "
            f"'{actual.netloc}', set [site] url to it.",
            page.canonical, expected.netloc, page.source, "head > link[rel=canonical]")]

    return [_finding("canonical.mismatch", CRITICAL,
                     f"Canonical URL '{page.canonical}' does not match expected "
                     f"site base URL '{site_url}'",
                     page.canonical, expected_base, page.source,
                     "head > link[rel=canonical]")]


def _urlparse(url: str):
    from urllib.parse import urlparse

    return urlparse(url if "//" in url else f"//{url}")


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

# Every rule_id this capability can emit, whether or not it fired. A report that
# lists only failures cannot tell "the page is clean" apart from "this check did
# not run" — and `compare` needs exactly that distinction to tell a new rule
# from a broken page. Maintained with RULES; a test enforces the agreement.
CHECKS: tuple[str, ...] = (
    "title.missing",
    "description.missing", "description.short", "description.long",
    "canonical.missing", "canonical.mismatch", "canonical.host_differs",
    "lang.missing",
    "h1.missing", "h1.multiple",
    "og.title.missing", "og.image.missing", "og.description.missing",
    "twitter.card.missing",
    "main.missing", "skiplink.missing",
    "img.alt.missing",
    "robots.noindex",
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

def run(config, ignore_noindex: bool = False, live: bool = False,
        run: str | None = None) -> dict[str, Any]:
    """Audit a site and return a report document.

    Static build output by default, rendered pages with `live=True`. Both arrive
    here as `Page` objects, so every rule above is written once and behaves
    identically on either source. A rule that only worked on files would have
    been a rule about the build, not about the site.
    """
    page_set = pages_module.resolve(config, live=live, run=run)

    findings: list[dict] = []
    page_records: list[dict] = []

    for page in page_set.pages:
        findings += audit_page(page, config.site_url, ignore_noindex)
        page_records.append({
            "source": page.source,
            "title": page.title,
            "canonical": page.canonical,
            "description_length": page.description_length,
            "og_image": page.og.get("og:image"),
            "schemas": page.schemas,
            "h1_count": page.h1_count,
        })

    critical = sum(1 for f in findings if f["severity"] == CRITICAL)
    pages_with_findings = len({f["subject"] for f in findings})
    audited = len(page_set.pages)

    report = {
        "report_version": REPORT_VERSION,
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "crawl_mode": page_set.mode,
        "site": {"url": config.site_url, "domain": config.domain},
        "capability": "on-page",
        "source": page_set.source,
        "rules_run": list(CHECKS),
        "summary": {
            "total_html_files": audited,
            "audited_pages": audited,
            "ignored_pages": page_set.ignored,
            "clean_pages": audited - pages_with_findings,
            "pages_with_findings": pages_with_findings,
            "total_critical_issues": critical,
            "total_warnings": len(findings) - critical,
        },
        "pages": page_records,
        "findings": findings,
    }
    if page_set.crawl is not None:
        report["crawl"] = page_set.crawl
    return report