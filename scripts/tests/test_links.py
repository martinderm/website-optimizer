"""The internal link graph: broken targets, reachability, depth.

Three tests here matter more than the rule-by-rule ones:

- **The graph is static-only and says so.** A crawl sees part of a site, so its
  graph would report the crawl's reach as the site's architecture. `run(live=True)`
  must refuse rather than produce that.
- **One missing target is one finding.** A broken link in a site-wide template is
  one defect on one URL; reporting it once per linking page is the failure D38
  named, and the test counts pages to prove the collapse happens.
- **Reachability is transitive.** A page linked only from another unreachable page
  is unreachable too, which is what "reachable only from the sitemap" means.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wo import jsonschema  # noqa: E402
from wo import urls as url_module  # noqa: E402
from wo.capabilities.links import audit as links  # noqa: E402
from wo.config import SiteConfig  # noqa: E402
from wo.errors import CapabilityError  # noqa: E402
from wo.page import extract_page, extract_page_from_html  # noqa: E402

SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "links-report.schema.json"


def _write_site(root: Path, files: dict[str, str]) -> list:
    for rel, html in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")
    return [
        extract_page(root / rel, source_label=rel)
        for rel in sorted(files) if rel.endswith(".html")
    ]


def _audit(files: dict[str, str], host: str = "example.com") -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        return links.audit_pages(_write_site(root, files), url_module.served(root), host)


def _ids(result):
    return sorted(f["rule_id"] for f in result["findings"])


def _by_rule(result, rule_id):
    return [f for f in result["findings"] if f["rule_id"] == rule_id]


class ExtractionTest(unittest.TestCase):
    def test_a_link_stores_its_target_and_nothing_else(self):
        page = extract_page_from_html(
            '<html><body><a href="/x/">Read more about the studio</a></body></html>'
        )
        self.assertEqual(page.links, [{"href": "/x/"}])
        self.assertNotIn("Read more", repr(page.__dict__))

    def test_an_anchor_without_href_is_not_a_link(self):
        page = extract_page_from_html('<html><body><a name="anchor">x</a></body></html>')
        self.assertEqual(page.links, [])


class TargetResolutionTest(unittest.TestCase):
    def test_external_hosts_are_not_our_business(self):
        self.assertIsNone(links.target_of("https://example.org/x/", "index.html", "example.com"))
        self.assertIsNone(links.target_of("//example.org/x/", "index.html", "example.com"))

    def test_www_and_apex_are_the_same_site(self):
        """D38's trap from the other side: one site, two spellings."""
        self.assertEqual(
            links.target_of("https://www.example.com/x/", "index.html", "example.com"), "/x")
        self.assertEqual(
            links.target_of("https://example.com/x/", "index.html", "www.example.com"), "/x")

    def test_non_page_schemes_and_fragments_resolve_to_nothing(self):
        for href in ("#top", "mailto:a@b.c", "tel:+43", "javascript:void(0)", "", "  "):
            self.assertIsNone(links.target_of(href, "index.html", "example.com"), href)

    def test_a_relative_link_resolves_against_its_own_page(self):
        self.assertEqual(
            links.target_of("../c/", "a/b/index.html", "example.com"), "/a/c")
        self.assertEqual(
            links.target_of("d/", "a/b/index.html", "example.com"), "/a/b/d")

    def test_query_and_fragment_are_not_part_of_the_target(self):
        self.assertEqual(
            links.target_of("/x/?page=2#p", "index.html", "example.com"), "/x")


class MissingTargetTest(unittest.TestCase):
    def test_a_missing_target_is_reported_once_for_every_page_that_links_it(self):
        """The D38 lesson applied to links: one URL, one finding."""
        result = _audit({
            "index.html": '<a href="/gone/">a</a>',
            "about/index.html": '<a href="/gone/">b</a>',
            "texts/index.html": '<a href="/gone/">c</a>',
        })
        findings = _by_rule(result, "link.target_missing")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["subject"], "/gone")
        self.assertEqual(findings[0]["severity"], "critical")
        self.assertEqual(result["broken_targets"], 1)
        self.assertIn("3 page(s)", findings[0]["message"])

    def test_an_existing_target_is_silent(self):
        result = _audit({
            "index.html": '<a href="/about/">a</a>',
            "about/index.html": "b",
        })
        self.assertEqual(_ids(result), [])

    def test_every_spelling_of_one_page_resolves(self):
        """`/about`, `/about/` and `/about/index.html` are one page."""
        result = _audit({
            "index.html": '<a href="/about">1</a><a href="/contact/">2</a>',
            "about/index.html": '<a href="/about/">3</a>',
            "contact/index.html": '<a href="/about/index.html">4</a>',
        })
        self.assertEqual(_by_rule(result, "link.target_missing"), [])
        self.assertEqual(_by_rule(result, "link.unreachable"), [])

    def test_a_link_to_a_built_file_is_not_broken(self):
        result = _audit({
            "index.html": '<a href="/media/doc.pdf">a</a>',
            "media/doc.pdf": "not really a pdf",
        })
        self.assertEqual(_ids(result), [])

    def test_a_target_outside_the_audit_still_counts_as_existing(self):
        """`ignore_path` says do not audit this page, not this page is absent."""
        result = _audit({
            "index.html": '<a href="/admin/">a</a>',
            "admin/index.html": "b",
        })
        self.assertEqual(_ids(result), [])


class ReachabilityTest(unittest.TestCase):
    def test_a_page_nothing_links_to_is_unreachable(self):
        result = _audit({
            "index.html": '<a href="/a/">a</a>',
            "a/index.html": '<a href="/">home</a>',
            "b/index.html": "nothing points here",
        })
        orphans = _by_rule(result, "link.unreachable")
        self.assertEqual([f["subject"] for f in orphans], ["b/index.html"])
        self.assertEqual(orphans[0]["severity"], "warning")

    def test_the_home_page_is_not_its_own_orphan(self):
        result = _audit({"index.html": "<p>home</p>"})
        self.assertEqual(_by_rule(result, "link.unreachable"), [])

    def test_the_404_page_is_exempt(self):
        """Nothing is meant to link to the 404 page; that is what it is for."""
        result = _audit({
            "index.html": "<p>home</p>",
            "404.html": "<p>not found</p>",
        })
        self.assertEqual(_by_rule(result, "link.unreachable"), [])

    def test_reachability_is_transitive(self):
        """Reachable only through an unreachable page is still unreachable."""
        result = _audit({
            "index.html": '<a href="/a/">a</a>',
            "a/index.html": "<p>a</p>",
            "b/index.html": '<a href="/c/">c</a>',
            "c/index.html": "<p>c</p>",
        })
        orphans = sorted(f["subject"] for f in _by_rule(result, "link.unreachable"))
        self.assertEqual(orphans, ["b/index.html", "c/index.html"])


class DepthTest(unittest.TestCase):
    def test_depth_fires_at_the_reference_threshold(self):
        result = _audit({
            "index.html": '<a href="/p1/">1</a>',
            "p1/index.html": '<a href="/p2/">2</a>',
            "p2/index.html": '<a href="/p3/">3</a>',
            "p3/index.html": '<a href="/p4/">4</a>',
            "p4/index.html": "<p>deep</p>",
        })
        deep = _by_rule(result, "link.depth")
        self.assertEqual([f["subject"] for f in deep], ["p4/index.html"])
        self.assertEqual(deep[0]["observed"], links.DEPTH_LIMIT)

    def test_a_shallow_site_is_silent(self):
        result = _audit({
            "index.html": '<a href="/p1/">1</a>',
            "p1/index.html": '<a href="/p2/">2</a>',
            "p2/index.html": "<p>shallow</p>",
        })
        self.assertEqual(_by_rule(result, "link.depth"), [])


class ContractTest(unittest.TestCase):
    def test_every_spelling_a_server_answers_names_its_page(self):
        """The spellings, written out as a table rather than derived from the code.

        `urls.served` decides whether a URL resolves; `urls.page_urls` decides
        which page it resolves to. A key the first accepts and the second misses
        is a URL that exists and leads nowhere. Found by reading the two functions
        next to each other: `/index.html` was served and named no page, while
        every other page had both of its spellings — which is why they now live
        in one module.

        A table, and not a derivation, because the defect was an omission. A test
        that computed the spellings the way the code does would have omitted the
        same one and passed.
        """
        spellings = {
            "index.html": ("/", "/index.html"),
            "a/index.html": ("/a", "/a/index.html"),
            "b.html": ("/b", "/b.html"),
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pages = _write_site(root, {rel: "<p>x</p>" for rel in spellings})
            served = url_module.served(root)
        aliases = links._page_alias_map(pages)
        for source, forms in spellings.items():
            for form in forms:
                self.assertIn(form, served, f"the build does not serve {form}")
                self.assertEqual(aliases.get(form), source, f"{form} must name {source}")

    def test_checks_covers_every_rule_a_page_set_can_emit(self):
        result = _audit({
            "index.html": '<a href="/gone/">broken</a><a href="/p1/">1</a>',
            "orphan/index.html": "<p>nothing links here</p>",
            "p1/index.html": '<a href="/p2/">2</a>',
            "p2/index.html": '<a href="/p3/">3</a>',
            "p3/index.html": '<a href="/p4/">4</a>',
            "p4/index.html": "<p>deep</p>",
        })
        self.assertEqual(set(_ids(result)) - set(links.CHECKS), set())
        self.assertEqual(set(links.CHECKS) - set(_ids(result)), set())

    def test_a_live_run_refuses_instead_of_drawing_a_partial_graph(self):
        config = SiteConfig(
            site_url="https://example.com", domain="example.com",
            static_dir=Path("does-not-matter"), workspace_root=Path("."),
        )
        with self.assertRaises(CapabilityError) as caught:
            links.run(config, live=True)
        self.assertIn("whole build", str(caught.exception))
        self.assertIn("links", str(caught.exception))

    def test_the_report_conforms_to_its_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_site(root, {
                "index.html": '<a href="/gone/">broken</a><a href="/a/">a</a>',
                "a/index.html": "<p>a</p>",
                "b/index.html": "<p>orphan</p>",
            })
            config = SiteConfig(
                site_url="https://example.com", domain="example.com",
                static_dir=root, workspace_root=root,
            )
            report = links.run(config)
        self.assertEqual(report["capability"], "links")
        self.assertEqual(report["crawl_mode"], "static")
        self.assertEqual(
            jsonschema.validate(report, jsonschema.load_schema(SCHEMA)), [])


class RedirectSourcesTest(unittest.TestCase):
    """A link to a redirect source is answered, not broken.

    The build's `_redirects` and `.htaccess` name URLs the server responds to.
    Reporting links to them as missing targets is a false positive with a real
    shape — the visitor arrives. Each format is tested through the file the
    build actually serves, with a control run proving the same links report
    without the files.
    """

    FILES = {
        "index.html": (
            '<html><head></head><body>'
            '<a href="/bio/">bio</a>'
            '<a href="/project/anything/">wildcard</a>'
            '<a href="/project/mudgroup3/">legacy</a>'
            "</body></html>"
        ),
        "_redirects": (
            "/bio/ /about/ 301\n"
            "/project/* /projects/:splat 301\n"
        ),
        ".htaccess": (
            "RewriteEngine On\n"
            "RewriteRule ^(?:portfolio/items|project)/mudgroup3/?$ "
            "/projects/coffee-table/ [R=301,L]\n"
        ),
    }

    def _audit_redirects(self, files, host="example.com"):
        from wo import redirect_rules  # noqa: E402
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pages = _write_site(root, files)
            sources = redirect_rules.sources_from_build(root)
            return links.audit_pages(
                pages, url_module.served(root), host, sources)

    def test_redirect_sources_are_not_missing_targets(self):
        result = self._audit_redirects(dict(self.FILES))
        self.assertEqual(_by_rule(result, "link.target_missing"), [])

    def test_same_links_report_without_the_files(self):
        files = {k: v for k, v in self.FILES.items() if k.endswith(".html")}
        result = self._audit_redirects(files)
        missing = _by_rule(result, "link.target_missing")
        self.assertEqual(
            sorted(f["subject"] for f in missing),
            ["/bio", "/project/anything", "/project/mudgroup3"])


if __name__ == "__main__":
    unittest.main()
