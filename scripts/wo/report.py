"""Run artifacts: where they go, what they contain, and how they are written.

Placement follows the Workspace Data Zones standard. Audit runs are Evidence:
logically append-only, therefore one run-scoped folder per execution, never a
single file that gets overwritten. Bulk raw crawl output is not knowledge and
stays outside the workspace zones entirely.

    memory/evidence/websites/<domain>/runs/<run-id>/
        report.json     the findings
        receipt.json    zone metadata, hashes, provenance

Nothing here writes outside those folders. Writes are atomic: a half-written
receipt would be worse than a missing one, because a missing run is visible and a
corrupt run looks valid.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import jsonschema

TOOL_NAME = "website-optimizer"
# Bumped whenever a rule is added, removed, split or re-severitied — that is,
# whenever `rules_run` would differ between two runs of the same site. A patch
# bump for anything else.
#
# The version sat at 0.2.0 across at least three mutually incompatible rule
# sets, which made `source_version` in the receipt a claim the report could not
# support: seventeen stored runs all read "website-optimizer 0.2.0" while their
# `rules_run` arrays show eight distinct rule sets underneath. `rules_run` did
# its job throughout — it is why those runs are still distinguishable at all —
# but a version string that stays still while the thing it names changes is not
# provenance, it is decoration. See decision D43.
# 0.5.0 added the sixth capability: `links`, with three rules, and the `Page.links`
# field they read. `rules_run` differs on every site from 0.4.1 onwards.
# 0.5.1 is a patch, under the "anything else" half of the rule above: the redirects
# User-Agent stopped restating a version by hand and derives this constant instead.
# No rule moved, so no fingerprint moved.
# 0.6.0 added the seventh capability: `crawler-files`, eleven rules over robots.txt,
# the sitemap and llms.txt.
# 0.6.1 is a patch under the "anything else" half: no rule moved, but a rule's
# result did. A partially readable sitemap index no longer counts as coverage, so
# two sites with the same `rules_run` can report differently across this version
# and a receipt should say which side of it the run was on.
# 0.7.0 added three rules to `images`: video posters and preload.
# 0.8.0 added the eighth capability: `performance`, five rules over weight,
# render-blocking scripts, font-display, preload targets and third-party origins.
# 0.8.1 is a patch under the "anything else" half: no rule moved, but a rule's
# result did. `link.target_missing` now accepts redirect sources, so two runs
# with the same `rules_run` can report differently across this version and a
# receipt should say which side of it the run was on.
TOOL_VERSION = "0.8.1"

# The artifact metadata contract. The authoritative schema lives in
# agent-architecture; it is not copied here, because one definition of the
# vocabulary is the whole point. This is the subset we enforce locally.
RECEIPT_CONFORMANCE = {
    "type": "object",
    "required": [
        "zone", "trust_level", "status", "artifact_sha256",
        "data_classification", "retention_class", "owner",
    ],
    "additionalProperties": False,
    "properties": {
        "zone": {"enum": ["references", "evidence", "cloud", "operations"]},
        "trust_level": {
            "enum": ["trusted_curated", "observed", "untrusted_external", "working"]
        },
        "status": {"enum": ["active", "superseded", "tombstoned", "archived", "expired"]},
        "source_uri": {"type": ["string", "null"]},
        "source_version": {"type": ["string", "null"]},
        "source_sha256": {"type": ["string", "null"], "pattern": "^[a-fA-F0-9]{64}$"},
        "artifact_sha256": {"type": "string", "pattern": "^[a-fA-F0-9]{64}$"},
        "synced_at": {"type": ["string", "null"]},
        "converter": {"type": ["string", "null"]},
        "data_classification": {"enum": ["public", "internal", "confidential", "restricted"]},
        "retention_class": {"type": "string", "minLength": 1},
        "owner": {"type": "string", "minLength": 1},
        "instructions_are_data": {"type": "boolean"},
        "origin_classifications": {"type": "array", "items": {"type": "string"}},
        "export_policy": {"enum": ["allowed", "approval_required", "prohibited"]},
        "promotion_policy": {"enum": ["allowed", "approval_required", "prohibited"]},
    },
}


class RunWriteError(Exception):
    """Raised with a self-correcting message rather than a bare OSError."""


def run_id(moment: datetime | None = None) -> str:
    """Timestamp-safe run identifier. No colons: Windows forbids them in paths."""
    moment = moment or datetime.now(timezone.utc)
    return moment.strftime("%Y-%m-%dT%H-%M-%SZ")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def atomic_write(path: Path, text: str) -> Path:
    """Write via tempfile + os.replace so a reader never sees a partial file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=path.parent,
        prefix=f".{path.name}.", suffix=".tmp", delete=False,
    )
    try:
        with handle as fh:
            fh.write(text)
        os.replace(handle.name, path)
    except OSError as exc:
        Path(handle.name).unlink(missing_ok=True)
        raise RunWriteError(f"Could not write {path}: {exc}") from exc
    return path


def runs_dir(workspace_root: Path, domain: str) -> Path:
    return Path(workspace_root) / "memory" / "evidence" / "websites" / domain / "runs"


def list_runs(workspace_root: Path, domain: str) -> list[str]:
    """All run identifiers for a site, oldest first. The tree is the state."""
    directory = runs_dir(workspace_root, domain)
    if not directory.is_dir():
        return []
    return sorted(p.name for p in directory.iterdir() if p.is_dir())


def build_receipt(report: dict[str, Any], config, run: str) -> dict[str, Any]:
    """Build the data-zone receipt for one run.

    Field names are the house vocabulary on purpose. A private provenance block
    could not be read by the workspace linter or by any other tool that speaks
    the standard, and an artifact format nobody validates is decoration.
    """
    payload = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True)
    return {
        "zone": "evidence",
        "trust_level": "observed",
        "status": "active",
        "source_uri": config.site_url,
        "source_version": f"{TOOL_NAME} {TOOL_VERSION}",
        "source_sha256": None,
        "artifact_sha256": sha256_bytes(payload.encode("utf-8")),
        "synced_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "converter": f"{TOOL_NAME}.wo",
        "data_classification": config.classification,
        "retention_class": config.retention_class,
        # D17: the owner is always the workspace slug. The fallback keeps that
        # true for programmatic construction, not only for config.load().
        "owner": config.owner or Path(config.workspace_root).name,
        # The run reports on pages it does not control. Their text is data.
        "instructions_are_data": True,
        "origin_classifications": ["public"],
        "export_policy": "allowed",
        "promotion_policy": "approval_required",
    }


def write_run(config, report: dict[str, Any], run: str | None = None,
              filename: str = "report.json") -> dict[str, Path]:
    """Write a run's artifact and its receipt into this run's evidence folder."""
    run = run or run_id()
    target = runs_dir(config.workspace_root, config.domain) / run

    report_path = atomic_write(
        target / filename,
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
    )
    receipt = build_receipt(report, config, run)
    jsonschema.assert_valid(receipt, RECEIPT_CONFORMANCE, f"receipt for run {run}")

    receipt_path = atomic_write(
        target / "receipt.json",
        json.dumps(receipt, indent=2, ensure_ascii=False) + "\n",
    )
    return {"report": report_path, "receipt": receipt_path, "run_dir": target}


def load_run(workspace_root: Path, domain: str, run: str) -> dict[str, Any] | None:
    """Load a stored report, or None when the run is absent."""
    path = runs_dir(workspace_root, domain) / run / "report.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))