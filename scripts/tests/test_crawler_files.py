"""What a site publishes about itself: robots.txt, its sitemap, llms.txt.

The rules that matter most here are the ones about *not claiming* things:

- Coverage is not reported when the sitemap could not be read. A sitemap that
  fails to parse would otherwise make every page on the site look absent from it,
  which is a confident wrong answer about a hundred pages.
- An empty sitemap and an unreadable one are different defects. The first means
  the generator emitted nothing; the second means a soft 404 answered the request
  with a page.
- `Disallow: /` for one agent is not `Disallow: /` for everyone.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wo import jsonschema  # noqa: E402
from wo.capabilities.crawler_files import audit as cf  # noqa: E402
from wo.config import SiteConfig  # noqa: E402
from wo.page import Page, extract_page  # noqa: E402

SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "crawler-files-report.schema.json"

URLSET = ('<?xml version="1.0" encoding="utf-8"?>'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{}</urlset>')
EMPTY_URLSET = URLSET.format("")
INDEX = ('<?xml version="1.0" encoding="utf-8"?>'
         '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
         "<sitemap><loc>{}</loc></sitemap></sitemapindex>")
GOOD_ROBOTS = "User-agent: *\nDisallow: /admin/\n\nSitemap: https://example.com/sitemap.xml\n"


def _urlset(*urls: str) -> str:
    return URLSET.format("".join(f"<url><loc>{u}</loc></url>" for u in urls))


def _ids(result):
    return sorted(f["rule_id"] for f in result["findings"])


def _by_rule(result, rule_id):
    return [f for f in result["findings"] if f["rule_id"] == rule_id]


class RobotsTest(unittest.TestCase):
    def test_a_missing_robots_file_is_a_warning(self):
        result = cf.audit_sources(robots=None, sitemap=None, llms=None)
        findings = _by_rule(result, "robots.missing")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"], "warning")

    def test_disallow_all_is_critical(self):
        result = cf.audit_sources(robots="User-agent: *\nDisallow: /\n", sitemap=None, llms=None)
        self.assertEqual(_by_rule(result, "robots.blocks_site")[0]["severity"], "critical")

    def test_disallowing_a_path_is_not_disallowing_the_site(self):
        result = cf.audit_sources(robots="User-agent: *\nDisallow: /admin/\n",
                                  sitemap=None, llms=None)
        self.assertEqual(_by_rule(result, "robots.blocks_site"), [])

    def test_disallow_all_for_one_agent_is_not_disallow_all(self):
        """`Disallow: /` for Googlebot alone is a deliberate exclusion, not a lockout."""
        result = cf.audit_sources(robots="User-agent: Googlebot\nDisallow: /\n",
                                  sitemap=None, llms=None)
        self.assertEqual(_by_rule(result, "robots.blocks_site"), [])

    def test_blocking_assets_is_reported(self):
        result = cf.audit_sources(robots="User-agent: *\nDisallow: /css/\nDisallow: /js/\n",
                                  sitemap=None, llms=None)
        blocked = {f["observed"] for f in _by_rule(result, "robots.blocks_asset")}
        self.assertEqual(blocked, {"/css/", "/js/"})

    def test_a_sitemap_directive_is_required_but_not_invented(self):
        with_directive = cf.audit_sources(robots=GOOD_ROBOTS, sitemap=None, llms=None)
        self.assertEqual(_by_rule(with_directive, "robots.sitemap_missing"), [])
        without = cf.audit_sources(robots="User-agent: *\nDisallow: /admin/\n",
                                   sitemap=None, llms=None)
        self.assertEqual(len(_by_rule(without, "robots.sitemap_missing")), 1)

    def test_a_missing_robots_file_does_not_also_report_a_missing_directive(self):
        result = cf.audit_sources(robots=None, sitemap=None, llms=None)
        self.assertEqual(_by_rule(result, "robots.sitemap_missing"), [])


class SitemapTest(unittest.TestCase):
    def test_a_missing_sitemap_is_a_warning(self):
        result = cf.audit_sources(robots=GOOD_ROBOTS, sitemap=None, llms=None)
        self.assertEqual(_by_rule(result, "sitemap.missing")[0]["severity"], "warning")

    def test_an_unreadable_sitemap_is_critical(self):
        """A host that answers with its own HTML page, not a sitemap."""
        result = cf.audit_sources(robots=GOOD_ROBOTS, sitemap="<html><body>404</body></html>",
                                  llms=None)
        self.assertEqual(_by_rule(result, "sitemap.unreadable")[0]["severity"], "critical")

    def test_an_empty_sitemap_is_critical_and_is_not_an_unreadable_one(self):
        result = cf.audit_sources(robots=GOOD_ROBOTS, sitemap=EMPTY_URLSET, llms=None)
        self.assertEqual(_ids(result).count("sitemap.empty"), 1)
        self.assertEqual(_by_rule(result, "sitemap.unreadable"), [])

    def test_an_index_is_followed_to_the_sitemaps_it_names(self):
        child = "https://example.com/sitemap-pages.xml"
        result = cf.audit_sources(
            robots=GOOD_ROBOTS, sitemap=INDEX.format(child), llms=None,
            read_url=lambda url: _urlset("https://example.com/a/") if url == child else None,
        )
        self.assertEqual(result["sitemap_urls"], 1)

    def test_a_page_absent_from_the_sitemap_is_reported(self):
        result = cf.audit_sources(
            robots=GOOD_ROBOTS, sitemap=_urlset("https://example.com/a/"), llms=None,
            pages=[Page(source="a/index.html"), Page(source="b/index.html")],
            served={"/a", "/b"}, host="example.com")
        absent = _by_rule(result, "sitemap.absent_page")
        self.assertEqual([f["subject"] for f in absent], ["b/index.html"])
        self.assertEqual(absent[0]["severity"], "warning")

    def test_an_unreadable_sitemap_does_not_report_every_page_as_absent(self):
        """The interaction worth guarding: no coverage claim from a failed read."""
        result = cf.audit_sources(
            robots=GOOD_ROBOTS, sitemap="<html>nope</html>", llms=None,
            pages=[Page(source=f"p{i}/index.html") for i in range(5)], host="example.com")
        self.assertEqual(_by_rule(result, "sitemap.absent_page"), [])

    def test_a_missing_sitemap_does_not_report_every_page_as_absent_either(self):
        result = cf.audit_sources(
            robots=GOOD_ROBOTS, sitemap=None, llms=None,
            pages=[Page(source="a/index.html")], host="example.com")
        self.assertEqual(_by_rule(result, "sitemap.absent_page"), [])

    def test_the_404_page_and_a_noindex_page_are_exempt(self):
        """Neither belongs in a sitemap, so their absence is not a defect."""
        result = cf.audit_sources(
            robots=GOOD_ROBOTS, sitemap=_urlset("https://example.com/a/"), llms=None,
            pages=[Page(source="a/index.html"), Page(source="404.html", is_404=True),
                   Page(source="secret/index.html", robots="noindex, follow")],
            served={"/a"}, host="example.com")
        self.assertEqual(_by_rule(result, "sitemap.absent_page"), [])

    def test_a_sitemap_url_the_build_does_not_serve_is_critical(self):
        result = cf.audit_sources(
            robots=GOOD_ROBOTS, sitemap=_urlset("https://example.com/a/",
                                                "https://example.com/gone/"),
            llms=None, served={"/a"}, host="example.com")
        findings = _by_rule(result, "sitemap.unsupported_url")
        # The subject is the URL as the sitemap writes it, not the resolved path:
        # that is the string somebody has to find and change, and a sitemap entry
        # has exactly one spelling where a link can have several.
        self.assertEqual([f["subject"] for f in findings],
                         ["https://example.com/gone/"])
        self.assertEqual(findings[0]["severity"], "critical")

    def test_a_sitemap_naming_another_site_is_reported(self):
        result = cf.audit_sources(
            robots=GOOD_ROBOTS, sitemap=_urlset("https://other.example/x/"),
            llms=None, served=set(), host="example.com")
        findings = _by_rule(result, "sitemap.unsupported_url")
        self.assertEqual(len(findings), 1)
        self.assertIn("other.example", findings[0]["message"])

    def test_coverage_is_not_claimed_without_a_build(self):
        """Live mode has no build, so the two build-only rules cannot run.

        The live path passes both as `None`. Passing only one would be a caller
        that has half a build, which does not happen — `run()` takes both from the
        same branch.
        """
        result = cf.audit_sources(
            robots=GOOD_ROBOTS, sitemap=_urlset("https://example.com/a/"), llms=None,
            pages=None, served=None, host="example.com")
        self.assertEqual(_by_rule(result, "sitemap.absent_page"), [])
        self.assertEqual(_by_rule(result, "sitemap.unsupported_url"), [])
        self.assertEqual(result["checked_pages"], 0)


class LlmsTest(unittest.TestCase):
    def test_a_missing_llms_file_is_a_warning(self):
        result = cf.audit_sources(robots=GOOD_ROBOTS, sitemap=None, llms=None)
        self.assertEqual(_by_rule(result, "llms.missing")[0]["severity"], "warning")

    def test_a_file_with_no_links_is_empty(self):
        result = cf.audit_sources(robots=GOOD_ROBOTS, sitemap=None, llms="# Title\n\nProse.\n")
        self.assertEqual(_ids(result).count("llms.empty"), 1)

    def test_a_file_with_links_is_silent(self):
        result = cf.audit_sources(
            robots=GOOD_ROBOTS, sitemap=None,
            llms="# Title\n\n- [About](https://example.com/about/)\n")
        self.assertEqual(_by_rule(result, "llms.missing"), [])
        self.assertEqual(_by_rule(result, "llms.empty"), [])


class ContractTest(unittest.TestCase):
    def test_checks_covers_every_rule_this_capability_can_emit(self):
        emitted = set()
        emitted |= set(_ids(cf.audit_sources(robots=None, sitemap=None, llms=None)))
        emitted |= set(_ids(cf.audit_sources(
            robots="User-agent: *\nDisallow: /\nDisallow: /css/\n",
            sitemap="<html>nope</html>", llms="# Title\n")))
        emitted |= set(_ids(cf.audit_sources(
            robots=GOOD_ROBOTS, sitemap=EMPTY_URLSET, llms=None)))
        emitted |= set(_ids(cf.audit_sources(
            robots=GOOD_ROBOTS, sitemap=_urlset("https://example.com/gone/"), llms=None,
            pages=[Page(source="b/index.html")], served=set(), host="example.com")))
        self.assertEqual(emitted - set(cf.CHECKS), set())
        self.assertEqual(set(cf.CHECKS) - emitted, set())

    def test_the_two_build_only_rules_drop_out_of_a_live_run(self):
        self.assertIn("sitemap.absent_page", cf.STATIC_ONLY)
        self.assertNotIn("sitemap.absent_page", cf.active_checks(live=True))
        self.assertEqual(set(cf.active_checks(live=False)), set(cf.CHECKS))

    def test_the_report_conforms_to_its_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text("<html lang='de'><h1>x</h1></html>", encoding="utf-8")
            (root / "robots.txt").write_text(GOOD_ROBOTS, encoding="utf-8")
            (root / "sitemap.xml").write_text(_urlset("https://example.com/"), encoding="utf-8")
            config = SiteConfig(
                site_url="https://example.com", domain="example.com",
                static_dir=root, workspace_root=root,
            )
            report = cf.run(config)
        self.assertEqual(report["capability"], "crawler-files")
        self.assertEqual(report["crawl_mode"], "static")
        self.assertEqual(
            jsonschema.validate(report, jsonschema.load_schema(SCHEMA)), [])


if __name__ == "__main__":
    unittest.main()
