"""TOOL_VERSION must move when `rules_run` moves.

D43 closed with this check named and unbuilt:

    "A check that the version string differs whenever `CHECKS` does - the same
     shape as the existing round-trip test between `CHECKS` and the rules a
     capability can actually emit. Not built; noted so the next person does not
     rediscover it."

D49 reviewed the no-CI decision and found that this check has exactly one place to
live: the test suite, because under no-CI the suite is the only thing that runs.

**Why a marker file and not a hash of the source.** The honest signal is "the rule
set a capability can emit differs from the one this version was stamped for". A
hash of `audit.py` would fire on every comment and every refactor, and a check
that cries wolf gets disabled - which is the failure mode D39's consequence
paragraph is about. So the fingerprint is the rule sets themselves.

**What a failure looks like.** The version is bumped, or the fingerprint is
updated because nothing about the rules actually changed. Note the second half:
editing a message text is not a rule change under D43, and the fingerprint must
not pretend otherwise.
"""

from __future__ import annotations

import importlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from wo.capabilities import REGISTRY  # noqa: E402
from wo.capabilities.compare.audit import KINDS  # noqa: E402
from wo.report import TOOL_VERSION  # noqa: E402

MARKER = Path(__file__).resolve().parent / "version-fingerprint.json"


def _fingerprint() -> dict[str, object]:
    """The rule set per capability, plus the version it was stamped for.

    `compare` declares no `CHECKS` — its rule set is `KINDS`, the five
    classifications. It has to be included explicitly, because it is the one that
    already changed once: D44 added `unattributed`, which moved `rules_run` and
    was a version bump under D43. A fingerprint that skipped it would miss the
    case that prompted this file.
    """
    per_capability: dict[str, list[str]] = {}
    for name, entry in sorted(REGISTRY.items()):
        module = importlib.import_module(entry["module"])
        checks = getattr(module, "CHECKS", ()) or ()
        if checks:
            per_capability[name] = sorted(checks)
    per_capability["compare"] = sorted(KINDS)
    return {"version": TOOL_VERSION, "rules": per_capability}


class VersionFollowsRulesTest(unittest.TestCase):
    def setUp(self):
        self.marker = json.loads(MARKER.read_text(encoding="utf-8"))
        self.current = _fingerprint()

    def test_the_fingerprint_covers_every_capability_that_declares_checks(self):
        """A capability with CHECKS but no entry would be silently unguarded."""
        declared = set(self.current["rules"])
        in_marker = set(self.marker["rules"])
        self.assertEqual(
            declared - in_marker, set(),
            "Capabilities declaring CHECKS but absent from the fingerprint. Add "
            "them and update the marker deliberately.",
        )
        self.assertEqual(
            in_marker - declared, set(),
            "The fingerprint names capabilities that no longer declare CHECKS.",
        )

    def test_the_rules_have_not_changed_since_the_version_was_stamped(self):
        stored = self.marker["rules"]
        self.assertEqual(
            self.current["rules"], stored,
            "The rule set changed. Under D43 that is a version bump: raise "
            "TOOL_VERSION in scripts/wo/report.py, then re-run this suite to "
            "refresh scripts/tests/version-fingerprint.json.\n"
            f"  baseline: {json.dumps(stored, sort_keys=True)}\n"
            f"  current : {json.dumps(self.current['rules'], sort_keys=True)}",
        )

    def test_the_marker_records_the_current_version(self):
        """Catches a bump that happened without the marker being refreshed.

        The failure is asymmetric on purpose: a version raised without the marker
        updated is the *correct* action taken incompletely, and it should be
        visible rather than silently passing.
        """
        if self.marker["rules"] == self.current["rules"]:
            self.assertEqual(
                self.marker["version"], TOOL_VERSION,
                "TOOL_VERSION changed but the fingerprint still names the old one. "
                "Re-run the suite to refresh it.",
            )

    def test_compare_kinds_are_covered(self):
        """compare declares no CHECKS, so KINDS is its rule set and must be seen."""
        self.assertIn(
            "compare", self.marker["rules"],
            "compare's rule set is KINDS, not CHECKS. Without an entry for it, a "
            "change like D44's added `unattributed` would not move the fingerprint.",
        )
        self.assertEqual(self.marker["rules"]["compare"], sorted(KINDS))
