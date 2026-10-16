"""Compare capability: what actually changed between two runs.

Design decision: **never refuse, always attribute.**

The naive alternative is to skip a comparison whenever the tool version or the
crawl mode differs. That is wrong in practice: the tool version changes on every
skill release, so in an actively developed skill the comparison would refuse
almost exactly when it is wanted. A strict gate trades one failure mode — a
false alarm — for a worse one — silence.

So the comparison always runs, and each difference is classified by *cause*:

| Kind | Meaning |
|---|---|
| `regression` | a critical finding is present now and was not present before |
| `improvement` | a finding is gone |
| `check-change` | the rule exists in only one run, so the site may not have moved at all |
| `site-change` | same rules both sides, different findings |

`check-change` is the bucket that makes the rest honest. Adding a rule to the
skill would otherwise look identical to breaking the site.

A provenance difference is reported as a qualifier on the comparison, never used
as a filter.

| Kind | Meaning |
|---|---|
| `unattributed` | **no cause could be assigned** — the two runs saw different numbers of pages |

`unattributed` is not a fifth *cause*, it is the absence of one, and it is the
only condition under which a difference is withheld from the other four buckets.
The case that produced it: a baseline that was a live crawl covering 25 of 173
pages, compared against a static run covering all 173, reported
`schema.identifier_conflicting` as a regression. The rule set was identical and
the site had not moved — the rule needs to meet the same `@id` on two pages, and
a quarter of the site cannot produce that. A comparison that attributed an
observation-depth difference to the site was making a claim it had no basis for.

Equal scope is the normal case and changes nothing. Unequal scope makes every
difference unattributable in *both* directions, because a larger sample is
expected to find more and a smaller one expected to find less — so a missing
finding is no more evidence of improvement than a new one is of regression.
Neither does it refuse: the difference is reported, both page counts are named,
and `unattributed` never becomes a finding, so `--strict` cannot fail on something
the tool cannot explain.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ... import report as report_module
from ...errors import CompareError
from ...report import TOOL_NAME, TOOL_VERSION

REPORT_VERSION = "1"
CRITICAL = "critical"
WARNING = "warning"

REGRESSION = "regression"
IMPROVEMENT = "improvement"
CHECK_CHANGE = "check-change"
SITE_CHANGE = "site-change"
UNATTRIBUTED = "unattributed"

KINDS = (REGRESSION, IMPROVEMENT, CHECK_CHANGE, SITE_CHANGE, UNATTRIBUTED)


def scope_of(report: dict[str, Any]) -> int | None:
    """How many pages a run actually looked at.

    `audited_pages` is the capability-neutral counter; every capability carries it
    for exactly this reason. The crawl block is the fallback for reports written
    before that field existed, and `None` means "unknown" rather than zero — a
    run of unknown scope must not be treated as a run that saw nothing, or every
    comparison against an old report would refuse.
    """
    summary = report.get("summary") or {}
    pages = summary.get("audited_pages")
    if isinstance(pages, int) and not isinstance(pages, bool):
        return pages
    crawl = report.get("crawl") or {}
    fetched = crawl.get("fetched")
    if isinstance(fetched, int) and not isinstance(fetched, bool):
        return fetched
    return None


def scope_differs(before: dict[str, Any], after: dict[str, Any]) -> tuple[bool, str]:
    """Whether the two runs observed different amounts of the site.

    Returns `(differs, reason)`. An unknown scope on either side does not count
    as a difference: refusing to compare against every older report would trade a
    narrow misattribution for total silence, which is the trade D25 exists to
    prevent.
    """
    a, b = scope_of(before), scope_of(after)
    if a is None or b is None:
        return False, ""
    if a == b:
        return False, ""
    return True, (
        f"The baseline saw {a} page(s) and this run saw {b}. A difference between "
        f"runs of different size cannot be attributed to the site: more pages is "
        f"expected to find more, fewer to find less."
    )





def _identity(finding: dict[str, Any]) -> tuple[str, str]:
    """What makes two findings 'the same finding'.

    Reports written before the `subject` rename carry `page` instead. Falling
    back keeps those runs comparable; a KeyError would make every comparison
    against an older run fail, and losing a real baseline is worse than
    tolerating a field that will never appear again.
    """
    subject = finding.get("subject")
    if subject is None:
        subject = finding.get("page", "")
    return (finding.get("rule_id", ""), subject)


def classify(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    """Attribute every difference between two reports of the same capability.

    With unequal scope nothing is attributable, and the differences say so and
    carry the reason. The computation is identical either way — what changes is
    the label, which keeps the classification in one place instead of spread over
    four branches that would each need the same guard.
    """
    rules_before = set(before.get("rules_run", []))
    rules_after = set(after.get("rules_run", []))
    unequal, reason = scope_differs(before, after)

    index_before = {_identity(f): f for f in before.get("findings", [])}
    index_after = {_identity(f): f for f in after.get("findings", [])}

    differences: list[dict[str, Any]] = []

    for key, finding in index_after.items():
        previous = index_before.get(key)
        if previous is None:
            # A baseline that declares no rule set cannot tell us whether this
            # rule existed there. Guessing "check-change" would silently swallow
            # every real regression against an older run, so fall back to the
            # severity rule and let a human look twice.
            rule_is_new = bool(rules_before) and finding["rule_id"] not in rules_before
            if rule_is_new:
                kind = CHECK_CHANGE
            elif finding["severity"] == CRITICAL:
                kind = REGRESSION
            else:
                kind = SITE_CHANGE
            differences.append(_difference(kind, finding, None))
        elif previous["severity"] != finding["severity"]:
            worsened = _rank(finding["severity"]) > _rank(previous["severity"])
            kind = REGRESSION if worsened else SITE_CHANGE
            differences.append(_difference(kind, finding, previous))

    for key, finding in index_before.items():
        if key not in index_after:
            rule_was_dropped = bool(rules_after) and finding["rule_id"] not in rules_after
            kind = CHECK_CHANGE if rule_was_dropped else IMPROVEMENT
            differences.append(_difference(kind, None, finding))

    differences.sort(key=lambda d: (d["kind"], d["rule_id"], d["subject"]))

    if unequal:
        for diff in differences:
            diff["kind"] = UNATTRIBUTED
            diff["reason"] = reason
        differences.sort(key=lambda d: (d["kind"], d["rule_id"], d["subject"]))
    return differences


def _rank(severity: str) -> int:
    return {CRITICAL: 2, WARNING: 1}.get(severity, 0)


def _difference(kind: str, current: dict | None, previous: dict | None) -> dict[str, Any]:
    source = current or previous or {}
    return {
        "kind": kind,
        "rule_id": source.get("rule_id"),
        "subject": source.get("subject") if source.get("subject") is not None else source.get("page"),
        "severity": (current or previous or {}).get("severity"),
        "baseline_severity": (previous or {}).get("severity"),
        "current_severity": (current or {}).get("severity"),
        "message": (current or previous or {}).get("message", ""),
    }


def _read_run(workspace_root: Path, domain: str, run: str) -> dict[str, Any]:
    data = report_module.load_run(workspace_root, domain, run)
    if data is None:
        available = report_module.list_runs(workspace_root, domain)
        raise CompareError(
            f"No report in run {run}.\n"
            f"Available runs: {', '.join(available) if available else 'none yet — run an audit first'}"
        )
    return data


def pick_baseline(workspace_root: Path, domain: str, current_run: str | None) -> str | None:
    """The nearest earlier run that shares a capability with the current one.

    Searching for a *comparable* run rather than simply the previous one matters
    because capabilities do not all run every time. With `redirects` and
    `on-page` alternating, "the previous run" is regularly a different
    capability, and the comparison would refuse for a reason the caller cannot
    act on.
    """
    runs = report_module.list_runs(workspace_root, domain)
    earlier = [r for r in runs if not current_run or r < current_run]
    if not earlier or not current_run:
        return earlier[-1] if earlier else None

    wanted = set(_reports_by_capability(workspace_root, domain, current_run))
    if not wanted:
        return earlier[-1]
    for candidate in reversed(earlier):
        if wanted & set(_reports_by_capability(workspace_root, domain, candidate)):
            return candidate
    return None


def build(workspace_root: Path, domain: str, baseline_run: str | None,
          current_run: str | None) -> dict[str, Any]:
    """Compare every capability present in both runs."""
    if baseline_run is None or current_run is None:
        raise CompareError(
            "Nothing to compare: this is the first stored run for this site.\n"
            "Run an audit again to get a second run, then compare."
        )

    before_runs = _reports_by_capability(workspace_root, domain, baseline_run)
    after_runs = _reports_by_capability(workspace_root, domain, current_run)

    compared = sorted(set(before_runs) & set(after_runs))
    if not compared:
        raise CompareError(
            f"Runs {baseline_run} and {current_run} share no capability "
            f"(baseline: {', '.join(sorted(before_runs)) or 'none'}; "
            f"current: {', '.join(sorted(after_runs)) or 'none'})."
        )

    all_differences: list[dict[str, Any]] = []
    regressions: list[dict[str, Any]] = []
    provenance_changed: list[str] = []
    scope_changed: list[str] = []
    pairs: list[dict[str, Any]] = []
    scopes: list[dict[str, Any]] = []

    for capability in compared:
        before, after = before_runs[capability], after_runs[capability]
        differences = classify(before, after)
        unequal, _ = scope_differs(before, after)

        for diff in differences:
            diff["capability"] = capability
            all_differences.append(diff)
            # An unattributed difference never becomes a finding. `--strict` must
            # not fail on something the tool cannot explain, and a reader scanning
            # `findings` should see only claims the tool stands behind.
            if diff["kind"] == REGRESSION:
                regressions.append(_regression_finding(diff, capability, current_run))

        if before.get("tool") != after.get("tool"):
            provenance_changed.append(capability)
        if before.get("crawl_mode") != after.get("crawl_mode"):
            provenance_changed.append(capability)
        if unequal:
            scope_changed.append(capability)

        before_pages, after_pages = scope_of(before), scope_of(after)
        scopes.append({
            "capability": capability,
            "baseline_pages": before_pages,
            "current_pages": after_pages,
            "equal": not unequal,
        })
        pairs.append({
            "capability": capability,
            "baseline_version": (before.get("tool") or {}).get("version"),
            "current_version": (after.get("tool") or {}).get("version"),
        })

    counts = {
        kind: sum(1 for d in all_differences if d["kind"] == kind)
        for kind in KINDS
    }

    return {
        "report_version": REPORT_VERSION,
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "crawl_mode": "static",
        "site": {"url": "", "domain": domain},
        "capability": "compare",
        "rules_run": list(KINDS),
        "baseline": {"run": baseline_run},
        "current": {"run": current_run},
        "provenance_changed": sorted(set(provenance_changed)),
        "scope_changed": sorted(set(scope_changed)),
        "scope": scopes,
        "compared": pairs,
        "summary": {
            "compared_capabilities": len(compared),
            **counts,
            # Only attributed regressions are critical. Counting an unattributed
            # difference here would let an unexplainable observation fail a build.
            "total_critical_issues": counts[REGRESSION],
            "total_warnings": counts[SITE_CHANGE],
        },
        "differences": all_differences,
        "findings": regressions,
    }


def _regression_finding(diff: dict[str, Any], capability: str, run: str) -> dict[str, Any]:
    """A regression enters the findings contract, so `--strict` works unchanged."""
    return {
        "rule_id": f"compare.{diff['kind']}",
        "severity": CRITICAL,
        "message": (
            f"{capability}: {diff['rule_id']} is new for {diff['subject']} "
            f"(run {run}) — {diff['message']}"
        ),
        "observed": diff["current_severity"],
        "expected": None,
        "subject": diff["subject"],
        "location": diff["capability"],
    }


# Reports written before the `capability` field existed still identify
# themselves by `source.kind`, which has been stable since the first report.
# Falling back keeps real observations comparable instead of discarding them as
# unrecognised.
_SOURCE_KIND_CAPABILITY = {
    "static_dir": "on-page",
    "redirect_file": "redirects",
    "live_crawl": "live-crawl",
}


def _reports_by_capability(workspace_root: Path, domain: str, run: str) -> dict[str, dict]:
    directory = report_module.runs_dir(workspace_root, domain) / run
    reports: dict[str, dict] = {}
    for path in sorted(directory.glob("*.json")):
        if path.name == "receipt.json":
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("capability") == "compare":
            continue
        capability = data.get("capability") or _SOURCE_KIND_CAPABILITY.get(
            (data.get("source") or {}).get("kind")
        )
        if capability:
            reports[capability] = data
    return reports


def run(config, baseline: str | None = None, current: str | None = None, **_) -> dict[str, Any]:
    """Entry point for the registry. The CLI passes --baseline and --current."""
    # Resolve the current run first, then look *behind* it. Doing it the other
    # way round makes "latest" resolve to the baseline and compares a run with
    # itself, which is a comparison that can never report anything.
    current_run = current or _latest_run(config)
    baseline_run = baseline or pick_baseline(config.workspace_root, config.domain, current_run)
    if baseline_run == current_run:
        raise CompareError(
            f"Baseline and current are both {current_run}.\n"
            f"Run an audit to produce a newer run, or pass --baseline and --current "
            f"explicitly. Available runs: "
            f"{', '.join(report_module.list_runs(config.workspace_root, config.domain))}"
        )
    comparison = build(config.workspace_root, config.domain, baseline_run, current_run)
    comparison["site"]["url"] = config.site_url
    return comparison


def _latest_run(config) -> str | None:
    runs = report_module.list_runs(config.workspace_root, config.domain)
    return runs[-1] if runs else None