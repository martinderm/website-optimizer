"""Performance capability: what the build weighs and what blocks its first paint.

`references/performance.md` names budgets and causes; this capability measures
the half of them a build contains. Asset weight comes from file sizes,
render-blocking from `<script>` attributes, font behavior from `@font-face`
blocks in served stylesheets, wasted preloads from `<link rel="preload">`
against the file set, and third-party exposure from the origins the markup
references.

**Two shapes of finding.** Weight is per page: every page loads what it
declares, so an overweight stylesheet is overweight on each page that loads
it. Everything else is keyed on its target (D52): one blocking script, one
unundered font file, one missing preload target, one foreign origin — each
naming the pages involved. A shared template defect is one defect, not one per
page it renders into.

**Build-only.** File sizes exist only in a build, so `run()` raises on
`live=True` rather than weighing a crawl (D51 pattern). Lab and field numbers
— LCP, INP, CLS themselves, caching headers — need measurement this tool does
not do; `references/performance.md` says which half is advice.

**No double reporting.** A declared file the build does not contain is
`links`' or `images`' finding. These rules skip it rather than weighing zero
bytes: a 404 never reads as lightweight here.
"""

from __future__ import annotations

import posixpath
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ... import pages as pages_module
from ... import urls
from ...errors import CapabilityError
from ...page import Page
from ...report import TOOL_NAME, TOOL_VERSION

CRITICAL = "critical"
WARNING = "warning"
REPORT_VERSION = "1"

# Budgets from `references/performance.md`, in bytes on disk. Stored bytes are
# compared directly: compression shrinks text in transit, so a file over budget
# on disk is over budget served, while one under it may still be close — the
# finding says what was measured, not what the wire would carry.
BUDGET_CSS_BYTES = 100 * 1024
BUDGET_JS_BYTES = 200 * 1024
# The reference budgets the *hero* image. Which image is heroic is a heuristic
# this tool refuses (a heuristic finding is a false positive with a schedule),
# so the rule reads conservatively instead: the largest image on the page is
# weighed against the hero budget. Under it, every image is; over it, the page
# has an image-weight problem whatever the hero is.
BUDGET_IMAGE_BYTES = 200 * 1024
# The reference budgets fonts per weight, which is per file.
BUDGET_FONT_BYTES = 100 * 1024

FONT_EXTENSIONS = (".woff2", ".woff", ".ttf", ".otf", ".eot")
FONT_FACE_RE = re.compile(r"@font-face\s*\{([^}]*)\}", re.IGNORECASE | re.DOTALL)
FONT_DISPLAY_RE = re.compile(r"font-display\s*:", re.IGNORECASE)
CSS_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
CSS_URL_RE = re.compile(r"url\(\s*['\"]?([^'\"\)\s]+)['\"]?\s*\)", re.IGNORECASE)
SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")

CHECKS: tuple[str, ...] = (
    "perf.budget_exceeded",
    "perf.render_blocking_script",
    "perf.font_display_missing",
    "perf.preload_target_missing",
    "perf.third_party_origin",
)


def _finding(rule_id, severity, message, observed, expected, subject, location):
    return {
        "rule_id": rule_id, "severity": severity, "message": message,
        "observed": observed, "expected": expected, "subject": subject,
        "location": location,
    }


def _resolve(source: str, url: str, host: str) -> str | None:
    """The site-relative key a URL names, or None when it names another site.

    Absolute paths resolve against the site root; relative ones against the
    page's directory, the way a browser resolves them. Anything with a scheme
    other than http(s) — `data:`, `blob:`, `mailto:`, `foo:bar` — is not a
    retrievable file and returns None, as does anything on another host (which
    is the third-party rule's question, not this function's).
    """
    raw = (url or "").strip()
    if not raw:
        return None
    if raw.startswith("//"):
        raw = "https:" + raw
    if SCHEME_RE.match(raw) and not raw.lower().startswith(("http:", "https:")):
        return None
    if "://" in raw:
        return urls.path_of(raw, host)
    if raw.startswith("/"):
        return urls.key(raw)
    # Relative to the page's directory, the way a browser resolves it.
    # `posixpath.join`, not string concatenation: the directory of a top-level
    # page is `/`, and `"/" + "/" + raw` keeps a double slash that `served`
    # never holds, so root-level relative references would silently miss.
    directory = posixpath.dirname("/" + source)
    return urls.key(posixpath.join(directory, raw))


def _origin(url: str) -> str | None:
    """The `scheme://authority` of an http(s) URL, or None."""
    raw = (url or "").strip()
    if raw.startswith("//"):
        raw = "https:" + raw
    try:
        parsed = urlparse(raw)
    except ValueError:
        return None
    if parsed.scheme.lower() not in ("http", "https") or not parsed.hostname:
        return None
    return f"{parsed.scheme.lower()}://{parsed.hostname.lower()}"


def _is_first_party(origin: str, host: str) -> bool:
    """Whether an origin is the site itself: same bare host, with or without
    `www`, the same spelling rule `urls.path_of` uses (D38). A subdomain is
    not: the markup cannot show whether it is the site's own CDN or a CNAME to
    someone else's infrastructure, so the rule reports it and a person
    attributes it."""
    authority = origin.split("://", 1)[1]
    return urls.bare_host(authority) == urls.bare_host(host)


def _srcset_files(srcset: str | None) -> list[str]:
    """The URLs in a srcset. Candidates all download under some viewport, so
    weight counts every candidate, not only the default `src`."""
    if not srcset:
        return []
    files = []
    for candidate in srcset.split(","):
        parts = candidate.strip().split()
        if parts:
            files.append(parts[0])
    return files


def _file_size(root: Path, key: str) -> int | None:
    """Bytes on disk, or None when the build does not contain the file."""
    candidate = root / key.lstrip("/")
    if candidate.is_file():
        return candidate.stat().st_size
    return None


def budget_findings(pages: list[Page], root: Path, served: set[str], host: str) -> list[dict]:
    """Weight against the reference budgets, keyed on the file (D52).

    A heavy file in a site-wide template is one defect, not one per page it
    renders into — so css, js and font files are reported once each, naming
    the pages that load them. The page total still matters: when no single
    file is over budget but their sum is, the composition itself is the
    finding and the page is its subject. Images are page-local enough that
    the largest image per page stays a page finding (see the constant above
    for why the largest stands in for the hero).
    """
    findings = []
    css_files: dict[str, set[str]] = {}
    js_files: dict[str, set[str]] = {}
    css_sizes: dict[str, int] = {}
    js_sizes: dict[str, int] = {}
    font_files: dict[str, set[str]] = {}
    for page in pages:
        page_css: list[str] = []
        page_js: list[str] = []
        for sheet in page.stylesheets:
            key = _resolve(page.source, sheet["href"], host)
            if key is None or key not in served:
                continue
            size = _file_size(root, key)
            if size is None:
                continue
            css_files.setdefault(key, set()).add(page.source)
            css_sizes[key] = size
            page_css.append(key)
            for font_key in _font_files(root, key, page.source, host):
                font_files.setdefault(font_key, set()).add(page.source)
        for script in page.scripts:
            key = _resolve(page.source, script["src"], host)
            if key is None or key not in served:
                continue
            size = _file_size(root, key)
            if size is None:
                continue
            js_files.setdefault(key, set()).add(page.source)
            js_sizes[key] = size
            page_js.append(key)
        _composition_finding(findings, page.source, "Stylesheets", page_css,
                             css_sizes, BUDGET_CSS_BYTES)
        _composition_finding(findings, page.source, "Scripts", page_js,
                             js_sizes, BUDGET_JS_BYTES)
        largest_image = 0
        largest_name = ""
        for image in page.images:
            for candidate in [image["src"]] + _srcset_files(image["srcset"]):
                if not candidate:
                    continue
                key = _resolve(page.source, candidate, host)
                if key is None or key not in served:
                    continue
                size = _file_size(root, key)
                if size is None:
                    continue
                if size > largest_image:
                    largest_image, largest_name = size, key
        if largest_image > BUDGET_IMAGE_BYTES:
            findings.append(_finding(
                "perf.budget_exceeded", WARNING,
                f"The largest image on this page weighs {largest_image} bytes "
                f"against a {BUDGET_IMAGE_BYTES} hero budget: {largest_name}.",
                largest_image, f"<= {BUDGET_IMAGE_BYTES}", page.source, "page weight"))
    for key in sorted(css_files):
        if css_sizes[key] > BUDGET_CSS_BYTES:
            findings.append(_finding(
                "perf.budget_exceeded", WARNING,
                f"Stylesheet {key} weighs {css_sizes[key]} bytes against a "
                f"{BUDGET_CSS_BYTES} budget, loaded by "
                f"{len(css_files[key])} page(s).",
                css_sizes[key], f"<= {BUDGET_CSS_BYTES}", key, "page weight"))
    for key in sorted(js_files):
        if js_sizes[key] > BUDGET_JS_BYTES:
            findings.append(_finding(
                "perf.budget_exceeded", WARNING,
                f"Script {key} weighs {js_sizes[key]} bytes against a "
                f"{BUDGET_JS_BYTES} budget, loaded by "
                f"{len(js_files[key])} page(s).",
                js_sizes[key], f"<= {BUDGET_JS_BYTES}", key, "page weight"))
    for font_key in sorted(font_files):
        size = _file_size(root, font_key)
        if size is not None and size > BUDGET_FONT_BYTES:
            findings.append(_finding(
                "perf.budget_exceeded", WARNING,
                f"Font file {font_key} weighs {size} bytes against a "
                f"{BUDGET_FONT_BYTES} per-weight budget, loaded by "
                f"{len(font_files[font_key])} page(s).",
                size, f"<= {BUDGET_FONT_BYTES}", font_key, "page weight"))
    return findings


def _composition_finding(findings: list[dict], subject: str, kind: str,
                         keys: list[str], sizes: dict[str, int], budget: int) -> None:
    """The sum is over budget though no single file is.

    Reported on the page, because the composition lives there: several light
    files adding up is a template decision, not a file defect. Silent when a
    file finding already names the cause, so the two never stack.
    """
    total = sum(sizes[key] for key in keys)
    if total <= budget:
        return
    if any(sizes[key] > budget for key in keys):
        return
    findings.append(_finding(
        "perf.budget_exceeded", WARNING,
        f"{kind} on this page weigh {total} bytes against a {budget} "
        f"budget: no single file is over, the composition is "
        f"({', '.join(sorted(set(keys))) or 'nothing served'}).",
        total, f"<= {budget}", subject, "page weight"))


def _font_files(root: Path, css_key: str, source: str, host: str) -> list[str]:
    """Font files a stylesheet references, resolved the way the page resolves.

    `url()` targets inside the stylesheet are relative to the stylesheet, not
    the page — the one resolution here that is not page-relative.
    """
    candidate = root / css_key.lstrip("/")
    if not candidate.is_file():
        return []
    try:
        text = candidate.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    directory = posixpath.dirname(css_key)
    found = []
    for match in CSS_URL_RE.finditer(text):
        target = match.group(1).strip()
        if SCHEME_RE.match(target) and not target.lower().startswith(("http:", "https:")):
            continue
        if "://" in target:
            key = urls.path_of(target, host)
        elif target.startswith("/"):
            key = urls.key(target)
        else:
            key = urls.key(posixpath.join(directory, target))
        if key is None:
            continue
        if key.lower().endswith(FONT_EXTENSIONS):
            found.append(key)
    return found


def blocking_scripts(pages: list[Page], host: str) -> list[dict]:
    """Parser-blocking scripts, keyed on the resolved target.

    A classic script in `<head>` without `defer` or `async` stops the parser:
    nothing below it — content, styles, images — proceeds until it has loaded
    and run. `type="module"` defers by definition, and a script in `<body>`
    blocks only what follows it, which is the author's placement decision, not
    a first-paint defect. External or internal makes no difference to the
    parser, so both are judged; whether the host is foreign is the
    third-party rule's question. Grouped by resolved target, not by spelling:
    `/js/a.js` and `https://example.com/js/a.js` are one file and one finding.
    """
    by_src: dict[str, set[str]] = {}
    for page in pages:
        for script in page.scripts:
            if not script["in_head"]:
                continue
            if script["defer"] or script["async"]:
                continue
            if script["type"] == "module":
                continue
            target = _resolve(page.source, script["src"], host) or script["src"]
            by_src.setdefault(target, set()).add(page.source)
    findings = []
    for src in sorted(by_src):
        count = len(by_src[src])
        findings.append(_finding(
            "perf.render_blocking_script", WARNING,
            f"{count} page(s) load a parser-blocking <script> from {src} in "
            f"<head>: nothing below it paints until it has loaded and run. "
            f"`defer` or `async` moves it off the critical path.",
            src, "defer, async, or out of <head>", src, "head > script[src]"))
    return findings


def font_display_files(pages: list[Page], root: Path, served: set[str], host: str) -> list[dict]:
    """Stylesheets whose `@font-face` blocks omit `font-display`.

    Without it the browser hides text until the face arrives (or flashes
    unstyled text, depending on the browser's default): either way the first
    paint is not what the visitor keeps reading, which is layout shift of the
    textual kind. One finding per stylesheet — the fix is one declaration per
    block, and the file is where it lands.
    """
    css_keys: dict[str, None] = {}
    for page in pages:
        for sheet in page.stylesheets:
            key = _resolve(page.source, sheet["href"], host)
            if key is not None and key in served:
                css_keys[key] = None
    findings = []
    for key in sorted(css_keys):
        candidate = root / key.lstrip("/")
        if not candidate.is_file():
            continue
        try:
            text = candidate.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        # Comments are not declarations: `/* font-display: swap */` in a
        # commented-out block must not silence a real miss.
        faces = FONT_FACE_RE.findall(CSS_COMMENT_RE.sub("", text))
        if not faces:
            continue
        missing = sum(1 for block in faces if not FONT_DISPLAY_RE.search(block))
        if missing:
            findings.append(_finding(
                "perf.font_display_missing", WARNING,
                f"{missing}/{len(faces)} @font-face block(s) in {key} declare "
                f"no font-display: text waits for the face or flashes unstyled "
                f"before it arrives. `font-display: swap` keeps the page readable.",
                None, "font-display in every @font-face", key,
                "stylesheet > @font-face"))
    return findings


def preload_targets(pages: list[Page], root: Path, served: set[str], host: str) -> list[dict]:
    """Preloads the build does not serve, keyed on target.

    A preload is a high-priority fetch instruction: one pointing at nothing
    spends the browser's earliest request on a 404. Only foreign preloads are
    skipped — the build cannot contain another host. A first-party absolute
    URL resolves like a relative one; skipping it would let the most explicit
    spelling of a missing file pass silently.
    """
    by_href: dict[str, set[str]] = {}
    for page in pages:
        for preload in page.preloads:
            href = preload["href"]
            origin = _origin(href)
            if origin is not None and not _is_first_party(origin, host):
                continue
            key = _resolve(page.source, href, host)
            if key is None or key in served:
                continue
            by_href.setdefault(key, set()).add(page.source)
    findings = []
    for key in sorted(by_href):
        declarers = sorted(by_href[key])
        findings.append(_finding(
            "perf.preload_target_missing", CRITICAL,
            f"{len(declarers)} page(s) preload {key}, which the build does not "
            f"serve: {', '.join(declarers)}.",
            None, "a file the build serves", key, "head > link[rel=preload]"))
    return findings


def third_party_origins(pages: list[Page], host: str) -> list[dict]:
    """Foreign origins the markup references, one finding each.

    The reference asks for third parties "named and justified, individually".
    The tool can only do the first half: one inventory line per origin with a
    page count, so a reader sees the whole exposure in one place. Justification
    stays human — a tag manager the team chose and a tracker someone pasted in
    2019 look identical in markup, and a rule that cannot tell them apart must
    not pretend it can. A subdomain of the site itself is delivery, not a third
    party.
    """
    by_origin: dict[str, set[str]] = {}
    for page in pages:
        addresses = (
            [script["src"] for script in page.scripts]
            + [sheet["href"] for sheet in page.stylesheets]
            + [preload["href"] for preload in page.preloads]
            + [frame["src"] for frame in page.iframes]
            + _page_urls_of_images(page)
        )
        for address in addresses:
            origin = _origin(address)
            if origin is None or _is_first_party(origin, host):
                continue
            by_origin.setdefault(origin, set()).add(page.source)
    findings = []
    for origin in sorted(by_origin):
        count = len(by_origin[origin])
        findings.append(_finding(
            "perf.third_party_origin", WARNING,
            f"{origin} is referenced by {count} page(s). The markup cannot "
            f"show whether that is the site's own infrastructure or someone "
            f"else's — name and justify each origin, individually.",
            count, "first-party delivery, or a named justification", origin,
            "markup > external reference"))
    return findings


def _page_urls_of_images(page: Page) -> list[str]:
    """Image addresses, including every srcset candidate."""
    found = [image["src"] for image in page.images if image["src"]]
    for image in page.images:
        found.extend(_srcset_files(image["srcset"]))
    return found


def audit_pages(pages: list[Page], root: Path, host: str) -> dict[str, Any]:
    """Run the five performance rules over a page set and the build it lives in.

    The 404 page is exempt: it is not a view, so it is neither weighed nor
    scanned. Pages excluded by `ignore_path` never reach this function.
    """
    served = urls.served(root)
    weighed = [page for page in pages if not page.is_404]
    findings: list[dict] = []
    findings += budget_findings(weighed, root, served, host)
    findings += blocking_scripts(weighed, host)
    findings += font_display_files(weighed, root, served, host)
    findings += preload_targets(weighed, root, served, host)
    findings += third_party_origins(weighed, host)
    return {
        "findings": findings,
        "rules_run": list(CHECKS),
        "budgets_exceeded": sum(1 for f in findings if f["rule_id"] == "perf.budget_exceeded"),
        "third_party_origins": sum(1 for f in findings if f["rule_id"] == "perf.third_party_origin"),
        "pages_weighed": len(weighed),
    }


def to_report(result: dict[str, Any], host: str, site_url: str, source: dict) -> dict[str, Any]:
    """The wire shape: counts plus findings, conforming to the capability schema."""
    findings = result["findings"]
    critical = sum(1 for f in findings if f["severity"] == CRITICAL)
    return {
        "report_version": REPORT_VERSION,
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "crawl_mode": "static",
        "site": {"url": site_url, "domain": host},
        "capability": "performance",
        "source": source,
        "rules_run": result["rules_run"],
        "summary": {
            "audited_pages": result["pages_weighed"],
            "ignored_pages": 0,
            "budgets_exceeded": result["budgets_exceeded"],
            "third_party_origins": result["third_party_origins"],
            "total_critical_issues": critical,
            "total_warnings": len(findings) - critical,
        },
    }


def run(config, live: bool = False, run: str | None = None, **_ignored) -> dict[str, Any]:
    """Weigh the configured build output and scan what blocks its first paint."""
    if live:
        raise CapabilityError(
            "Performance needs the whole build; file sizes exist only in one.\n\n"
            "A live crawl weighs the pages inside its limit, so every shared "
            "stylesheet would be guessed at and every file size approximated. "
            "That report would describe the crawl, not the site.\n\n"
            "Run it against built output instead:\n"
            "  python scripts/wo.py performance"
        )

    page_set = pages_module.resolve(config, live=False)
    root = pages_module.find_static_dir(config.static_dir)
    result = audit_pages(page_set.pages, root, config.domain)
    report = to_report(result, config.domain, config.site_url, page_set.source)
    report["summary"]["ignored_pages"] = page_set.ignored
    return report
