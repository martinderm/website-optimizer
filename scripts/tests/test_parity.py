"""Parity against the tool this capability replaces.

The original `hugo-wizard/scripts/audit-site-seo.py` remains the reference until
it is removed. This test runs both over the same fixture directory and compares
the findings they would report to a human.

It compares `(page, severity, message)` triples rather than whole documents,
because the JSON shape intentionally changed: two loose lists of strings became
atomic findings. What must not change is which defects are reported and what they
are called — otherwise the migration silently changed the tool's verdicts.

Skipped once the original is gone, which is the intended end state.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wo.capabilities.on_page.audit import find_static_dir, run  # noqa: E402
from wo.config import SiteConfig  # noqa: E402

ORIGINAL = Path("D:/users/dagobert/agents/hugo-wizard/scripts/audit-site-seo.py")
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "site"
SITE_URL = "https://example.com"


def _triples_from_original(target: Path) -> set[tuple[str, str, str]]:
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
        out = Path(fh.name)
    try:
        proc = subprocess.run(
            [sys.executable, str(ORIGINAL), str(target),
             "--site-url", SITE_URL, "--json"],
            capture_output=True, text=True, check=True,
        )
        payload = __import__("json").loads(proc.stdout)
        triples = set()
        for page, result in payload["findings"].items():
            for issue in result["issues"]:
                triples.add((page, "critical", issue))
            for warning in result["warnings"]:
                triples.add((page, "warning", warning))
        return triples
    finally:
        out.unlink(missing_ok=True)


def _triples_from_new(static_dir: Path) -> set[tuple[str, str, str]]:
    config = SiteConfig(
        site_url=SITE_URL,
        domain="example.com",
        static_dir=static_dir,
        workspace_root=static_dir.parent,
    )
    report = run(config)
    return {(f["page"], f["severity"], f["message"]) for f in report["findings"]}


@unittest.skipUnless(ORIGINAL.is_file(), "reference implementation has been removed")
class ParityTest(unittest.TestCase):
    def setUp(self):
        self.target = find_static_dir(FIXTURES)
        self.original = _triples_from_original(self.target)
        self.new = _triples_from_new(self.target)

    def test_same_number_of_findings(self):
        self.assertEqual(len(self.original), len(self.new))

    def test_identical_findings(self):
        missing = self.original - self.new
        extra = self.new - self.original
        self.assertEqual(missing, set(), "findings the original reports are now lost")
        self.assertEqual(extra, set(), "findings the original did not report are now invented")

    def test_summary_counts_agree(self):
        config = SiteConfig(
            site_url=SITE_URL, domain="example.com",
            static_dir=self.target, workspace_root=self.target.parent,
        )
        summary = run(config)["summary"]
        self.assertEqual(summary["total_html_files"], 3)
        self.assertEqual(summary["audited_pages"], 3)
        self.assertEqual(summary["pages_with_findings"], 2)
        self.assertEqual(summary["total_critical_issues"],
                         sum(1 for t in self.original if t[1] == "critical"))
        self.assertEqual(summary["total_warnings"],
                         sum(1 for t in self.original if t[1] == "warning"))

    def test_original_module_still_importable_for_future_reference(self):
        spec = importlib.util.spec_from_file_location("legacy_audit", ORIGINAL)
        self.assertIsNotNone(spec and spec.loader)


if __name__ == "__main__":
    unittest.main()