"""Redirect rule parsing and finding derivation, without touching the network."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wo.capabilities.redirects import audit as redirect_audit  # noqa: E402
from wo.capabilities.redirects.parse import (  # noqa: E402
    MappingError, clean_regex_to_path, dedupe, load_mappings,
)

HTACCESS = """\
# sample
RewriteEngine On
RewriteRule ^bio/?$ /about/ [R=301,L]
RewriteRule ^portfolio/items/?$ /projects/ [R=301,L]
RewriteRule ^portfolio/items/([^/]+)/?$ /projects/$1/ [R=301,L]
RewriteRule ^(.*)$ https://example.com/$1 [R=301,L]
Redirect 301 /statement /works/
"""

REDIRECTS = """\
# Cloudflare Pages format
/portfolio/items/      /projects/          301
/portfolio/items/*     /projects/:splat    301
/old-cms/page         /new-cms/page       302
"""


class ParserTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _write(self, name: str, text: str) -> Path:
        path = self.dir / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_regex_becomes_a_requestable_path(self):
        path, captured, wildcard = clean_regex_to_path(r"^portfolio/items/([^/]+)/?$")
        # The optional trailing slash is preserved as a real slash, matching the
        # original tool: the request has to hit the URL the rule actually serves.
        self.assertEqual(path, "/portfolio/items/test-sample-item/")
        self.assertEqual(captured, "test-sample-item")
        self.assertTrue(wildcard)

    def test_literal_rule_is_not_a_wildcard(self):
        _, _, wildcard = clean_regex_to_path(r"^bio/?$")
        self.assertFalse(wildcard)

    def test_htaccess_rules_and_the_global_rewrite_is_skipped(self):
        mappings = load_mappings(self._write(".htaccess", HTACCESS))
        sources = [m[0] for m in mappings]
        self.assertIn("/bio/", sources)
        self.assertIn("/portfolio/items/", sources)
        self.assertIn("/portfolio/items/test-sample-item/", sources)
        self.assertIn("/statement", sources)
        # The force-HTTPS/canonical catch-all is not a route and must not appear.
        self.assertNotIn("/test-sample-item", sources)
        # The mapping's target, not its source, is what /portfolio/items/ maps to.
        targets = [m[1] for m in mappings]
        self.assertIn("/projects/", targets)

    def test_wildcard_is_flagged_so_its_sample_target_is_not_checked(self):
        mappings = load_mappings(self._write(".htaccess", HTACCESS))
        wildcards = {m[0] for m in mappings if m[2]}
        self.assertIn("/portfolio/items/test-sample-item/", wildcards)
        self.assertNotIn("/bio/", wildcards)

    def test_netlify_splat_substitution(self):
        mappings = load_mappings(self._write("_redirects", REDIRECTS))
        pair = [(m[0], m[1], m[2]) for m in mappings]
        self.assertIn(("/portfolio/items/sample-item", "/projects/sample-item", True), pair)
        self.assertIn(("/old-cms/page", "/new-cms/page", False), pair)

    def test_json_mappings_in_both_shapes(self):
        self.assertEqual(
            load_mappings(self._write("m.json", '{"a": "/b"}')),
            [("a", "/b", False)],
        )
        self.assertEqual(
            load_mappings(self._write("m.json", '[{"from": "/a", "to": "/b"}]')),
            [("/a", "/b", False)],
        )

    def test_csv_and_tsv(self):
        self.assertEqual(
            load_mappings(self._write("m.csv", "a,/b\nc,/d\n")),
            [("a", "/b", False), ("c", "/d", False)],
        )

    def test_missing_file_names_the_fix(self):
        with self.assertRaises(MappingError) as caught:
            load_mappings(self.dir / "nope.htaccess")
        self.assertIn("site.optimizer.toml", str(caught.exception))

    def test_invalid_json_names_the_problem(self):
        with self.assertRaises(MappingError):
            load_mappings(self._write("m.json", "{not json"))

    def test_dedupe_keeps_first_seen_order(self):
        mappings = [("/a", "/b", False), ("/a", "/b", False), ("/c", "/d", True)]
        self.assertEqual(dedupe(mappings), [("/a", "/b", False), ("/c", "/d", True)])


class FindingTest(unittest.TestCase):
    def _row(self, **kwargs):
        base = {
            "source": "/old/", "requested_url": "https://x/old/",
            "expected_target": "https://x/new/", "status_code": 301,
            "location": "https://x/new/", "redirect_valid": True,
            "target_status": 200, "target_valid": True,
            "is_wildcard": False, "success": True, "error": None,
        }
        base.update(kwargs)
        return base

    def test_passing_rule_produces_no_finding(self):
        self.assertEqual(redirect_audit._findings_from_row(self._row(), True), [])

    def test_location_mismatch_is_critical(self):
        row = self._row(success=False, redirect_valid=False,
                        error="Location mismatch: got 'https://x/other/', expected 'https://x/new/'")
        finding = redirect_audit._findings_from_row(row, True)[0]
        self.assertEqual(finding["rule_id"], "redirect.location_mismatch")
        self.assertEqual(finding["severity"], "critical")
        self.assertEqual(finding["expected"], "https://x/new/")
        self.assertEqual(finding["subject"], "/old/")

    def test_no_redirect_at_all(self):
        row = self._row(success=False, redirect_valid=False, status_code=200,
                        error="No redirect returned (HTTP 200 OK)")
        self.assertEqual(
            redirect_audit._findings_from_row(row, True)[0]["rule_id"],
            "redirect.status_unexpected",
        )

    def test_unreachable_source(self):
        row = self._row(success=False, redirect_valid=False, status_code=None,
                        error="Connection error: timeout")
        self.assertEqual(
            redirect_audit._findings_from_row(row, True)[0]["rule_id"],
            "redirect.unreachable",
        )

    def test_broken_target_is_its_own_rule(self):
        row = self._row(success=False, target_valid=False, target_status=404,
                        error="Target endpoint returned HTTP 404")
        finding = redirect_audit._findings_from_row(row, True)[0]
        self.assertEqual(finding["rule_id"], "redirect.target_unreachable")

    def test_finding_shape_matches_the_shared_contract(self):
        finding = redirect_audit._findings_from_row(
            self._row(success=False, redirect_valid=False, status_code=None,
                      error="Connection error"), True)[0]
        self.assertEqual(
            set(finding),
            {"rule_id", "severity", "message", "observed", "expected", "subject", "location"},
        )


if __name__ == "__main__":
    unittest.main()