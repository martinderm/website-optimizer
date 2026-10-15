"""Schema capability: JSON-LD structure and completeness.

Scope decision (approved): this capability checks **structure and completeness**
locally and does not attempt to validate against schema.org's vocabulary. Instead
every finding points at the authority.

**Why not fetch schema.org.** The full vocabulary is a machine with tens of
thousands of terms and subclass hierarchies. Pulling it in would make the tool
network-dependent for a check that runs on a build directory, and a vendored copy
of the vocabulary would be a second source of truth that silently ages. What the
local check can prove is what usually goes wrong in practice: a block that does
not parse, a type that is only claimed and never filled, an `@id` that does not
resolve, a duplicate node.

Everything the tool cannot judge is handed to the right place: schema.org's
validator for the vocabulary, and the Rich Results Test for what actually
produces a rich result.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ...report import TOOL_NAME, TOOL_VERSION

CRITICAL = "critical"
WARNING = "warning"
REPORT_VERSION = "1"

VOCABULARY_REFERENCE = "https://schema.org/docs/full.html"
VALIDATOR_REFERENCE = "https://validator.schema.org/"
RICH_RESULTS_REFERENCE = (
    "https://search.google.com/test/rich-results"
)

# Types a site is expected to identify with. Not a requirement list — a
# portfolio may identify with `Person` only and be perfectly correct.
COMMON_TYPES = ("WebSite", "Organization", "Person", "LocalBusiness")

REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "WebSite": ("name", "url"),
    "Organization": ("name",),
    "Person": ("name",),
    "LocalBusiness": ("name", "address"),
    "Article": ("headline", "datePublished", "author"),
    "FAQPage": ("mainEntity",),
    "HowTo": ("name", "step"),
    "Product": ("name",),
    "Recipe": ("name", "recipeIngredient", "recipeInstructions"),
    "BreadcrumbList": ("itemListElement",),
    "VideoObject": ("name", "thumbnailUrl", "uploadDate"),
}

URL_RE = re.compile(r"^https?://", re.IGNORECASE)


def _finding(rule_id, severity, message, observed, expected, subject, location):
    return {
        "rule_id": rule_id, "severity": severity, "message": message,
        "observed": observed, "expected": expected, "subject": subject,
        "location": location,
    }


def iter_blocks(content: str) -> list[str]:
    """Every `application/ld+json` script body, in document order.

    The attribute value may be double-quoted, single-quoted, or — as minified
    generator output routinely emits — unquoted. Requiring quotes silently
    reported a fully marked-up site as having no structured data at all, which
    is the worst failure shape this capability has: a confident, wrong "clean".
    """
    pattern = re.compile(
        r"<script[^>]*\btype\s*=\s*(?:[\"']application/ld\+json[\"']|application/ld\+json)"
        r"[^>]*>(.*?)</script\s*>",
        re.IGNORECASE | re.DOTALL,
    )
    return [match.group(1).strip() for match in pattern.finditer(content)]


def audit_page(page_path: Path, relative: str) -> tuple[list[dict], list[str], list[tuple], int]:
    """Return (findings, type names, (id, page, payload) tuples, block count)."""
    content = page_path.read_text(encoding="utf-8", errors="replace")
    blocks = iter_blocks(content)

    findings: list[dict] = []
    types_found: list[str] = []
    identifiers: list[tuple[str, str, str]] = []

    if not blocks:
        findings.append(_finding(
            "schema.none", WARNING, "Page has no JSON-LD block", 0, ">= 1",
            relative, "head > script[type=application/ld+json]"))
        return findings, types_found, identifiers, 0

    for index, raw in enumerate(blocks):
        location = f"head > script[ld+json]:{index}"
        if not raw:
            findings.append(_finding(
                "schema.block_empty", CRITICAL, "JSON-LD block is empty",
                None, "a JSON object", relative, location))
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            findings.append(_finding(
                "schema.block_invalid_json", CRITICAL,
                f"JSON-LD block does not parse: {exc.msg} at line {exc.lineno}",
                exc.msg, "valid JSON", relative, location))
            continue

        nodes = _nodes(data)
        if not nodes:
            findings.append(_finding(
                "schema.block_no_types", WARNING,
                "JSON-LD block declares no @type",
                0, ">= 1 node with @type", relative, location))
            continue

        # @context is declared once on the block. A node inside a @graph inherits
        # it, so checking the node itself would report every graph member as
        # missing a context — which is exactly what a correct @graph looks like.
        block_has_context = _declares_context(data)
        for node in nodes:
            findings += _audit_node(node, relative, location, block_has_context)
            types_found.extend(_type_names(node))
            if isinstance(node.get("@id"), str):
                identifiers.append(
                    (node["@id"], relative, json.dumps(node, sort_keys=True))
                )

    return findings, types_found, identifiers, len(blocks)


def _declares_context(data: Any) -> bool:
    if isinstance(data, dict):
        return "@context" in data
    if isinstance(data, list):
        return any(_declares_context(item) for item in data)
    return False


def _nodes(data: Any) -> list[dict]:
    nodes: list[dict] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if "@type" in node:
                nodes.append(node)
            graph = node.get("@graph")
            if isinstance(graph, list):
                for item in graph:
                    walk(item)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)
    return nodes


def _type_names(node: dict) -> list[str]:
    value = node.get("@type")
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(v) for v in value]
    return []


def _audit_node(node: dict, subject: str, location: str, block_has_context: bool) -> list[dict]:
    findings: list[dict] = []
    node_id = node.get("@id") or "(no @id)"
    names = _type_names(node)
    if not names:
        return findings

    for name in names:
        required = REQUIRED_FIELDS.get(name)
        if not required:
            continue
        missing = [field for field in required if not node.get(field)]
        if missing:
            findings.append(_finding(
                "schema.required_field_missing", CRITICAL,
                f"{name} is missing required field(s): {', '.join(missing)}",
                missing, list(required), subject,
                f"{location} @type={name}"))

    if not block_has_context and "@context" not in node:
        findings.append(_finding(
            "schema.context_missing", WARNING,
            "JSON-LD has no @context, so no vocabulary is in force",
            None, "@context on the block", subject, location))
    return findings


def _audit_site(types_found: list[str]) -> list[dict]:
    """A site without an identity node cannot be attributed to anything."""
    if not types_found:
        return []
    if any(t in types_found for t in COMMON_TYPES):
        return []
    return [_finding(
        "schema.identity_missing", WARNING,
        "No site identity type found; expected one of " + ", ".join(COMMON_TYPES),
        sorted(set(types_found)), list(COMMON_TYPES), "(site)", "all pages")]


def _duplicate_identifiers(pairs: list[tuple[str, str, str]]) -> list[dict]:
    """The same `@id` carrying different content on two pages unresolves the graph.

    Reusing one `@id` across many pages is the *correct* pattern for a site-wide
    `@graph`: the partial emits the same `Person` and `WebSite` node in every
    head, and that is what makes the nodes resolvable. Only a genuine
    disagreement is a defect, so the comparison is on the payload, not on the
    number of pages.
    """
    payloads: dict[str, dict[str, str]] = {}
    for identifier, page, payload in pairs:
        payloads.setdefault(identifier, {})[page] = payload

    findings = []
    for identifier, pages in sorted(payloads.items()):
        distinct = set(pages.values())
        if len(distinct) > 1:
            sample = sorted(pages)[0]
            findings.append(_finding(
                "schema.identifier_conflicting", CRITICAL,
                f"@id {identifier} is declared with {len(distinct)} different contents "
                f"across {len(pages)} pages",
                len(distinct), 1, identifier,
                f"first seen on {sample}"))
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
    all_types: set[str] = set()
    identifier_pages: list[tuple[str, str]] = []
    blocks_total = 0
    audited = 0
    ignored = 0

    for file_path in sorted(target.rglob("*.html")):
        relative = file_path.relative_to(target).as_posix()
        if pattern and pattern.search(relative):
            ignored += 1
            continue
        audited += 1
        page_findings, page_types, ids_payload, blocks = audit_page(file_path, relative)
        findings += page_findings
        all_types.update(page_types)
        blocks_total += blocks
        identifier_pages += ids_payload

    findings += _audit_site(sorted(all_types))
    findings += _duplicate_identifiers(identifier_pages)

    critical = sum(1 for f in findings if f["severity"] == CRITICAL)
    return {
        "report_version": REPORT_VERSION,
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "crawl_mode": "static",
        "site": {"url": config.site_url, "domain": config.domain},
        "capability": "schema",
        "rules_run": list(CHECKS),
        "source": {"kind": "static_dir", "path": _relative(target, config.workspace_root)},
        "references": {
            "vocabulary": VOCABULARY_REFERENCE,
            "validator": VALIDATOR_REFERENCE,
            "rich_results": RICH_RESULTS_REFERENCE,
        },
        "summary": {
            "audited_pages": audited,
            "ignored_pages": ignored,
            "jsonld_blocks": blocks_total,
            "types_found": sorted(all_types),
            "pages_with_findings": len({f["subject"] for f in findings}),
            "total_critical_issues": critical,
            "total_warnings": len(findings) - critical,
        },
        "findings": findings,
    }


CHECKS: tuple[str, ...] = (
    "schema.none",
    "schema.block_empty",
    "schema.block_invalid_json",
    "schema.block_no_types",
    "schema.required_field_missing",
    "schema.context_missing",
    "schema.identity_missing",
    "schema.identifier_conflicting",
)


def _relative(path: Path, root: Path) -> str:
    try:
        return Path(path).resolve().relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        return Path(path).name