"""Difference attribution: the reason a comparison never refuses, only explains.

These tests are the decision under test. If they pass but the behaviour is
subtly wrong, `compare` will confidently mislabel a broken page as a newly
added rule — the exact confusion it exists to remove.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wo import report as report_module  # noqa: E402
from wo.capabilities.compare.audit import (  # noqa: E402
    CHECK_CHANGE, IMPROVEMENT, REGRESSION, SITE_CHANGE, CompareError, build,
    classify, pick_baseline,
)
from wo.capabilities.compare.audit import run as compare_run  # noqa: E402
from wo.config import SiteConfig  # noqa: E402


def _finding(rule_id, subject, severity="critical"):
    return {
        "rule_id": rule_id, "severity": severity, "message": f"{rule_id} on {subject}",
        "observed": None, "expected": None, "subject": subject,
        "location": "head",
    }


def _report(findings, rules_run, capability="on-page", version="0.2.0",
            crawl_mode="static", pages=None):
    report = {
        "report_version": "1",
        "tool": {"name": "website-optimizer", "version": version},
        "crawl_mode": crawl_mode,
        "capability": capability,
        "site": {"url": "https://x", "domain": "x"},
        "rules_run": list(rules_run),
        "findings": findings,
    }
    if pages is not None:
        report["summary"] = {"audited_pages": pages}
    return report


RULES = ("title.missing", "img.alt.missing", "canonical.missing")


class ClassifyTest(unittest.TestCase):
    def test_new_critical_finding_is_a_regression(self):
        before = _report([], RULES)
        after = _report([_finding("img.alt.missing", "a.html")], RULES)
        kinds = {d["kind"] for d in classify(before, after)}
        self.assertEqual(kinds, {REGRESSION})

    def test_new_warning_finding_is_a_site_change_not_a_regression(self):
        # The rule exists in both runs, so the difference can only be the site.
        rules = RULES + ("description.short",)
        before = _report([], rules)
        after = _report([_finding("description.short", "a.html", "warning")], rules)
        kinds = {d["kind"] for d in classify(before, after)}
        self.assertEqual(kinds, {SITE_CHANGE})

    def test_a_rule_added_to_the_tool_is_not_a_regression(self):
        """The whole point: a new check must not read as a broken site."""
        before = _report([], ("title.missing",))
        after = _report([_finding("img.alt.missing", "a.html")], ("title.missing", "img.alt.missing"))
        diffs = classify(before, after)
        self.assertEqual([d["kind"] for d in diffs], [CHECK_CHANGE])
        self.assertEqual(diffs[0]["rule_id"], "img.alt.missing")

    def test_a_rule_removed_from_the_tool_is_also_a_check_change(self):
        before = _report([_finding("img.alt.missing", "a.html")], ("title.missing", "img.alt.missing"))
        after = _report([], ("title.missing",))
        self.assertEqual([d["kind"] for d in classify(before, after)], [CHECK_CHANGE])

    def test_resolved_finding_is_an_improvement(self):
        before = _report([_finding("img.alt.missing", "a.html")], RULES)
        after = _report([], RULES)
        self.assertEqual([d["kind"] for d in classify(before, after)], [IMPROVEMENT])

    def test_severity_worsening_is_a_regression(self):
        before = _report([_finding("img.alt.missing", "a.html", "warning")], RULES)
        after = _report([_finding("img.alt.missing", "a.html", "critical")], RULES)
        self.assertEqual([d["kind"] for d in classify(before, after)], [REGRESSION])

    def test_severity_improving_is_a_site_change(self):
        before = _report([_finding("img.alt.missing", "a.html", "critical")], RULES)
        after = _report([_finding("img.alt.missing", "a.html", "warning")], RULES)
        self.assertEqual([d["kind"] for d in classify(before, after)], [SITE_CHANGE])

    def test_identical_reports_produce_no_differences(self):
        report = _report([_finding("img.alt.missing", "a.html")], RULES)
        self.assertEqual(classify(report, dict(report)), [])

    def test_findings_are_matched_by_rule_and_subject(self):
        before = _report([_finding("img.alt.missing", "a.html")], RULES)
        after = _report([_finding("img.alt.missing", "b.html")], RULES)
        kinds = sorted(d["kind"] for d in classify(before, after))
        self.assertEqual(kinds, [IMPROVEMENT, REGRESSION])

    def test_report_without_rules_run_is_still_comparable(self):
        """Older reports predate rules_run; they must not crash the comparison."""
        before = {"findings": [], "rules_run": []}
        after = _report([_finding("img.alt.missing", "a.html")], RULES)
        # Without a declared rule set, a new critical finding is still a regression.
        self.assertEqual([d["kind"] for d in classify(before, after)], [REGRESSION])


class ScopeTest(unittest.TestCase):
    """A run that looked at a different amount of the site explains nothing.

    Found by running compare on real stored runs: a baseline that was a live
    crawl covering 25 of 173 pages against a static run covering all 173 reported
    schema.identifier_conflicting as a regression. The rule set was identical and
    the site had not moved. That rule has to meet the same @id on two pages, and
    a quarter of the site cannot produce that.
    """

    def test_a_new_finding_across_unequal_scope_is_not_a_regression(self):
        before = _report([], RULES, pages=25)
        after = _report([_finding("schema.identifier_conflicting", "https://x/#artist")],
                        RULES, pages=173)
        diffs = classify(before, after)
        self.assertEqual([d["kind"] for d in diffs], ["unattributed"])
        # The reason has to name both counts, or it is just another verdict.
        self.assertIn("25", diffs[0]["reason"])
        self.assertIn("173", diffs[0]["reason"])

    def test_a_vanished_finding_across_unequal_scope_is_not_an_improvement(self):
        """Unequal scope confounds both directions, not only the alarming one.

        Fewer pages is expected to find less, so a missing finding is no more
        evidence of a fixed site than a new one is of a broken one.
        """
        before = _report([_finding("img.alt.missing", "a.html")], RULES, pages=173)
        after = _report([], RULES, pages=25)
        self.assertEqual([d["kind"] for d in classify(before, after)], ["unattributed"])

    def test_equal_scope_still_classifies_normally(self):
        before = _report([], RULES, pages=173)
        after = _report([_finding("img.alt.missing", "a.html", "warning")], RULES, pages=173)
        self.assertEqual([d["kind"] for d in classify(before, after)], ["site-change"])

    def test_a_check_change_is_still_a_check_change_across_unequal_scope(self):
        """The kind of difference is still known even when the site is not.

        Withholding the label wholesale would lose information we do have: we
        still know the rule set differs.
        """
        before = _report([], ("title.missing",), pages=25)
        after = _report([_finding("img.alt.missing", "a.html")],
                        ("title.missing", "img.alt.missing"), pages=173)
        self.assertEqual([d["kind"] for d in classify(before, after)], ["unattributed"])

    def test_unknown_scope_does_not_withhold_anything(self):
        """A report without the counter must not silence every comparison.

        Refusing against every older report would trade a narrow misattribution
        for total silence, which is the trade D25 exists to prevent.
        """
        before = _report([], RULES)
        after = _report([_finding("img.alt.missing", "a.html")], RULES)
        self.assertEqual([d["kind"] for d in classify(before, after)], [REGRESSION])

    def test_crawl_block_is_the_fallback_for_older_reports(self):
        before = _report([], RULES)
        before["crawl"] = {"requested": 25, "fetched": 25}
        after = _report([_finding("img.alt.missing", "a.html")], RULES, pages=173)
        self.assertEqual([d["kind"] for d in classify(before, after)], ["unattributed"])

    def test_scope_is_reported_per_capability_in_the_comparison(self):
        before = _report([], RULES, pages=25)
        after = _report([_finding("img.alt.missing", "a.html")], RULES, pages=173)
        with tempfile.TemporaryDirectory() as root:
            for name, payload in (("b", before), ("c", after)):
                d = Path(root) / "memory" / "evidence" / "websites" / "x" / "runs" / name
                d.mkdir(parents=True)
                (d / "report.json").write_text(json.dumps(payload), encoding="utf-8")
            result = build(Path(root), "x", "b", "c")
        self.assertEqual(result["scope_changed"], ["on-page"])
        self.assertEqual(result["scope"][0]["baseline_pages"], 25)
        self.assertEqual(result["scope"][0]["current_pages"], 173)
        self.assertFalse(result["scope"][0]["equal"])
        # Not a finding: --strict must not fail on something unexplained.
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["summary"]["unattributed"], 1)
        self.assertEqual(result["summary"]["regression"], 0)


class RunSelectionTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _config(self):
        return SiteConfig(site_url="https://x", domain="x", static_dir=self.root,
                          workspace_root=self.root)

    def test_baseline_is_the_run_before_the_current_one(self):
        config = self._config()
        for run in ("2026-01-01T00-00-00Z", "2026-01-02T00-00-00Z", "2026-01-03T00-00-00Z"):
            report_module.write_run(config, _report([], RULES), run=run)
        self.assertEqual(
            pick_baseline(self.root, "x", "2026-01-03T00-00-00Z"),
            "2026-01-02T00-00-00Z",
        )

    def test_run_resolves_current_first_so_it_cannot_compare_a_run_with_itself(self):
        """Regression guard: resolving the baseline first picks 'latest' twice."""
        config = self._config()
        for run in ("2026-01-01T00-00-00Z", "2026-01-02T00-00-00Z"):
            report_module.write_run(config, _report([], RULES), run=run)
        comparison = compare_run(config)
        self.assertEqual(comparison["baseline"]["run"], "2026-01-01T00-00-00Z")
        self.assertEqual(comparison["current"]["run"], "2026-01-02T00-00-00Z")

    def test_baseline_skips_runs_of_other_capabilities(self):
        """Capabilities do not all run every time; 'the previous run' is often wrong."""
        config = self._config()
        report_module.write_run(config, _report([], RULES), run="2026-01-01T00-00-00Z")
        report_module.write_run(config, _report([], RULES, capability="redirects"),
                                run="2026-01-02T00-00-00Z")
        report_module.write_run(config, _report([], RULES), run="2026-01-03T00-00-00Z")
        self.assertEqual(
            pick_baseline(self.root, "x", "2026-01-03T00-00-00Z"),
            "2026-01-01T00-00-00Z",
        )
        comparison = compare_run(config)
        self.assertEqual(comparison["baseline"]["run"], "2026-01-01T00-00-00Z")
        self.assertEqual(comparison["current"]["run"], "2026-01-03T00-00-00Z")

    def test_identical_baseline_and_current_are_refused(self):
        config = self._config()
        report_module.write_run(config, _report([], RULES), run="2026-01-01T00-00-00Z")
        with self.assertRaises(CompareError) as caught:
            compare_run(config, baseline="2026-01-01T00-00-00Z",
                        current="2026-01-01T00-00-00Z")
        self.assertIn("both", str(caught.exception))

    def test_first_run_has_no_baseline(self):
        self.assertIsNone(pick_baseline(self.root, "x", None))

    def test_build_refuses_only_when_there_is_nothing_to_compare(self):
        with self.assertRaises(CompareError) as caught:
            build(self.root, "x", None, None)
        self.assertIn("first stored run", str(caught.exception))

    def test_build_names_available_runs_when_one_is_missing(self):
        config = self._config()
        report_module.write_run(config, _report([], RULES), run="2026-01-01T00-00-00Z")
        with self.assertRaises(CompareError) as caught:
            build(self.root, "x", "1999-01-01T00-00-00Z", "2026-01-01T00-00-00Z")
        self.assertIn("2026-01-01T00-00-00Z", str(caught.exception))

    def test_runs_without_a_shared_capability_are_refused_explicitly(self):
        config = self._config()
        report_module.write_run(config, _report([], RULES), run="2026-01-01T00-00-00Z")
        report_module.write_run(config, _report([], RULES, capability="redirects"),
                                run="2026-01-02T00-00-00Z")
        with self.assertRaises(CompareError) as caught:
            build(self.root, "x", "2026-01-01T00-00-00Z", "2026-01-02T00-00-00Z")
        self.assertIn("share no capability", str(caught.exception))

    def test_legacy_reports_without_a_capability_field_are_recognised(self):
        """Runs predating the `capability` field are real observations, not litter."""
        config = self._config()
        legacy = _report([], RULES)
        del legacy["capability"]
        legacy["source"] = {"kind": "static_dir", "path": "public"}
        report_module.write_run(config, legacy, run="2026-01-01T00-00-00Z")
        report_module.write_run(config, _report([], RULES), run="2026-01-02T00-00-00Z")
        comparison = build(self.root, "x", "2026-01-01T00-00-00Z", "2026-01-02T00-00-00Z")
        self.assertEqual(comparison["summary"]["compared_capabilities"], 1)

    def test_comparison_artifacts_are_skipped_when_scanning_a_run_folder(self):
        """A run folder holding report.json *and* comparison.json has one input."""
        config = self._config()
        report_module.write_run(config, _report([], RULES), run="2026-01-01T00-00-00Z")
        report_module.write_run(config, _report([], RULES), run="2026-01-02T00-00-00Z")
        report_module.write_run(config, {
            "capability": "compare", "tool": {"version": "0.2.0"},
            "crawl_mode": "static", "findings": [], "rules_run": ["regression"],
        }, run="2026-01-02T00-00-00Z", filename="comparison.json")

        comparison = build(self.root, "x", "2026-01-01T00-00-00Z", "2026-01-02T00-00-00Z")
        self.assertEqual([p["capability"] for p in comparison["compared"]], ["on-page"])


class BuildTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.config = SiteConfig(site_url="https://x", domain="x",
                                 static_dir=self.root, workspace_root=self.root)
        report_module.write_run(
            self.config, _report([], ("title.missing",)), run="2026-01-01T00-00-00Z")
        report_module.write_run(
            self.config,
            _report([_finding("img.alt.missing", "a.html")], ("title.missing", "img.alt.missing")),
            run="2026-01-02T00-00-00Z")

    def tearDown(self):
        self._tmp.cleanup()

    def test_comparison_reports_a_check_change_not_a_regression(self):
        comparison = build(self.root, "x", "2026-01-01T00-00-00Z", "2026-01-02T00-00-00Z")
        self.assertEqual(comparison["summary"]["check-change"], 1)
        self.assertEqual(comparison["summary"]["regression"], 0)
        # A check change must not raise the regression counter that --strict reads.
        self.assertEqual(comparison["summary"]["total_critical_issues"], 0)
        self.assertEqual(comparison["findings"], [])

    def test_provenance_change_is_reported_not_used_as_a_filter(self):
        report_module.write_run(
            self.config, _report([], ("title.missing",), version="0.9.0"),
            run="2026-01-03T00-00-00Z")
        comparison = build(self.root, "x", "2026-01-02T00-00-00Z", "2026-01-03T00-00-00Z")
        self.assertEqual(comparison["provenance_changed"], ["on-page"])
        self.assertEqual(comparison["summary"]["compared_capabilities"], 1)

    def test_comparison_itself_is_written_as_its_own_run(self):
        run_id = "2026-01-04T00-00-00Z"
        comparison = build(self.root, "x", "2026-01-01T00-00-00Z", "2026-01-02T00-00-00Z")
        written = report_module.write_run(self.config, comparison, run=run_id,
                                         filename="comparison.json")
        self.assertTrue(written["report"].is_file())
        on_disk = json.loads(written["report"].read_text(encoding="utf-8"))
        self.assertEqual(on_disk["baseline"]["run"], "2026-01-01T00-00-00Z")
        # Evidence stays append-only: the compared runs are untouched.
        self.assertEqual(
            len(report_module.list_runs(self.root, "x")),
            3,
        )


if __name__ == "__main__":
    unittest.main()