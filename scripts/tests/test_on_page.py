"""Every rule fires when it should, and stays silent when it should not."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wo.capabilities.on_page.audit import CHECKS, RULES, audit_page, run  # noqa: E402
from wo.config import SiteConfig  # noqa: E402
from wo.page import extract_page  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "site" / "public"
SITE = "https://example.com"


def _ids(findings):
    return [f["rule_id"] for f in findings]


class RuleTest(unittest.TestCase):
    def setUp(self):
        self.index = extract_page(FIXTURES / "index.html", "index.html")
        self.clean = extract_page(FIXTURES / "ueber-uns" / "index.html", "clean.html")
        self.notfound = extract_page(FIXTURES / "404.html", "404.html")

    def test_all_rules_are_registered(self):
        self.assertEqual(len(RULES), 10)

    def test_checks_covers_every_rule_the_capability_can_emit(self):
        """`rules_run` is only trustworthy if it matches the rules.

        A rule missing from CHECKS would be invisible to `compare`, which
        attributes a difference to a check change only when the rule set says
        so. A stale CHECKS entry is just as wrong.
        """
        emitted = set()
        page = extract_page(FIXTURES / "index.html")
        for mutate in (
            lambda p: None,
            lambda p: setattr(p, "lang", None),
            lambda p: setattr(p, "title", ""),
            lambda p: setattr(p, "description", "kurz"),
            lambda p: setattr(p, "description", "x" * 400),
            lambda p: setattr(p, "description", None),
            lambda p: setattr(p, "canonical", None),
            lambda p: setattr(p, "canonical", "https://other.example/"),
            lambda p: setattr(p, "h1_count", 0),
            lambda p: setattr(p, "h1_count", 4),
            lambda p: setattr(p, "og", {}),
            lambda p: setattr(p, "twitter", {}),
            lambda p: (setattr(p, "has_main", False), setattr(p, "has_skip_link", False)),
            lambda p: setattr(p, "images_missing_alt", 3),
            lambda p: setattr(p, "robots", "noindex"),
        ):
            fresh = extract_page(FIXTURES / "index.html")
            mutate(fresh)
            emitted |= {f["rule_id"] for f in audit_page(fresh, SITE)}

        self.assertEqual(emitted - set(CHECKS), set(),
                         "a rule emits an id that CHECKS does not declare")
        self.assertEqual(set(CHECKS) - emitted, set(),
                         "CHECKS declares a rule that can never fire")

    def test_report_declares_the_rule_set_it_ran(self):
        config = SiteConfig(
            site_url=SITE, domain="example.com",
            static_dir=FIXTURES, workspace_root=FIXTURES.parent,
        )
        report = run(config)
        self.assertEqual(set(report["rules_run"]), set(CHECKS))
        self.assertEqual(report["capability"], "on-page")

    def test_page_with_findings(self):
        findings = audit_page(self.index, SITE)
        # index.html has a skip-link, so skiplink.missing must not fire.
        self.assertEqual(
            _ids(findings),
            ["og.description.missing", "twitter.card.missing", "img.alt.missing"],
        )
        alt = [f for f in findings if f["rule_id"] == "img.alt.missing"][0]
        self.assertEqual(alt["severity"], "critical")
        self.assertEqual(alt["observed"], 1)
        self.assertEqual(alt["expected"], 0)
        self.assertEqual(alt["message"], "1/2 <img> missing alt attribute")

    def test_clean_page_produces_nothing(self):
        self.assertEqual(audit_page(self.clean, SITE), [])

    def test_404_exempts_description_and_canonical(self):
        ids = _ids(audit_page(self.notfound, SITE))
        self.assertNotIn("description.missing", ids)
        self.assertNotIn("canonical.missing", ids)
        self.assertIn("og.title.missing", ids)

    def test_canonical_mismatch_uses_site_base(self):
        findings = audit_page(self.index, "https://other.example")
        ids = _ids(findings)
        self.assertIn("canonical.mismatch", ids)
        message = [f for f in findings if f["rule_id"] == "canonical.mismatch"][0]["message"]
        self.assertEqual(
            message,
            "Canonical URL 'https://example.com/' does not match expected site base "
            "URL 'https://other.example'",
        )

    def test_description_length_bounds(self):
        short = extract_page(FIXTURES / "index.html")
        short.description = "zu kurz"
        self.assertIn("description.short", _ids(audit_page(short, SITE)))
        long = extract_page(FIXTURES / "index.html")
        long.description = "x" * 320
        self.assertIn("description.long", _ids(audit_page(long, SITE)))

    def test_missing_lang_is_critical(self):
        page = extract_page(FIXTURES / "index.html")
        page.lang = None
        self.assertIn("lang.missing", _ids(audit_page(page, SITE)))

    def test_multiple_h1_is_a_warning(self):
        page = extract_page(FIXTURES / "index.html")
        page.h1_count = 3
        findings = [f for f in audit_page(page, SITE) if f["rule_id"] == "h1.multiple"]
        self.assertEqual(findings[0]["message"], "Multiple (3) <h1> headings found")
        self.assertEqual(findings[0]["severity"], "warning")

    def test_noindex_reports_unless_suppressed(self):
        page = extract_page(FIXTURES / "index.html")
        page.robots = "noindex, nofollow"
        self.assertIn("robots.noindex", _ids(audit_page(page, SITE)))
        self.assertNotIn("robots.noindex", _ids(audit_page(page, SITE, ignore_noindex=True)))


if __name__ == "__main__":
    unittest.main()