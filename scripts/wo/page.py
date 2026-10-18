"""Fact extraction from a single HTML page.

Scope rule (decision D13): this module extracts *fields* only. It never retains
body text, comments, or any prose supplied by the page. A finding quotes an
extracted value and its source location, never a passage of page content.

Keeping the document free of page text is not tidiness, it is the boundary that
makes an audit of an untrusted site safe to read: whatever a crawled page
contains, it cannot travel forward through this module into a report or into an
agent context.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

OG_PROPERTIES = ("og:title", "og:description", "og:image", "og:url", "og:type", "og:locale")
TWITTER_NAMES = ("twitter:card", "twitter:image")
ICON_RELS = ("icon", "apple-touch-icon", "manifest", "mask-icon")


def _int_or_none(value: str | None) -> int | None:
    """Dimensions only count when the markup states a number, not a string."""
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


@dataclass
class Page:
    """The audit-relevant facts of one page. Fields, never prose."""

    source: str = ""
    is_404: bool = False
    title: str = ""
    title_found: bool = False
    lang: str | None = None
    description: str | None = None
    canonical: str | None = None
    robots: str | None = None
    og: dict[str, str] = field(default_factory=dict)
    twitter: dict[str, str] = field(default_factory=dict)
    h1_count: int = 0
    has_main: bool = False
    has_skip_link: bool = False
    images_total: int = 0
    images_missing_alt: int = 0
    schemas: list[str] = field(default_factory=list)
    # Per-image delivery facts. `alt` is reduced to presence and length on
    # purpose: the value itself is authored prose, and a report has no use for it.
    images: list[dict] = field(default_factory=list)
    # Declared icons, so the images capability can check whether the referenced
    # files actually exist in the build output.
    icons: list[dict] = field(default_factory=list)
    # Link targets, so the links capability can build the site's internal link
    # graph. Only `href` is kept: the words inside an <a> are authored prose, and
    # this module holds no prose (D13). The consequence is stated rather than
    # hidden — anchor-text quality is a rule this tool cannot measure, and
    # `references/internal-linking.md` says so next to the guidance.
    links: list[dict] = field(default_factory=list)
    # `<video>` facts the images capability checks. A video normally carries its
    # sources as `<source>` children rather than a `src`, so absence of `src` is
    # not a defect and is not recorded.
    videos: list[dict] = field(default_factory=list)
    # Delivery facts the performance capability weighs: external scripts with
    # their loading attributes, stylesheets, preloads, and embeds. Only
    # addresses and delivery attributes are kept — a URL is a field, and
    # `defer`/`async`/`as` describe delivery, not content. Inline script and
    # style bodies are not retained: they are authored code, and no rule reads
    # them (D13).
    scripts: list[dict] = field(default_factory=list)
    stylesheets: list[dict] = field(default_factory=list)
    preloads: list[dict] = field(default_factory=list)
    iframes: list[dict] = field(default_factory=list)

    @property
    def description_length(self) -> int:
        return len(self.description) if self.description else 0


class _Extractor(HTMLParser):
    """Collects audit fields. Deliberately has no attribute for body text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._in_title = False
        self._in_json_ld = False
        self._in_head = False
        self._title_parts: list[str] = []
        self._json_ld_chunks: list[str] = []
        self.page = Page(source="")

    def handle_starttag(self, tag, attrs):
        attr = {k.lower(): (v or "") for k, v in attrs}

        if tag == "html":
            self.page.lang = attr.get("lang")
        elif tag == "head":
            self._in_head = True
        elif tag == "title":
            self._in_title = True
            self.page.title_found = True
        elif tag == "meta":
            self._handle_meta(attr)
        elif tag == "link":
            if attr.get("rel", "").lower() == "canonical":
                self.page.canonical = attr.get("href", "").strip()
            elif attr.get("rel", "").lower() in ICON_RELS:
                self.page.icons.append({
                    "rel": attr.get("rel", "").lower(),
                    "href": attr.get("href", "").strip(),
                    "sizes": attr.get("sizes", "").strip() or None,
                    "type": attr.get("type", "").strip() or None,
                })
            else:
                rels = set(attr.get("rel", "").lower().split())
                href = attr.get("href", "").strip()
                if "stylesheet" in rels and href:
                    self.page.stylesheets.append({"href": href})
                if "preload" in rels and href:
                    self.page.preloads.append({
                        "href": href,
                        "as": attr.get("as", "").strip().lower() or None,
                    })
        elif tag == "h1":
            self.page.h1_count += 1
        elif tag == "main":
            self.page.has_main = True
        elif tag == "a":
            href = attr.get("href", "")
            if "#main-content" in href or "skip-link" in attr.get("class", ""):
                self.page.has_skip_link = True
            # Only the target is kept, not the element's text. An `<a>` with no
            # `href` at all is not a link; one with an empty `href` is a link to
            # the current page, and the capability resolves that rather than this
            # module deciding it is not one.
            if "href" in attr:
                self.page.links.append({"href": href.strip()})
        elif tag == "video":
            self.page.videos.append({
                "poster": attr.get("poster", "").strip(),
                "preload": (attr.get("preload") or "").strip().lower() or None,
            })
        elif tag == "img":
            self.page.images_total += 1
            alt_present = "alt" in attr
            if not alt_present:
                self.page.images_missing_alt += 1
            alt_value = attr.get("alt") or ""
            self.page.images.append({
                "src": attr.get("src", "").strip(),
                # `src` absent and `src=""` parse to the same empty string but are
                # different defects: the empty attribute makes the browser request
                # the page URL as an image. The rule that reports this needs to
                # tell them apart, so the presence of the key is kept.
                "src_present": "src" in attr,
                "srcset": attr.get("srcset", "").strip() or None,
                "sizes": attr.get("sizes", "").strip() or None,
                "width": _int_or_none(attr.get("width")),
                "height": _int_or_none(attr.get("height")),
                "loading": (attr.get("loading") or "").strip().lower() or None,
                "alt_present": alt_present,
                "alt_length": len(alt_value),
            })
        elif tag == "script":
            if attr.get("type", "").lower() == "application/ld+json":
                self._in_json_ld = True
            elif "src" in attr and attr.get("src", "").strip():
                self.page.scripts.append({
                    "src": attr.get("src", "").strip(),
                    "defer": "defer" in attr,
                    "async": "async" in attr,
                    "type": attr.get("type", "").strip().lower(),
                    "in_head": self._in_head,
                })
        elif tag == "iframe":
            if "src" in attr and attr.get("src", "").strip():
                self.page.iframes.append({"src": attr.get("src", "").strip()})

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "head":
            self._in_head = False
        elif tag == "script" and self._in_json_ld:
            self._in_json_ld = False

    def handle_data(self, data):
        # Only two sinks are permitted: the title (a metadata field) and JSON-LD
        # (structured data, parsed below). Everything else is dropped on the floor.
        if self._in_title:
            self._title_parts.append(data)
        elif self._in_json_ld:
            self._json_ld_chunks.append(data)

    def _handle_meta(self, attr: dict[str, str]) -> None:
        name = attr.get("name", "").lower()
        prop = attr.get("property", "").lower()
        content = attr.get("content", "").strip()

        if name == "description":
            self.page.description = content
        elif name == "robots":
            self.page.robots = content
        elif name in TWITTER_NAMES:
            self.page.twitter[name] = content

        if prop in OG_PROPERTIES:
            self.page.og[prop] = content

    def finish(self) -> Page:
        self.page.title = "".join(self._title_parts).strip()
        for chunk in self._json_ld_chunks:
            raw = chunk.strip()
            if not raw:
                continue
            try:
                _collect_types(json.loads(raw), self.page.schemas)
            except (ValueError, TypeError):
                # Malformed JSON-LD is a page defect, not a crash. The schema
                # capability reports it; extraction stays quiet here.
                continue
        return self.page


def _collect_types(node, sink: list[str]) -> None:
    """Walk JSON-LD and record every @type encountered, including inside @graph."""
    if isinstance(node, dict):
        node_type = node.get("@type")
        if isinstance(node_type, str):
            sink.append(node_type)
        graph = node.get("@graph")
        if isinstance(graph, list):
            for item in graph:
                _collect_types(item, sink)
    elif isinstance(node, list):
        for item in node:
            _collect_types(item, sink)


def extract_page_from_html(html: str, source_label: str = "", is_404: bool = False) -> Page:
    """Extract audit fields from an HTML string.

    The entry point for a live crawl. Rendering a page and reading a file are
    the same question asked of two different sources, so they converge here
    rather than in each capability: a capability written against `Page` cannot
    tell where the markup came from, and cannot accidentally grow a rule that
    only works on one of them.
    """
    parser = _Extractor()
    parser.feed(html)
    page = parser.finish()
    page.source = source_label
    page.is_404 = is_404
    return page


def extract_page(file_path: Path, source_label: str | None = None) -> Page:
    """Extract audit fields from one HTML file."""
    file_path = Path(file_path)
    content = file_path.read_text(encoding="utf-8", errors="replace")
    page = extract_page_from_html(
        content,
        source_label=source_label if source_label is not None else file_path.name,
        is_404=file_path.name == "404.html",
    )
    return page


def iter_html_files(root: Path):
    """Yield every HTML file under root, as a stable, sorted sequence."""
    return sorted(Path(root).rglob("*.html"))