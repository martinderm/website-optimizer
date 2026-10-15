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

from ...page import Page, extract_page, iter_html_files
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

def image_dimensions(page: Page) -> list[dict]:
    """Without width and height the browser cannot reserve space (CLS)."""
    findings = []
    for image in page.images:
        if image["width"] is None or image["height"] is None:
            missing = [d for d in ("width", "height") if image[d] is None]
            findings.append(_finding(
                "image.dimensions_missing", CRITICAL,
                f"<img> has no {' and no '.join(missing)}: {image['src'] or '(no src)'}",
                missing, ["width", "height"], page.source, "body > img"))
    return findings


def image_srcset(page: Page) -> list[dict]:
    """An image without a candidate set cannot adapt to the viewport."""
    findings = []
    for image in page.images:
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
    """Missing loading attribute entirely is worth one note per page, not per image."""
    if not page.images:
        return []
    without = sum(1 for i in page.images if not i["loading"])
    if without == len(page.images):
        return [_finding(
            "image.loading_unset", WARNING,
            f"None of {len(page.images)} <img> declares a loading strategy",
            None, 'loading="lazy" or "eager"', page.source, "body > img")]
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


RULES = (
    image_dimensions,
    image_srcset,
    image_sizes,
    image_format,
    image_lazy_loading,
    og_image_absolute,
)

CHECKS: tuple[str, ...] = (
    "image.dimensions_missing",
    "image.srcset_missing",
    "image.sizes_missing",
    "image.format_legacy",
    "image.loading_unset",
    "image.og_relative",
    "icon.none_declared",
    "icon.file_missing",
)


def audit_page(page: Page, root: Path | None = None) -> list[dict]:
    findings: list[dict] = []
    for rule in RULES:
        findings += rule(page)
    findings += icons_declared(page)
    findings += icon_files_present(page, root)
    return findings


def find_static_dir(path: Path) -> Path:
    resolved = Path(path).resolve()
    if (resolved / "public").is_dir():
        return resolved / "public"
    if resolved.is_dir() and any(resolved.glob("*.html")):
        return resolved
    return resolved


def run(config, **_) -> dict[str, Any]:
    target = find_static_dir(config.static_dir)
    if not target.exists():
        raise FileNotFoundError(
            f"Static output directory not found: {target}\n"
            f"Set [site] static_dir in site.optimizer.toml, or build the site first."
        )

    pattern = re.compile(config.ignore_path) if config.ignore_path else None
    findings: list[dict] = []
    audited = 0
    ignored = 0
    images_total = 0
    pages_with_images = 0

    for file_path in iter_html_files(target):
        rel = Path(file_path).relative_to(target).as_posix()
        if pattern and pattern.search(rel):
            ignored += 1
            continue
        audited += 1
        page = extract_page(file_path, source_label=rel)
        if page.images:
            pages_with_images += 1
        images_total += len(page.images)
        findings += audit_page(page, target)

    critical = sum(1 for f in findings if f["severity"] == CRITICAL)
    subjects = {f["subject"] for f in findings}

    return {
        "report_version": REPORT_VERSION,
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "crawl_mode": "static",
        "site": {"url": config.site_url, "domain": config.domain},
        "capability": "images",
        "rules_run": list(CHECKS),
        "source": {"kind": "static_dir", "path": _relative(target, config.workspace_root)},
        "summary": {
            "audited_pages": audited,
            "ignored_pages": ignored,
            "pages_with_images": pages_with_images,
            "images_total": images_total,
            "pages_with_findings": len(subjects),
            "total_critical_issues": critical,
            "total_warnings": len(findings) - critical,
        },
        "findings": findings,
    }


def _relative(path: Path, root: Path) -> str:
    try:
        return Path(path).resolve().relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        return Path(path).name