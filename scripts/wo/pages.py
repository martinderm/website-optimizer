"""Where a run's pages come from: a build directory, or a live browser.

One resolver for every capability. A capability asks for pages and gets `Page`
objects; it never learns whether they were read from disk or rendered, and cannot
therefore grow a rule that only works on one of them. That is the whole reason
static and live share a code path rather than each having a `--live` branch.

The trade is deliberate: the report cannot describe a live crawl as precisely as
a static one, because a browser run has no directory to point at. `source` says
what was read and how, and `crawl` carries the qualifiers — failures, limits,
whether a consent wall was suspected — as first-class fields rather than as a
footnote in the message.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import crawl as crawl_module
from .errors import CapabilityError
from .page import Page, extract_page, iter_html_files


@dataclass
class PageSet:
    """Pages for one run, plus how they were obtained."""

    pages: list[Page] = field(default_factory=list)
    mode: str = "static"
    source: dict[str, Any] = field(default_factory=dict)
    crawl: dict[str, Any] | None = None
    ignored: int = 0
    # page.source -> rendered markup, live mode only.
    #
    # Most rules read the extracted fields and never need this. `schema` does:
    # JSON-LD is a document, not a field, and reducing it to a list of type
    # names loses exactly the structure that capability exists to check. It is
    # kept out of `Page` on purpose — that module never holds page prose (D13) —
    # so a capability that genuinely needs the document asks for it explicitly.
    raw: dict[str, str] = field(default_factory=dict)


def find_static_dir(path: Path) -> Path:
    """Resolve `public/`, a bare HTML directory, or the path as given.

    Identical in all three capabilities that read build output. Duplicated three
    times it would be three places to fix the next time a Hugo layout changes.
    """
    resolved = Path(path).resolve()
    if (resolved / "public").is_dir():
        return resolved / "public"
    if resolved.is_dir() and any(resolved.glob("*.html")):
        return resolved
    return resolved


def resolve(config, live: bool = False, run: str | None = None) -> PageSet:
    """The pages to audit, from the configured source.

    `live` is the only switch, and it is passed on a command line by a person.
    Nothing in the config turns it on: D26 decided that a crawl must never run
    because a hook fired.
    """
    if live:
        return _resolve_live(config, run)
    return _resolve_static(config)


def _resolve_static(config) -> PageSet:
    target = find_static_dir(config.static_dir)
    if not target.exists():
        raise CapabilityError(
            f"Static output directory not found: {target}\n"
            f"Set [site] static_dir in site.optimizer.toml, or build the site first.\n"
            f"For a site without build output, run with --live instead."
        )

    pattern = re.compile(config.ignore_path) if config.ignore_path else None
    pages: list[Page] = []
    ignored = 0

    for file_path in iter_html_files(target):
        rel = Path(file_path).relative_to(target).as_posix()
        if pattern and pattern.search(rel):
            ignored += 1
            continue
        pages.append(extract_page(file_path, source_label=rel))

    return PageSet(
        pages=pages,
        mode="static",
        source={"kind": "static_dir", "path": _relative(target, config.workspace_root)},
        ignored=ignored,
    )


def _resolve_live(config, run: str | None) -> PageSet:
    urls = crawl_module.resolve_start_urls(config)
    limit = int(config.crawl.get("max_pages", 200))
    if len(urls) > limit:
        urls = urls[:limit]

    result = crawl_module.crawl(urls, config, run=run)

    # A wall produces a confident, entirely wrong report. Refusing is the honest
    # outcome; a finding about a cookie dialog is not a finding about the site.
    if result.wall_suspected:
        raise CapabilityError(
            "The crawl is reading a page that is not the site.\n\n"
            f"{result.wall_reason}\n\n"
            "No findings were produced. To audit a site like this, either:\n"
            "  - accept the cookie banner once in the browser session and re-run, or\n"
            "  - run against build output with --static instead."
        )

    artifacts = None
    if result.artifact_dir:
        try:
            artifacts = result.artifact_dir.relative_to(config.workspace_root).as_posix()
        except ValueError:
            artifacts = result.artifact_dir.name

    return PageSet(
        pages=result.pages,
        mode="live",
        source={"kind": "live_render", "path": None},
        raw=result.raw,
        crawl={
            "requested": result.requested,
            "fetched": result.fetched,
            "failed": result.failed,
            "limit": limit,
            "artifacts": artifacts,
            "retention_class": "crawl-ephemeral",
        },
    )


def _relative(path: Path, root: Path) -> str:
    """Store workspace-relative paths so a report never leaks a local layout."""
    try:
        return Path(path).resolve().relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        return Path(path).name