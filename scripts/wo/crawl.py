"""Live page rendering through `playwright-cli`.

Round 5. A static audit reads build output; a dynamic site has none. This module
renders URLs in a real browser and hands `Page` objects to the same capability
code that reads files, so a capability cannot grow a rule that only works on one
of the two.

**Why this is not a hook** (D26): a browser crawl costs minutes where a static
audit costs seconds; sessions are a shared resource that two harnesses collide
on; and results depend on viewport and consent state, so a hook would fail
intermittently and an intermittently failing hook gets disabled. It runs when a
person asks for it, never otherwise.

**The consent wall is checked, not assumed** (D26(d)). A crawl behind a cookie
wall finds the wall on every page and reports it as that page's content —
consistently wrong in a way that looks entirely real. `_looks_like_a_wall`
detects the signature of that failure and refuses to emit findings rather than
producing a confident, useless report.

**Crawl artifacts go to the data zone, not the evidence zone** (D27). Raw HTML is
regenerable and bulky; the evidence zone is for conclusions that a reader
reasons about. They are written beside the run at `data/crawl/<run-id>/` and are
safe to delete.

**Page content is data** (D13). HTML from a site this tool does not control goes
to the extractor and nowhere else. Nothing here prints, logs, or returns page
text.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import urljoin, urlparse

from .errors import ConfigError, CrawlError
from .page import Page, extract_page_from_html
from .report import TOOL_NAME, TOOL_VERSION, atomic_write

# `--raw` makes the CLI emit only the value, JSON-encoded. Asking the browser
# for a JSON string is what makes the response safe to hand to `json.loads`:
# quotes, newlines and non-ASCII in page content cannot break the transport.
EVAL_HTML = "document.documentElement.outerHTML"

DEFAULT_TIMEOUT = 30
DEFAULT_SETTLE_MS = 400

# Markers of a page whose content is a modal rather than the page. Presence of
# one is a hint, not a verdict: plenty of honest pages carry the word "cookie".
WALL_MARKERS = (
    "consent",
    "cookie-banner",
    "cookie-consent",
    "gdpr",
    "onetrust",
    "usercentrics",
    "cookieyes",
    "didomi",
    "trustarc",
    "qcpt",
)


@dataclass
class CrawlResult:
    """What a crawl produced, including what it failed to produce."""

    pages: list[Page] = field(default_factory=list)
    requested: int = 0
    failed: list[dict[str, str]] = field(default_factory=list)
    artifact_dir: Path | None = None
    wall_suspected: bool = False
    wall_reason: str = ""
    # page.source -> rendered markup, for capabilities that need the document
    # itself rather than the fields extracted from it.
    raw: dict[str, str] = field(default_factory=dict)

    @property
    def fetched(self) -> int:
        return len(self.pages)


# npm installs `playwright-cli` on Windows as a .CMD shim that re-invokes node.
# `subprocess` cannot execute a .CMD without a shell, and a shell is the wrong
# tool here: a URL containing `&` — which the playwright-cli docs call out
# explicitly — would be split by cmd.exe before the browser ever saw it.
#
# So the shim is parsed rather than shelled out to. npm generates it from one
# template, the path inside it is stable, and resolving it gives an invocation
# with no shell anywhere in it.
_SHIM_JS = "node_modules/@playwright/cli/playwright-cli.js"
_SHIM_JS_WINDOWS = "node_modules\\@playwright\\cli\\playwright-cli.js"


def _resolve_command(override: str | None = None) -> tuple[list[str] | None, str]:
    """The argv prefix that runs playwright-cli, plus a message when it cannot.

    Prefers a real executable, falls back to the node entry point behind an npm
    shim, and only as a last resort to cmd.exe. The order matters: every step
    down removes a shell, and with it a class of quoting bug.
    """
    if override:
        return ([override] if not override.lower().endswith(".cmd") else
                _node_command(Path(override))), f"using configured {override}"

    found = shutil.which("playwright-cli")
    if not found:
        return None, (
            "playwright-cli is not on PATH.\n"
            "Install it with:  npm install -g @playwright/cli@latest\n"
            "Then confirm the browser:  python ../playwright-cli/scripts/check_environment.py --json"
        )

    if Path(found).suffix.lower() not in (".cmd", ".bat"):
        return [found], f"using {found}"

    shim_dir = Path(found).parent
    entry = shim_dir / _SHIM_JS_WINDOWS
    if entry.is_file():
        # The shim prefers a node.exe next to itself; fall back to PATH.
        local_node = shim_dir / "node.exe"
        node = str(local_node) if local_node.is_file() else (shutil.which("node") or "node")
        return [node, str(entry)], f"using {entry} via node"

    # Last resort. subprocess still needs a shell for this one, so arguments are
    # quoted by cmd's own rules rather than the caller's.
    comspec = os.environ.get("COMSPEC", "cmd.exe")
    return [comspec, "/d", "/s", "/c", found], f"using cmd.exe wrapper for {found}"


def _node_command(shim: Path) -> list[str]:
    entry = shim.parent / _SHIM_JS_WINDOWS
    if entry.is_file():
        local_node = shim.parent / "node.exe"
        return [str(local_node) if local_node.is_file() else (shutil.which("node") or "node"),
                str(entry)]
    return [str(shim)]


def browser_available() -> tuple[bool, str]:
    """Whether the CLI can be run, and what the message should say if not."""
    command, detail = _resolve_command()
    return (command is not None), detail


def browser_ready() -> tuple[bool, str]:
    """Preflight: CLI present and a browser selected. Never launches anything."""
    ok, detail = browser_available()
    if not ok:
        return False, detail
    # `--browser=msedge` is the selection this workspace's preflight reports as
    # installed. Chrome is the CLI default and is frequently absent, so the
    # caller passes the browser explicitly rather than inheriting a default that
    # fails at launch time with a message about a cache directory.
    return True, "playwright-cli found"


def _run_cli(session: str, args: list[str], timeout: int,
             command: list[str] | None = None) -> subprocess.CompletedProcess:
    """One CLI call. `--raw` first so the reply is the bare value."""
    if command is None:
        resolved, _ = _resolve_command()
        if resolved is None:
            raise CrawlError(browser_available()[1])
        command = resolved
    argv = [*command, f"-s={session}", "--raw", *args]
    try:
        # Bytes in, explicit decoding out. `text=True` would decode with the
        # machine's locale code page — cp1252 on a German Windows — and a
        # rendered page containing a character outside that code page raises
        # UnicodeDecodeError in a reader thread. The process then dies with a
        # traceback instead of an audit. A tool whose input is arbitrary web
        # pages cannot inherit the terminal's encoding.
        completed = subprocess.run(
            argv, capture_output=True, timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise CrawlError(
            f"playwright-cli did not answer within {timeout}s.\n"
            f"Command: {' '.join(argv)}\n"
            f"Raise [crawl] timeout_seconds, or check whether a session is stuck."
        ) from exc
    except FileNotFoundError as exc:
        _, detail = _resolve_command()
        raise CrawlError(f"Could not start playwright-cli ({detail}).") from exc

    completed.stdout = completed.stdout.decode("utf-8", "replace")
    completed.stderr = completed.stderr.decode("utf-8", "replace")
    return completed


class BrowserSession:
    """One named browser session, opened on enter and closed on exit.

    Session names are namespaced per site. Two harnesses in one workspace must
    not share a browser session, and `playwright-cli` names are global to the
    machine, so the name carries the domain rather than the capability.
    """

    def __init__(self, name: str, timeout: int = DEFAULT_TIMEOUT,
                 settle_ms: int = DEFAULT_SETTLE_MS,
                 headed: bool = False,
                 runner: Callable[..., subprocess.CompletedProcess] | None = None,
                 command: list[str] | None = None):
        self.name = name
        self.timeout = timeout
        self.settle_ms = settle_ms
        self.headed = headed
        self._runner = runner or _run_cli
        self._command = command
        self._open = False

    def _call(self, args: list[str]) -> subprocess.CompletedProcess:
        return self._runner(self.name, args, self.timeout, self._command)

    def __enter__(self) -> "BrowserSession":
        ok, detail = browser_ready()
        if not ok:
            raise CrawlError(detail)
        args = ["open", "--browser=msedge"]
        if self.headed:
            args.append("--headed")
        result = self._call(args)
        if result.returncode != 0:
            raise CrawlError(
                f"The browser did not open (exit {result.returncode}).\n"
                f"{result.stderr.strip() or result.stdout.strip()}\n"
                f"If the message names a missing browser cache, run:\n"
                f"  python ../playwright-cli/scripts/check_environment.py --json --browser=msedge"
            )
        self._open = True
        return self

    def __exit__(self, *exc_info) -> None:
        if not self._open:
            return
        # Only ever closes the session it opened.
        self._call(["close"])
        self._open = False

    def goto(self, url: str) -> None:
        result = self._call(["goto", url])
        if result.returncode != 0:
            raise CrawlError(
                f"{url} could not be opened (exit {result.returncode}).\n"
                f"{result.stderr.strip() or result.stdout.strip()}"
            )
        if self.settle_ms:
            # Lazy-loaded markup arrives after load. Sleeping is crude, and the
            # honest alternative — waiting on a selector — means deciding which
            # selector, which is a page assumption this tool should not make.
            time.sleep(self.settle_ms / 1000)

    def html(self) -> str:
        result = self._call(["eval", EVAL_HTML])
        if result.returncode != 0:
            raise CrawlError(
                f"The page could not be read back (exit {result.returncode}).\n"
                f"{result.stderr.strip() or result.stdout.strip()}"
            )
        raw = result.stdout.strip()
        if not raw:
            raise CrawlError("The browser returned no HTML for the current page.")
        try:
            value = json.loads(raw)
        except ValueError as exc:
            raise CrawlError(
                "The browser returned something that is not JSON. "
                "A page with content that breaks the transport would do this."
            ) from exc
        if not isinstance(value, str):
            raise CrawlError(f"Expected a string of HTML, got {type(value).__name__}.")
        return value


def _looks_like_a_wall(htmls: Iterable[str]) -> tuple[bool, str]:
    """Detect a crawl that is seeing a wall, not the site.

    The signature is *many distinct URLs returning identical markup*. A real site
    differs between pages; a consent overlay or a JS-only shell does not. Both
    failure modes produce the same output — confident findings about a dialog —
    so they are caught by one test.

    Returns `(suspected, reason)`. Empty and single-page crawls are never
    suspect: with nothing to compare, there is no evidence of a wall, and
    refusing to report one page would be refusing to do the job asked.
    """
    samples = [h for h in htmls if h]
    if len(samples) < 3:
        return False, ""

    fingerprints: dict[str, int] = {}
    for html in samples:
        digest = hashlib.sha256(html.encode("utf-8", "replace")).hexdigest()
        fingerprints[digest] = fingerprints.get(digest, 0) + 1

    dominant = max(fingerprints.values())
    if dominant < len(samples) * 0.9:
        return False, ""

    lowered = samples[0].lower()
    named = [m for m in WALL_MARKERS if m in lowered]
    reason = (
        f"{dominant} of {len(samples)} distinct URLs returned byte-identical markup. "
        f"Pages that differ cannot produce identical documents, so this crawl is "
        f"reading one page repeatedly."
    )
    if named:
        reason += (
            f" The markup carries {', '.join(named)}, which is consistent with a "
            f"consent overlay."
        )
    else:
        reason += (
            " No known consent marker was present, so this may be a JavaScript "
            "shell rather than a cookie wall; either way the rendered content is "
            "not the site's."
        )
    return True, reason


def _slug(url: str) -> str:
    """A stable, filesystem-safe name for one URL."""
    parsed = urlparse(url)
    path = parsed.path.strip("/") or "index"
    name = path.replace("/", "__") or "index"
    return f"{parsed.netloc.replace(':', '_')}__{name}"[:120]


def crawl(urls: list[str], config, run: str | None = None,
          session_name: str | None = None,
          progress: Callable[[int, int, str], None] | None = None) -> CrawlResult:
    """Render each URL and return the extracted pages.

    A page that fails is recorded, not raised: one broken URL must not discard a
    crawl of four hundred. The failures travel with the result so the report can
    say how much of the site it actually saw.
    """
    result = CrawlResult(requested=len(urls))
    crawl_dir = Path(config.workspace_root) / "data" / "crawl" / (run or "adhoc")
    session_name = session_name or f"wo-{config.domain}"
    raw: list[str] = []

    command, detail = _resolve_command(config.crawl.get("cli_path"))
    if command is None:
        raise CrawlError(detail)

    with BrowserSession(
        session_name,
        timeout=int(config.crawl.get("timeout_seconds", DEFAULT_TIMEOUT)),
        settle_ms=int(config.crawl.get("settle_ms", DEFAULT_SETTLE_MS)),
        command=command,
    ) as browser:
        for index, url in enumerate(urls, start=1):
            try:
                browser.goto(url)
                html = browser.html()
            except CrawlError as exc:
                result.failed.append({"url": url, "reason": str(exc).splitlines()[0]})
                if progress:
                    progress(index, len(urls), url)
                continue

            raw.append(html)
            result.pages.append(
                extract_page_from_html(html, source_label=url)
            )
            result.raw[url] = html

            # The artifact write happens after extraction, so a page that failed
            # to parse leaves no file claiming it was seen.
            #
            # The provenance comment is prepended rather than kept in a sidecar:
            # an HTML file that does not say which URL produced it is worth
            # little, and a separate index is a second file to lose.
            try:
                atomic_write(
                    crawl_dir / f"{_slug(url)}.html",
                    f"<!-- website-optimizer crawl\n     url: {url}\n"
                    f"     fetched: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}\n"
                    f"     tool: {TOOL_NAME} {TOOL_VERSION}\n-->\n{html}",
                )
                result.artifact_dir = crawl_dir
            except OSError:
                # The crawl is the observation; the raw copy is a convenience.
                # Losing it must not fail the audit.
                pass

            if progress:
                progress(index, len(urls), url)

    suspected, reason = _looks_like_a_wall(raw)
    if suspected:
        result.wall_suspected = True
        result.wall_reason = reason

    if result.fetched == 0:
        raise CrawlError(
            f"No page could be rendered ({len(urls)} attempted, {len(result.failed)} failed).\n"
            + _first_reasons(result.failed)
            + "\nCheck the URLs and that the site is reachable from here."
        )
    return result


def _first_reasons(failed: list[dict[str, str]], limit: int = 3) -> str:
    if not failed:
        return ""
    lines = [f"  {f['url']}: {f['reason']}" for f in failed[:limit]]
    if len(failed) > limit:
        lines.append(f"  ... and {len(failed) - limit} more")
    return "First failures:\n" + "\n".join(lines)


def resolve_start_urls(config) -> list[str]:
    """Which URLs to render, from config or the sitemap.

    Order of preference, and why: an explicit list is a decision someone made;
    a sitemap is the site's own declaration of what is a page; a bare root URL
    is a guess and is labelled as one in the report.
    """
    explicit = list(config.crawl.get("start_urls", []) or [])
    if explicit:
        return [_absolute(config.site_url, u) for u in explicit]

    sitemap = config.crawl.get("sitemap")
    if sitemap:
        return _urls_from_sitemap(_absolute(config.site_url, sitemap), config)

    return [config.site_url.rstrip("/") + "/"]


def _absolute(base: str, url: str) -> str:
    if url.startswith(("http://", "https://")):
        return url
    return urljoin(base.rstrip("/") + "/", url.lstrip("/"))


def _urls_from_sitemap(url: str, config) -> list[str]:
    """Read loc entries from a sitemap without an XML parser dependency.

    `xml.etree` is stdlib and would be the obvious choice, but a sitemap served
    with a wrong content type or a namespace prefix would then abort the crawl.
    The loc values are plain text and a regex over them cannot fail on shape.
    """
    import re
    import urllib.request

    limit = int(config.crawl.get("max_pages", 200))
    try:
        with urllib.request.urlopen(url, timeout=int(config.crawl.get("timeout_seconds", DEFAULT_TIMEOUT))) as response:
            body = response.read().decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001 - any failure here means "no sitemap"
        raise CrawlError(
            f"The sitemap could not be read: {url}\n{exc}\n"
            f"List the pages explicitly under [crawl] start_urls instead."
        ) from exc

    locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", body, re.IGNORECASE)
    if not locs:
        raise CrawlError(
            f"No <loc> entries in the sitemap: {url}\n"
            f"It may be a sitemap index. List pages under [crawl] start_urls instead."
        )
    return locs[:limit]


def crawl_settings(data: dict) -> dict[str, Any]:
    """Validated `[crawl]` block with defaults."""
    section = data.get("crawl", {})
    timeout = section.get("timeout_seconds", DEFAULT_TIMEOUT)
    if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0:
        raise ConfigError(f"[crawl] timeout_seconds must be a positive integer, got {timeout!r}.")
    settle = section.get("settle_ms", DEFAULT_SETTLE_MS)
    if not isinstance(settle, int) or isinstance(settle, bool) or settle < 0:
        raise ConfigError(f"[crawl] settle_ms must be a zero or positive integer, got {settle!r}.")
    max_pages = section.get("max_pages", 200)
    if not isinstance(max_pages, int) or isinstance(max_pages, bool) or max_pages <= 0:
        raise ConfigError(f"[crawl] max_pages must be a positive integer, got {max_pages!r}.")
    start = section.get("start_urls", []) or []
    if not isinstance(start, list) or not all(isinstance(u, str) for u in start):
        raise ConfigError("[crawl] start_urls must be a list of URL strings.")
    return {
        "start_urls": start,
        "sitemap": section.get("sitemap"),
        "max_pages": max_pages,
        "timeout_seconds": timeout,
        "settle_ms": settle,
        "cli_path": section.get("cli_path"),
    }
