"""Redirect capability: does the live site actually behave as its rules say?

Ported from `hugo-wizard/scripts/verify-redirects.py`. Rule loading, status
handling, retry behaviour and the wildcard exemption are unchanged, so the port
is verifiable against the original.

**Response bodies are never read.** Only status lines and the `Location` header
are consumed. That is not a performance choice: a redirect target is arbitrary
content, and this capability deliberately has no path by which a server's HTML
could reach the report (decision D13).

Findings are atomic and failures only — a rule that passes produces a row in
`checks`, not a finding. The verdict is derived from the rows.
"""

from __future__ import annotations

import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ...report import TOOL_NAME, TOOL_VERSION
from .parse import MappingError, dedupe, load_mappings

CRITICAL = "critical"
WARNING = "warning"
REPORT_VERSION = "1"
REDIRECT_CODES = (301, 302, 307, 308)
USER_AGENT = "Mozilla/5.0 (compatible; website-optimizer/0.2; +redirect-audit)"

# Rule ids this capability can emit, whether or not they fired. See the note in
# the on-page capability: a report that lists only failures cannot distinguish
# "nothing is broken" from "this check did not run".
CHECKS: tuple[str, ...] = (
    "redirect.location_mismatch",
    "redirect.status_unexpected",
    "redirect.unreachable",
    "redirect.target_unreachable",
    "redirect.failed",
)


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Surface redirects instead of following them."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _finding(rule_id, severity, message, observed, expected, subject, location):
    return {
        "rule_id": rule_id,
        "severity": severity,
        "message": message,
        "observed": observed,
        "expected": expected,
        "subject": subject,
        "location": location,
    }


def _absolute(url: str, base: str) -> str:
    if url.startswith(("http://", "https://")):
        return url
    return base.rstrip("/") + ("/" if not url.startswith("/") else "") + url


def probe(base_url: str, source: str, expected: str, opener, *, check_target: bool,
          is_wildcard: bool, timeout: int) -> dict[str, Any]:
    """Request one rule's source URL and record what the server actually did."""
    requested = _absolute(source, base_url)
    expected_full = _absolute(expected, base_url)

    row: dict[str, Any] = {
        "source": source,
        "requested_url": requested,
        "expected_target": expected_full,
        "status_code": None,
        "location": None,
        "redirect_valid": False,
        "target_status": None,
        "target_valid": False,
        "is_wildcard": is_wildcard,
        "success": False,
        "error": None,
    }

    request = urllib.request.Request(requested, headers={"User-Agent": USER_AGENT})
    for attempt in range(3):
        try:
            response = opener.open(request, timeout=timeout)
            row["status_code"] = response.status
            row["error"] = f"No redirect returned (HTTP {response.status} OK)"
            break
        except urllib.error.HTTPError as exc:
            row["status_code"] = exc.code
            if exc.code in REDIRECT_CODES:
                location = exc.headers.get("Location", "")
                row["location"] = location
                if (location.rstrip("/") == expected_full.rstrip("/")
                        or location.rstrip("/") == expected.rstrip("/")
                        or location in (expected, expected_full)):
                    row["redirect_valid"] = True
                else:
                    row["error"] = f"Location mismatch: got '{location}', expected '{expected_full}'"
            else:
                row["error"] = f"Unexpected HTTP status {exc.code}"
            break
        except Exception as exc:  # noqa: BLE001 - network failure is a result, not a crash
            if attempt == 2:
                row["error"] = f"Connection error: {exc}"
            time.sleep(1)

    # A wildcard rule was only ever probed with a sample slug, so its target is
    # not a real page and must not be treated as a 404.
    effective_check = check_target and not is_wildcard
    if row["redirect_valid"] and effective_check:
        target = row["location"] or expected_full
        target_request = urllib.request.Request(target, headers={"User-Agent": USER_AGENT})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(target_request, timeout=timeout) as response:
                    row["target_status"] = response.status
                    if response.status == 200:
                        row["target_valid"] = True
                break
            except urllib.error.HTTPError as exc:
                row["target_status"] = exc.code
                row["error"] = f"Target endpoint returned HTTP {exc.code}"
                break
            except Exception as exc:  # noqa: BLE001
                if attempt == 2:
                    row["error"] = f"Target endpoint connection error: {exc}"
                time.sleep(1)
    elif row["redirect_valid"]:
        row["target_valid"] = True

    row["success"] = row["redirect_valid"] and (row["target_valid"] if effective_check else True)
    return row


def _findings_from_row(row: dict[str, Any], check_target: bool) -> list[dict[str, Any]]:
    if row["success"]:
        return []

    source = row["source"]
    error = row["error"] or "Redirect failed"

    if not row["redirect_valid"]:
        if row["status_code"] is None:
            rule_id, severity = "redirect.unreachable", CRITICAL
        elif row["status_code"] in REDIRECT_CODES:
            rule_id, severity = "redirect.location_mismatch", CRITICAL
        else:
            rule_id, severity = "redirect.status_unexpected", CRITICAL
    elif check_target and not row["target_valid"]:
        rule_id, severity = "redirect.target_unreachable", CRITICAL
    else:
        rule_id, severity = "redirect.failed", WARNING

    return [_finding(rule_id, severity, error,
                     row["location"] or row["status_code"],
                     row["expected_target"],
                     source, row["requested_url"])]


def run(config, **_ignored) -> dict[str, Any]:
    """Probe every configured redirect rule against the live site."""
    settings = config.redirects
    base = config.site_url
    redirect_file = Path(settings["file"])
    if not redirect_file.is_absolute():
        redirect_file = config.workspace_root / redirect_file

    try:
        mappings = dedupe(load_mappings(redirect_file))
    except MappingError as exc:
        raise FileNotFoundError(str(exc)) from exc

    if not mappings:
        raise FileNotFoundError(
            f"{redirect_file.name} contains no redirect rules.\n"
            f"Check that the rules use a status the parser recognises, or that the "
            f"file is the one this site actually serves."
        )

    opener = urllib.request.build_opener(_NoRedirectHandler)
    check_target = settings["check_target"]
    timeout = settings["timeout"]

    checks: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    for source, expected, wildcard in mappings:
        row = probe(base, source, expected, opener,
                    check_target=check_target, is_wildcard=wildcard, timeout=timeout)
        checks.append(row)
        findings.extend(_findings_from_row(row, check_target))

    passed = sum(1 for row in checks if row["success"])
    critical = sum(1 for f in findings if f["severity"] == CRITICAL)

    return {
        "report_version": REPORT_VERSION,
        "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        # Live probing is what a redirect is; calling it anything else would
        # make a later comparison silently meaningless.
        "crawl_mode": "live",
        "site": {"url": base, "domain": config.domain},
        "capability": "redirects",
        "source": {"kind": "redirect_file", "path": _display_path(redirect_file, config)},
        "rules_run": list(CHECKS),
        "summary": {
            "total_tested": len(checks),
            "passed": passed,
            "failed": len(checks) - passed,
            "check_targets_enabled": check_target,
            "total_critical_issues": critical,
            "total_warnings": len(findings) - critical,
        },
        "checks": checks,
        "findings": findings,
    }


def _display_path(path: Path, config) -> str:
    """Store the rule file workspace-relative, never as a local absolute path."""
    try:
        return path.resolve().relative_to(config.workspace_root.resolve()).as_posix()
    except ValueError:
        return path.name