"""Redirect-rule parsers.

Ported from `hugo-wizard/scripts/verify-redirects.py`. The parsers are
unchanged in behaviour: they read a redirect configuration file and yield
concrete test paths, because a live check needs a URL it can actually request.
A wildcard rule cannot be probed directly, so a capture group is substituted with
a sample slug and the rule is marked as a wildcard.

Supported sources: Apache `.htaccess`, Cloudflare Pages / Netlify `_redirects`,
and JSON or CSV mapping files.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

Mapping = tuple[str, str, bool]

REDIRECT_STATUSES = ("r=301", "r=308", "r=302")


class MappingError(Exception):
    """Raised with a self-correcting message, never a bare OSError."""


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

            match = re.match(
                r"^RewriteRule\s+\^?([^\$\s]+)\$?\s+([^\s]+)(?:\s+\[(.*)\])?", line, re.IGNORECASE
            )
            if match:
                source_pattern, target, flags = match.groups()
                flags = flags or ""
                # A whole-site rule (force HTTPS, www canonical) is not a route.
                if source_pattern in ("(.*)", "(.*)/?", "^(.*)$", "^(.*)"):
                    continue
                lowered = flags.lower()
                if any(marker in lowered for marker in REDIRECT_STATUSES) or "r" in lowered:
                    test_source, captured, has_capture = clean_regex_to_path(source_pattern)
                    is_wildcard = has_capture or ("$1" in target) or ("$2" in target)
                    clean_target = target.replace("$1", captured).replace("$2", captured)
                    if not (clean_target.startswith("/") or clean_target.startswith("http")):
                        clean_target = "/" + clean_target
                    if test_source and clean_target:
                        mappings.append((test_source, clean_target, is_wildcard))
                continue

            match_redirect = re.match(
                r"^Redirect\s+(?:301|308|permanent)?\s+([^\s]+)\s+([^\s]+)", line, re.IGNORECASE
            )
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