"""Redirect-rule syntax: one home, two callers.

Ported from `hugo-wizard/scripts/verify-redirects.py` (see the `redirects`
capability). The parsers below read a redirect configuration file and yield
concrete rules, because a live check needs a URL it can actually request.
A wildcard rule cannot be probed directly, so a capture group is substituted
with a sample slug and the rule is marked as a wildcard.

Second caller: `links` accepts redirect *sources* as existing link targets.
It needs the same syntax read a different way — exact paths and prefixes from
`_redirects`, matchable patterns from `.htaccess` — so the format knowledge
lives here once (D57) instead of being re-parsed next door.

Supported sources: Apache `.htaccess`, Cloudflare Pages / Netlify `_redirects`,
and JSON or CSV mapping files.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from . import urls
from .errors import MappingError

Mapping = tuple[str, str, bool]

REDIRECT_STATUSES = ("r=301", "r=308", "r=302")

# Whole-site rules (force-HTTPS, www canonical) answer everything and route
# nothing. They are not routes for probing, and they must never blanket-accept
# missing link targets either — one shared skip list for both callers.
WHOLE_SITE_PATTERNS = ("(.*)", "(.*)/?", "^(.*)$", "^(.*)")

REWRITE_RULE_RE = re.compile(
    r"^RewriteRule\s+\^?([^\$\s]+)\$?\s+([^\s]+)(?:\s+\[(.*)\])?", re.IGNORECASE
)
# Verbatim pattern and flags: acceptance matching needs the anchors the
# probing regex above consumes. `^bio/?$` compiled without its `$` would
# accept `/biodiesel` — a silent wrong answer on exactly the legacy URLs this
# is for.
REWRITE_SOURCE_RE = re.compile(
    r"^RewriteRule\s+(\S+)\s+(\S+)(?:\s+\[(.*)\])?", re.IGNORECASE
)
REDIRECT_DIRECTIVE_RE = re.compile(
    r"^Redirect\s+(?:301|308|permanent)?\s+([^\s]+)\s+([^\s]+)", re.IGNORECASE
)


def _is_redirect_flags(flags: str) -> bool:
    """Whether a RewriteRule flag set performs a redirect.

    Unchanged probing behavior: any `r` marker redirects, exactly as before.
    """
    lowered = (flags or "").lower()
    return any(marker in lowered for marker in REDIRECT_STATUSES) or "r" in lowered


def _is_no_case(flags: str) -> bool:
    """Whether the rule matches case-insensitively (`NC` flag)."""
    return any(part.strip() == "nc" for part in (flags or "").lower().split(","))





def clean_regex_to_path(pattern: str) -> tuple[str, str, bool]:
    """Turn a regex into a requestable path and report whether it is a wildcard."""
    p = pattern.lstrip("^").rstrip("$")
    p = re.sub(r"\(\?:[^)]+\)\?", "", p)
    p = re.sub(r"\(\?:([^|)]+)(?:\|[^)]*)*\)", r"\1", p)
    p = re.sub(r"([a-zA-Z0-9])\?", r"\1", p)
    p = p.replace("/?", "/")
    has_capture = bool(re.search(r"\([^)]+\)|\.\*", p))
    captured = "test-sample-item"
    p = re.sub(r"\([^)]+\)", captured, p)
    p = p.replace(".*", captured)
    p = re.sub(r"[\\+?^$]", "", p)
    if not p.startswith("/"):
        p = "/" + p
    p = re.sub(r"/+", "/", p)
    return p, captured, has_capture


def parse_htaccess(file_path) -> list[Mapping]:
    """RewriteRule and Redirect directives from an Apache configuration."""
    mappings: list[Mapping] = []
    with open(file_path, "r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            match = REWRITE_RULE_RE.match(line)
            if match:
                source_pattern, target, flags = match.groups()
                flags = flags or ""
                # A whole-site rule (force HTTPS, www canonical) is not a route.
                if source_pattern in WHOLE_SITE_PATTERNS:
                    continue
                if _is_redirect_flags(flags):
                    test_source, captured, has_capture = clean_regex_to_path(source_pattern)
                    is_wildcard = has_capture or ("$1" in target) or ("$2" in target)
                    clean_target = target.replace("$1", captured).replace("$2", captured)
                    if not (clean_target.startswith("/") or clean_target.startswith("http")):
                        clean_target = "/" + clean_target
                    if test_source and clean_target:
                        mappings.append((test_source, clean_target, is_wildcard))
                continue

            match_redirect = REDIRECT_DIRECTIVE_RE.match(line)
            if match_redirect:
                src, dst = match_redirect.groups()
                mappings.append((src, dst, False))

    return mappings


def parse_netlify_redirects(file_path) -> list[Mapping]:
    """`/source /target [status]` lines from a `_redirects` file."""
    mappings: list[Mapping] = []
    with open(file_path, "r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                src, dst = parts[0], parts[1]
                is_wildcard = ("*" in src) or (":splat" in dst)
                if "*" in src:
                    src = src.replace("*", "sample-item")
                if ":splat" in dst:
                    dst = dst.replace(":splat", "sample-item")
                mappings.append((src, dst, is_wildcard))
    return mappings


def parse_json_mappings(file_path) -> list[Mapping]:
    """A mapping object, a list of pairs, or a list of `{from,to}` objects."""
    with open(file_path, "r", encoding="utf-8", errors="replace") as handle:
        try:
            data = json.load(handle)
        except json.JSONDecodeError as exc:
            raise MappingError(f"{Path(file_path).name} is not valid JSON: {exc}") from exc

    mappings: list[Mapping] = []
    if isinstance(data, dict):
        for key, value in data.items():
            mappings.append((key, value, False))
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, list) and len(item) >= 2:
                mappings.append((item[0], item[1], False))
            elif isinstance(item, dict):
                src = item.get("from") or item.get("source") or item.get("url")
                dst = item.get("to") or item.get("target") or item.get("destination")
                if src and dst:
                    mappings.append((src, dst, False))
    return mappings


def parse_csv_mappings(file_path) -> list[Mapping]:
    """Two-column source/target table, comma or tab separated."""
    mappings: list[Mapping] = []
    delimiter = "\t" if str(file_path).endswith(".tsv") else ","
    with open(file_path, "r", encoding="utf-8", errors="replace", newline="") as handle:
        for row in csv.reader(handle, delimiter=delimiter):
            if not row or row[0].startswith("#") or len(row) < 2:
                continue
            mappings.append((row[0].strip(), row[1].strip(), False))
    return mappings


def load_mappings(file_path) -> list[Mapping]:
    """Detect the file type and read its redirect rules."""
    path = Path(file_path)
    if not path.is_file():
        raise MappingError(
            f"Redirect file not found: {path}\n"
            f"Set [redirects] file in site.optimizer.toml to the .htaccess or "
            f"_redirects file of this site."
        )

    name = path.name.lower()
    if name == ".htaccess" or name.endswith(".htaccess") or name.endswith(".conf"):
        return parse_htaccess(path)
    if name == "_redirects" or name.endswith("_redirects"):
        return parse_netlify_redirects(path)
    if name.endswith(".json"):
        return parse_json_mappings(path)
    if name.endswith(".csv") or name.endswith(".tsv"):
        return parse_csv_mappings(path)

    head = path.read_text(encoding="utf-8", errors="replace")[:500]
    if "RewriteRule" in head or "RewriteEngine" in head:
        return parse_htaccess(path)
    if "{" in head or "[" in head:
        return parse_json_mappings(path)
    return parse_netlify_redirects(path)


def dedupe(mappings: list[Mapping]) -> list[Mapping]:
    """Drop repeated (source, target) pairs, keeping first-seen order."""
    seen: set[tuple[str, str]] = set()
    unique: list[Mapping] = []
    for src, dst, wildcard in mappings:
        if (src, dst) not in seen:
            seen.add((src, dst))
            unique.append((src, dst, wildcard))
    return unique


# --- redirect sources for the link graph -----------------------------------
#
# `links` asks a narrower question than probing: does the server answer this
# URL at all? A redirect source is answered (with 3xx), so a link to one is
# not a missing target — wherever the redirect leads is `redirects`' live
# question, not this one. Sources come in three shapes, one per syntax:
# exact paths, prefixes (`*` splats), and matchable regexes (RewriteRules).
# Placeholders (`:id` segments in `_redirects`) are not matched: inventing
# segment semantics the file's host may not share would accept what nothing
# answers.

RedirectSources = dict[str, object]

EMPTY_SOURCES: RedirectSources = {"exact": set(), "prefix": set(), "pattern": []}


def _read_lines(path) -> list[str]:
    return Path(path).read_text(encoding="utf-8", errors="replace").splitlines()


def sources_from_redirects_file(path) -> RedirectSources:
    """Exact and prefix sources from a `_redirects` file.

    Absent file, empty set — a build without redirect files behaves exactly as
    before, because there is nothing to accept.
    """
    exact: set[str] = set()
    prefix: set[str] = set()
    candidate = Path(path)
    if candidate.is_file():
        for line in _read_lines(candidate):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            src = parts[0]
            if "*" in src:
                piece = src.split("*", 1)[0].strip()
                if not piece.startswith("/"):
                    piece = "/" + piece
                piece = piece if piece.endswith("/") else piece + "/"
                # A bare `/*` answers everything (maintenance page, SPA
                # fallback) and routes nothing. Like the whole-site rules it
                # must never blanket-accept missing targets, or one catch-all
                # would silence the entire missing-target rule.
                if piece == "/":
                    continue
                prefix.add(piece)
            else:
                exact.add(urls.key(src))
    return {"exact": exact, "prefix": prefix, "pattern": []}


def sources_from_htaccess(path) -> RedirectSources:
    """Exact sources (`Redirect` directives) and regexes (R-flag RewriteRules).

    Patterns are matched the way the server matches them: verbatim (anchors
    kept) with search semantics against the path without leading slash,
    case-sensitive unless the `NC` flag says otherwise. `RewriteCond` lines
    are not evaluated — a conditional rule may accept more than the server
    would, and that limit is stated in the capability README rather than
    hidden. A pattern that does not compile is skipped: a site file must
    never crash the audit. Catch-all patterns (`.*` in any anchoring) never
    accept: like the whole-site rules they answer everything and route
    nothing, and blanket-acceptance would make the missing-target rule
    vacuous. This guard is acceptance-only — probing keeps its own skip list
    untouched, so no verified probing behavior moves.
    """
    exact: set[str] = set()
    patterns: list = []
    candidate = Path(path)
    if candidate.is_file():
        for line in _read_lines(candidate):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            match = REWRITE_SOURCE_RE.match(line)
            if match:
                source_pattern, _, flags = match.groups()
                if _is_catchall(source_pattern):
                    continue
                if not _is_redirect_flags(flags or ""):
                    continue
                try:
                    compiled = re.compile(
                        source_pattern,
                        re.IGNORECASE if _is_no_case(flags or "") else 0,
                    )
                except re.error:
                    continue
                patterns.append(compiled)
                continue
            match_redirect = REDIRECT_DIRECTIVE_RE.match(line)
            if match_redirect:
                src, _ = match_redirect.groups()
                exact.add(urls.key(src))
    return {"exact": exact, "prefix": set(), "pattern": patterns}


def _is_catchall(pattern: str) -> bool:
    """Whether a pattern answers every URL: whole-site rules and bare `.*`."""
    if pattern in WHOLE_SITE_PATTERNS:
        return True
    core = pattern
    if core.startswith("^"):
        core = core[1:]
    if core.endswith("$"):
        core = core[:-1]
    return core in ("(.*)", ".*")


def sources_from_build(root) -> RedirectSources:
    """The redirect sources a build output serves, both formats combined."""
    root = Path(root)
    combined: RedirectSources = {"exact": set(), "prefix": set(), "pattern": []}
    for path, loader in (
        (root / "_redirects", sources_from_redirects_file),
        (root / ".htaccess", sources_from_htaccess),
    ):
        if path.is_file():
            found = loader(path)
            combined["exact"].update(found["exact"])
            combined["prefix"].update(found["prefix"])
            combined["pattern"].extend(found["pattern"])
    return combined


def matches(sources: RedirectSources, key: str) -> bool:
    """Whether a normalized URL key is a redirect source."""
    if key in sources["exact"]:
        return True
    for prefix in sources["prefix"]:
        if key == prefix.rstrip("/") or key.startswith(prefix):
            return True
    stripped = key.lstrip("/")
    for pattern in sources["pattern"]:
        # Search, not match: the server tries the pattern anywhere unless
        # anchors say otherwise. An unanchored `old` answers `/x/old`.
        if pattern.search(stripped):
            return True
    return False