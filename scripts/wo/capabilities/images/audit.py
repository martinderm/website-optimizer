"""Images capability: delivery, dimensions, formats, and icons.

Reads the built output directory, not a single page, because half of what matters
here is only visible across the site: an icon declared on every page but missing
from the build, or an image set whose files the build never emitted.

**Scope boundary.** The `alt` check belongs to the `on-page` capability and is not
repeated here. Duplicating it would produce two rules, two severities and two
sources of truth for one defect — the exact failure this skill exists to remove.
What is read from `alt` here is presence and length only.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ... import pages
from ...page import Page
from ...report import TOOL_NAME, TOOL_VERSION

CRITICAL = "critical"
WARNING = "warning"
REPORT_VERSION = "1"

MODERN_FORMATS = ("webp", "avif")
LEGACY_FORMATS = ("jpg", "jpeg", "png", "gif")

WIDTH_DESCRIPTORS = re.compile(r"\d+w")


def _finding(rule_id, severity, message, observed, expected, subject, location):
    return {
        "rule_id": rule_id, "severity": severity, "message": message,
        "observed": observed, "expected": expected, "subject": subject,
        "location": location,
    }


# --- per-image rules -------------------------------------------------------

def image_src_missing(page: Page) -> list[dict]:
    """An <img> the browser cannot fetch, whatever its other attributes say.

    Two different defects share one rule because both are fixed the same way —
    the template must emit a real URL:

    - `src` absent entirely: the placeholder waits for JavaScript and nothing
      loads until it runs.
    - `src` present but empty: worse. The HTML parser reads a bare `src`
      attribute as `src=""`, which resolves against the document, so the
      browser issues a real request for the HTML page itself as an image.

    Neither is a missing-dimension problem. There is no image to reserve space
    for, so this rule replaces the dimension and srcset findings for these
    elements rather than stacking on top of them.
    """
    findings = []
    for image in page.images:
        if image["src"]:
            continue
        if image["src_present"]:
            message = "<img> has an empty src: the browser requests the page URL as an image"
        else:
            message = "<img> has no src at all: it stays empty until JavaScript fills it"
        findings.append(_finding(
            "image.src_missing", WARNING, message,
            "src" if image["src_present"] else None,
            "a real image URL", page.source, "body > img"))
    return findings


def image_dimensions(page: Page) -> list[dict]:
    """Without width and height the browser cannot reserve space (CLS).

    An <img> with no src is excluded: nothing is downloaded, so it reserves no
    space and shifts nothing. It is reported once by `image.src_missing`.
    """
    findings = []
    for image in page.images:
        if not image["src"]:
            continue
        if image["width"] is None or image["height"] is None:
            missing = [d for d in ("width", "height") if image[d] is None]
            findings.append(_finding(
                "image.dimensions_missing", CRITICAL,
                f"<img> has no {' and no '.join(missing)}: {image['src']}",
                missing, ["width", "height"], page.source, "body > img"))
    return findings


def image_srcset(page: Page) -> list[dict]:
    """An image without a candidate set cannot adapt to the viewport.

    An <img> with no src is excluded for the same reason as in
    `image_dimensions`; there is no candidate to adapt.
    """
    findings = []
    for image in page.images:
        if not image["src"]:
            continue
        if not image["srcset"]:
            findings.append(_finding(
                "image.srcset_missing", WARNING,
                f"<img> has no srcset: {image['src'] or '(no src)'}",
                None, "srcset with width descriptors", page.source, "body > img"))
    return findings


def image_sizes(page: Page) -> list[dict]:
    """A width-descriptor srcset without `sizes` makes the browser pick wrongly."""
    findings = []
    for image in page.images:
        if image["srcset"] and WIDTH_DESCRIPTORS.search(image["srcset"]) and not image["sizes"]:
            findings.append(_finding(
                "image.sizes_missing", WARNING,
                f"<img> has a width-descriptor srcset but no sizes: {image['src']}",
                None, "sizes describing the layout width", page.source, "body > img"))
    return findings


def image_format(page: Page) -> list[dict]:
    """Legacy formats are fine as a source; they are not the best candidate."""
    findings = []
    for image in page.images:
        candidates = _all_candidates(image)
        if candidates and not any(_extension(c) in MODERN_FORMATS for c in candidates):
            findings.append(_finding(
                "image.format_legacy", WARNING,
                f"No modern format offered: {image['src']}",
                _extension(candidates[0]), MODERN_FORMATS, page.source, "body > img"))
    return findings


def image_lazy_loading(page: Page) -> list[dict]:
    """Missing loading attribute entirely is worth one note per page, not per image.

    Two findings, and the difference between them is the point.

    `loading_unset` fires when *no* image on the page declares a strategy. That is
    a defect on every one of them.

    `loading_partial` fires when some do and some do not. Those images are not
    necessarily wrong: the first one may be the hero, and a hero must be eager.
    A static audit cannot tell, so this is a recommendation rather than a verdict
    - it says the question is open and what would close it, instead of leaving
    the question unasked. On the reference sites this is the commoner case by a
    wide margin, and silently skipping it is how 121 pages once looked clean
    while 123 images had no strategy at all.
    """
    if not page.images:
        return []
    without = sum(1 for i in page.images if not i["loading"])

    if without == len(page.images):
        return [_finding(
            "image.loading_unset", WARNING,
            f"None of {len(page.images)} <img> declares a loading strategy",
            None, 'loading="lazy" or "eager"', page.source, "body > img")]

    if without:
        return [_finding(
            "image.loading_partial", WARNING,
            f"{without} of {len(page.images)} <img> declare no loading strategy while "
            f"{len(page.images) - without} do. The ones with a strategy are probably "
            f"above the fold, which would make these lazy-load candidates - but a "
            f"static audit cannot measure the fold. Close this with a live run that "
            f"measures it, not by guessing here.",
            without, "a strategy on every image",
            page.source, "body > img")]
    return []


def _all_candidates(image: dict) -> list[str]:
    entries = [image["src"] or ""]
    if image["srcset"]:
        entries += [part.strip().split(" ")[0] for part in image["srcset"].split(",") if part.strip()]
    return [e for e in entries if e]


def _extension(url: str) -> str:
    suffix = url.split("?")[0].rsplit(".", 1)[-1].lower() if "." in url.rsplit("/", 1)[-1] else ""
    return suffix


# --- site-wide rules -------------------------------------------------------

def icons_declared(page: Page) -> list[dict]:
    if page.icons:
        return []
    return [_finding(
        "icon.none_declared", WARNING,
        "No favicon or app icon is declared",
        0, ">= 1", page.source, "head > link[rel=icon]")]


def icon_files_present(page: Page, root: Path | None) -> list[dict]:
    """A declared icon that the build never emitted is the classic silent fault."""
    if root is None:
        return []
    findings = []
    for icon in page.icons:
        href = icon["href"]
        if not href or href.startswith(("http://", "https://", "data:")):
            continue
        candidate = root / href.lstrip("/")
        if not candidate.is_file():
            findings.append(_finding(
                "icon.file_missing", CRITICAL,
                f"Declared icon is not in the build output: {href}",
                None, href, page.source, f"head > link[rel={icon['rel']}]"))
    return findings


def og_image_absolute(page: Page) -> list[dict]:
    """Scrapers do not resolve relative og:image URLs."""
    href = page.og.get("og:image")
    if href and not href.startswith(("http://", "https://")):
        return [_finding(
            "image.og_relative", WARNING,
            f"og:image is not an absolute URL: {href}",
            href, "absolute URL", page.source, "head > meta[property=og:image]")]
    return []


# --- video rules -----------------------------------------------------------
#
# `<video>` is checked here rather than in a capability of its own because the
# mechanism is the one this capability already has: something declared in the
# markup, checked against what the build emitted. Two rules would not pay for a
# third folder, and a rule prefix of its own keeps them findable.
#
# Captions are deliberately not checked. A `<track>` presence check is markup and
# would be easy; whether the captions are *right* needs a person, and reporting
# presence only would read as a clearance. `references/video.md` says so.

def video_poster_missing(page: Page) -> list[dict]:
    """A video with no poster paints a black rectangle until it is played."""
    if not page.videos:
        return []
    without = sum(1 for video in page.videos if not video["poster"])
    if not without:
        return []
    return [_finding(
        "video.poster_missing", WARNING,
        f"{without}/{len(page.videos)} <video> declare no poster. Until it is "
        f"played, a video without one is a black rectangle — and a poster can be "
        f"a real image, not only a first frame.",
        without, 0, page.source, "body > video")]


def video_poster_file_missing(page: Page, root: Path | None) -> list[dict]:
    """A poster the build never emitted: the same silent fault as a missing icon."""
    if root is None:
        return []
    findings = []
    for video in page.videos:
        poster = video["poster"]
        if not poster or poster.startswith(("http://", "https://", "data:")):
            continue
        if not (root / poster.lstrip("/")).is_file():
            findings.append(_finding(
                "video.poster_file_missing", CRITICAL,
                f"A <video> declares a poster the build does not contain: {poster}",
                None, poster, page.source, "body > video"))
    return findings


def video_preload_unset(page: Page) -> list[dict]:
    """No video on the page says how eagerly it should be fetched.

    Per page rather than per video, exactly as the two `loading` rules are: a page
    where nothing declares a `preload` has one decision to make, not four. Absent
    leaves it to the browser, which for a large file is a real cost on a page
    whose video is not the reason anyone came.
    """
    if not page.videos:
        return []
    if any(video["preload"] for video in page.videos):
        return []
    return [_finding(
        "video.preload_unset", WARNING,
        f"None of {len(page.videos)} <video> declares a preload strategy, so the "
        f"browser decides. `preload=\"metadata\"` or `\"none\"` bounds what a "
        f"visitor downloads before they asked for the video.",
        None, 'preload="metadata" or "none"', page.source, "body > video")]


RULES = (
    image_src_missing,
    image_dimensions,
    image_srcset,
    image_sizes,
    image_format,
    image_lazy_loading,
    og_image_absolute,
)

# Rules that need the build directory rather than the page. They leave `rules_run`
# in a live run, because a rule that cannot fire must never read as one that found
# nothing.
STATIC_ONLY: tuple[str, ...] = ("icon.file_missing", "video.poster_file_missing")

CHECKS: tuple[str, ...] = (
    "image.src_missing",
    "image.dimensions_missing",
    "image.srcset_missing",
    "image.sizes_missing",
    "image.format_legacy",
    "image.loading_unset",
    "image.loading_partial",
    "image.og_relative",
    "icon.none_declared",
    "icon.file_missing",
    "video.poster_missing",
    "video.poster_file_missing",
    "video.preload_unset",
)


def audit_page(page: Page, root: Path | None = None) -> list[dict]:
    findings: list[dict] = []
    for rule in RULES:
        findings += rule(page)
    findings += icons_declared(page)
    findings += icon_files_present(page, root)
    findings += video_poster_missing(page)
    findings += video_poster_file_missing(page, root)
    findings += video_preload_unset(page)
    return findings


def run(config, live: bool = False, run: str | None = None, **_) -> dict[str, Any]:
    page_set = pages.resolve(config, live=live, run=run)
    # The two file-existence rules compare a declared path against files in a
    # build directory. A live crawl has no directory, so they cannot run and say
    # so rather than passing vacuously — a rule that cannot fire must not be
    # reported as a rule that found nothing.
    #
    # `find_static_dir` rather than `config.static_dir`: a workspace whose
    # `static_dir` is its own root and which builds into `public/` would otherwise
    # have its icons checked against the wrong directory.
    root = pages.find_static_dir(config.static_dir) if page_set.mode == "static" else None
    active_checks = list(CHECKS) if root is not None else [
        c for c in CHECKS if c not in STATIC_ONLY
    ]

    findings: list[dict] = []
    pages_with_images = 0
    images_total = 0

    for page in page_set.pages:
        if page.images:
            pages_with_images += 1
        images_total += len(page.images)
        findings += audit_page(page, root)

    critical = sum(1 for f in findings if f["severity"] == CRITICAL)
    subjects = {f["subject"] for f in findings}
    audited = len(page_set.pages)

    report = {
        "report_version": REPORT_VERSION,
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "crawl_mode": page_set.mode,
        "site": {"url": config.site_url, "domain": config.domain},
        "capability": "images",
        "rules_run": active_checks,
        "source": page_set.source,
        "summary": {
            "audited_pages": audited,
            "ignored_pages": page_set.ignored,
            "pages_with_images": pages_with_images,
            "images_total": images_total,
            "pages_with_findings": len(subjects),
            "total_critical_issues": critical,
            "total_warnings": len(findings) - critical,
        },
        "findings": findings,
    }
    if page_set.crawl is not None:
        report["crawl"] = page_set.crawl
    return report