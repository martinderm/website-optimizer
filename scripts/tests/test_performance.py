"""Static performance signals: weight, render-blocking, fonts, preloads, third parties.

Five tests here matter more than the rule-by-rule ones:

- **Weight is measured, not estimated.** Budgets compare bytes on disk against
  the budgets `references/performance.md` already names. A fixture file is
  padded to an exact size so the assertion is arithmetic, not vibes.
- **One missing target is one finding.** A preload to a missing file in a
  site-wide template is one defect on one URL (D52), naming the pages that
  declare it — not one finding per page.
- **One origin is one finding.** A third-party host on 190 pages is one
  inventory line with a page count, not 190 warnings.
- **The capability is build-only and says so.** File sizes exist only in a
  build; `run(live=True)` must refuse rather than weigh a crawl.
- **Missing files are someone else's finding.** A declared path the build does
  not contain is reported by `links`/`images`; no performance rule fires on it,
  so weight can never go negative and a 404 never reads as lightweight.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wo import jsonschema  # noqa: E402
from wo.capabilities.performance import audit as perf  # noqa: E402
from wo.config import SiteConfig  # noqa: E402
from wo.errors import CapabilityError  # noqa: E402
from wo.page import extract_page, extract_page_from_html  # noqa: E402

SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "performance-report.schema.json"


def _write_site(root: Path, files: dict[str, str | bytes]) -> list:
    for rel, body in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(body, bytes):
            path.write_bytes(body)
        else:
            path.write_text(body, encoding="utf-8")
    return [
        extract_page(root / rel, source_label=rel)
        for rel in sorted(files) if rel.endswith(".html")
    ]


def _audit(files: dict[str, str | bytes], host: str = "example.com") -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        return perf.audit_pages(_write_site(root, files), root, host)


def _ids(result):
    return sorted(f["rule_id"] for f in result["findings"])


def _by_rule(result, rule_id):
    return [f for f in result["findings"] if f["rule_id"] == rule_id]


def _pad(size: int) -> bytes:
    """A file of exactly `size` bytes. Weight assertions need arithmetic."""
    return b"x" * size


class ExtractionTest(unittest.TestCase):
    def test_a_head_script_keeps_src_and_loading_attributes(self):
        page = extract_page_from_html(
            '<html><head><script src="/js/a.js"></script></head><body></body></html>'
        )
        self.assertEqual(page.scripts, [{
            "src": "/js/a.js", "defer": False, "async": False,
            "type": "", "in_head": True,
        }])

    def test_a_deferred_body_script_knows_where_it_stood(self):
        page = extract_page_from_html(
            '<html><head></head><body><script src="/js/b.js" defer></script></body></html>'
        )
        self.assertEqual(page.scripts, [{
            "src": "/js/b.js", "defer": True, "async": False,
            "type": "", "in_head": False,
        }])

    def test_stylesheets_preloads_and_iframes_are_addresses_not_content(self):
        page = extract_page_from_html(
            '<html><head>'
            '<link rel="stylesheet" href="/css/site.css">'
            '<link rel="preload" href="/fonts/a.woff2" as="font">'
            '</head><body><iframe src="https://player.example/video/1"></iframe>'
            '<script>var bodyText = "Fließtext";</script>'
            "</body></html>"
        )
        self.assertEqual(page.stylesheets, [{"href": "/css/site.css"}])
        self.assertEqual(
            page.preloads, [{"href": "/fonts/a.woff2", "as": "font"}])
        self.assertEqual(page.iframes, [{"src": "https://player.example/video/1"}])
        self.assertEqual(page.scripts, [])
        self.assertNotIn("Fließtext", repr(page.__dict__))


class BudgetTest(unittest.TestCase):
    def test_stylesheet_weight_over_budget_is_one_finding_on_the_file(self):
        result = _audit({
            "index.html": '<html><head><link rel="stylesheet" href="/css/big.css"></head>'
                          "<body><p>x</p></body></html>",
            "css/big.css": _pad(153600),
        })
        findings = _by_rule(result, "perf.budget_exceeded")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["subject"], "/css/big.css")
        self.assertEqual(findings[0]["observed"], 153600)
        self.assertIn("1 page(s)", findings[0]["message"])

    def test_weight_under_every_budget_is_silence(self):
        result = _audit({
            "index.html": '<html><head><link rel="stylesheet" href="/css/ok.css"></head>'
                          "<body><p>x</p></body></html>",
            "css/ok.css": _pad(1024),
        })
        self.assertEqual(_by_rule(result, "perf.budget_exceeded"), [])

    def test_script_weight_counts_against_the_script_budget(self):
        result = _audit({
            "index.html": '<html><head><script src="/js/big.js" defer></script></head>'
                          "<body><p>x</p></body></html>",
            "js/big.js": _pad(230400),
        })
        findings = _by_rule(result, "perf.budget_exceeded")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["subject"], "/js/big.js")

    def test_the_largest_image_counts_against_the_hero_budget(self):
        result = _audit({
            "index.html": "<html><body>"
                          '<img src="/img/small.jpg"><img src="/img/huge.jpg">'
                          "</body></html>",
            "img/small.jpg": _pad(1024),
            "img/huge.jpg": _pad(230400),
        })
        findings = _by_rule(result, "perf.budget_exceeded")
        self.assertEqual(len(findings), 1)
        self.assertIn("huge.jpg", findings[0]["message"])

    def test_a_font_file_over_budget_is_keyed_on_the_file(self):
        css = ("@font-face{font-family:A;src:url('/fonts/heavy.woff2');}"
               "@font-face{font-family:B;font-display:swap;src:url('/fonts/light.woff2');}")
        result = _audit({
            "index.html": '<html><head><link rel="stylesheet" href="/css/f.css"></head>'
                          "<body><p>x</p></body></html>",
            "css/f.css": css,
            "fonts/heavy.woff2": _pad(153600),
            "fonts/light.woff2": _pad(1024),
        })
        findings = _by_rule(result, "perf.budget_exceeded")
        self.assertEqual(len(findings), 1)
        self.assertIn("heavy.woff2", findings[0]["message"])

    def test_a_declared_file_missing_from_the_build_weighs_nothing(self):
        """A 404 is `links`' finding. Weight skips it rather than going negative."""
        result = _audit({
            "index.html": '<html><head><link rel="stylesheet" href="/css/gone.css"></head>'
                          "<body><p>x</p></body></html>",
        })
        self.assertEqual(_by_rule(result, "perf.budget_exceeded"), [])

    def test_the_404_page_is_not_a_view_and_is_not_weighed(self):
        result = _audit({
            "404.html": '<html><head><link rel="stylesheet" href="/css/big.css"></head>'
                        "<body><p>gone</p></body></html>",
            "css/big.css": _pad(153600),
        })
        self.assertEqual(_by_rule(result, "perf.budget_exceeded"), [])

    def test_a_shared_heavy_stylesheet_is_one_finding_naming_both_pages(self):
        """D52: one file in a site-wide template is one defect, not one per page."""
        result = _audit({
            "index.html": '<html><head><link rel="stylesheet" href="/css/big.css"></head>'
                          "<body><p>x</p></body></html>",
            "sub/index.html": '<html><head><link rel="stylesheet" href="/css/big.css"></head>'
                              "<body><p>y</p></body></html>",
            "css/big.css": _pad(153600),
        })
        findings = _by_rule(result, "perf.budget_exceeded")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["subject"], "/css/big.css")
        self.assertIn("2 page(s)", findings[0]["message"])

    def test_light_files_adding_up_over_budget_report_the_composition(self):
        """No single file over budget, but the page total is: the composition
        is the finding, once, on the page — and never stacked on a file finding."""
        result = _audit({
            "index.html": "<html><head>"
                          '<link rel="stylesheet" href="/css/a.css">'
                          '<link rel="stylesheet" href="/css/b.css"></head>'
                          "<body><p>x</p></body></html>",
            "css/a.css": _pad(61440),
            "css/b.css": _pad(61440),
        })
        findings = _by_rule(result, "perf.budget_exceeded")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["subject"], "index.html")
        self.assertIn("composition", findings[0]["message"])

    def test_a_relative_reference_from_a_top_level_page_resolves(self):
        """Regression: the page directory of `index.html` is `/`, and joining
        it by concatenation produced a `//`-key that `served` never holds."""
        result = _audit({
            "index.html": '<html><head><link rel="stylesheet" href="css/big.css"></head>'
                          "<body><p>x</p></body></html>",
            "css/big.css": _pad(153600),
        })
        findings = _by_rule(result, "perf.budget_exceeded")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["subject"], "/css/big.css")


class BlockingTest(unittest.TestCase):
    def test_a_plain_head_script_blocks(self):
        result = _audit({
            "index.html": '<html><head><script src="/js/a.js"></script></head>'
                          "<body><p>x</p></body></html>",
            "js/a.js": "var a = 1;",
        })
        findings = _by_rule(result, "perf.render_blocking_script")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["subject"], "/js/a.js")

    def test_defer_async_module_and_body_scripts_do_not_block(self):
        result = _audit({
            "index.html": "<html><head>"
                          '<script src="/js/d.js" defer></script>'
                          '<script src="/js/a.js" async></script>'
                          '<script type="module" src="/js/m.js"></script>'
                          "</head><body>"
                          '<script src="/js/b.js"></script>'
                          "</body></html>",
            "js/d.js": "1", "js/a.js": "1", "js/m.js": "1", "js/b.js": "1",
        })
        self.assertEqual(_by_rule(result, "perf.render_blocking_script"), [])

    def test_one_blocking_src_is_one_finding_naming_both_pages(self):
        result = _audit({
            "index.html": '<html><head><script src="/js/a.js"></script></head>'
                          "<body><p>x</p></body></html>",
            "sub/index.html": '<html><head><script src="/js/a.js"></script></head>'
                              "<body><p>y</p></body></html>",
            "js/a.js": "var a = 1;",
        })
        findings = _by_rule(result, "perf.render_blocking_script")
        self.assertEqual(len(findings), 1)
        self.assertIn("2 page(s)", findings[0]["message"])

    def test_spelling_variants_of_one_file_are_one_finding(self):
        result = _audit({
            "index.html": '<html><head><script src="/js/a.js"></script></head>'
                          "<body><p>x</p></body></html>",
            "sub/index.html": "<html><head>"
                              '<script src="https://example.com/js/a.js"></script>'
                              "</head><body><p>y</p></body></html>",
            "js/a.js": "var a = 1;",
        })
        findings = _by_rule(result, "perf.render_blocking_script")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["subject"], "/js/a.js")
        self.assertIn("2 page(s)", findings[0]["message"])

    def test_defer_false_still_defers(self):
        """Boolean attributes are true by presence: browsers defer
        `defer="false"`. Firing on it would contradict the platform to honor
        an author's probable typo."""
        result = _audit({
            "index.html": '<html><head><script src="/js/a.js" defer="false"></script></head>'
                          "<body><p>x</p></body></html>",
            "js/a.js": "var a = 1;",
        })
        self.assertEqual(_by_rule(result, "perf.render_blocking_script"), [])


class FontDisplayTest(unittest.TestCase):
    def test_a_face_without_font_display_is_reported_per_file(self):
        result = _audit({
            "index.html": '<html><head><link rel="stylesheet" href="/css/f.css"></head>'
                          "<body><p>x</p></body></html>",
            "css/f.css": "@font-face{font-family:A;src:url(a.woff2);}",
        })
        findings = _by_rule(result, "perf.font_display_missing")
        self.assertEqual(len(findings), 1)
        self.assertIn("css/f.css", findings[0]["subject"])

    def test_a_face_with_swap_is_silence(self):
        result = _audit({
            "index.html": '<html><head><link rel="stylesheet" href="/css/f.css"></head>'
                          "<body><p>x</p></body></html>",
            "css/f.css": "@font-face{font-family:A;font-display:swap;src:url(a.woff2);}",
        })
        self.assertEqual(_by_rule(result, "perf.font_display_missing"), [])

    def test_unreferenced_css_is_not_read(self):
        """A stylesheet no page loads is not delivered, so it cannot slow one."""
        result = _audit({
            "index.html": "<html><head></head><body><p>x</p></body></html>",
            "css/dead.css": "@font-face{font-family:A;src:url(a.woff2);}",
        })
        self.assertEqual(_by_rule(result, "perf.font_display_missing"), [])

    def test_a_commented_declaration_is_no_declaration(self):
        result = _audit({
            "index.html": '<html><head><link rel="stylesheet" href="/css/f.css"></head>'
                          "<body><p>x</p></body></html>",
            "css/f.css": "@font-face{font-family:A;/* font-display: swap; */src:url(a.woff2);}",
        })
        findings = _by_rule(result, "perf.font_display_missing")
        self.assertEqual(len(findings), 1)


class PreloadTest(unittest.TestCase):
    def test_a_preload_to_nothing_is_critical_and_keyed_on_the_target(self):
        result = _audit({
            "index.html": "<html><head>"
                          '<link rel="preload" href="/fonts/gone.woff2" as="font">'
                          "</head><body><p>x</p></body></html>",
            "sub/index.html": "<html><head>"
                              '<link rel="preload" href="/fonts/gone.woff2" as="font">'
                              "</head><body><p>y</p></body></html>",
        })
        findings = _by_rule(result, "perf.preload_target_missing")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"], "critical")
        self.assertEqual(findings[0]["subject"], "/fonts/gone.woff2")
        self.assertIn("2 page(s)", findings[0]["message"])

    def test_a_preload_to_a_file_is_silence(self):
        result = _audit({
            "index.html": "<html><head>"
                          '<link rel="preload" href="/fonts/a.woff2" as="font">'
                          "</head><body><p>x</p></body></html>",
            "fonts/a.woff2": _pad(100),
        })
        self.assertEqual(_by_rule(result, "perf.preload_target_missing"), [])

    def test_an_external_preload_is_not_a_build_question(self):
        result = _audit({
            "index.html": "<html><head>"
                          '<link rel="preload" href="https://cdn.example/f.woff2" as="font">'
                          "</head><body><p>x</p></body></html>",
        })
        self.assertEqual(_by_rule(result, "perf.preload_target_missing"), [])

    def test_a_first_party_absolute_preload_to_nothing_is_critical(self):
        """The most explicit spelling of a missing file must not pass
        silently just because it carries a scheme and host."""
        result = _audit({
            "index.html": "<html><head>"
                          '<link rel="preload" href="https://example.com/fonts/gone.woff2" as="font">'
                          "</head><body><p>x</p></body></html>",
        })
        findings = _by_rule(result, "perf.preload_target_missing")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"], "critical")
        self.assertEqual(findings[0]["subject"], "/fonts/gone.woff2")


class ThirdPartyTest(unittest.TestCase):
    def test_one_foreign_origin_is_one_finding_with_a_page_count(self):
        result = _audit({
            "index.html": "<html><head>"
                          '<script src="https://cdn.example/lib.js" defer></script>'
                          "</head><body><p>x</p></body></html>",
            "sub/index.html": "<html><head></head><body>"
                              '<img src="https://cdn.example/i.png">'
                              "</body></html>",
        })
        findings = _by_rule(result, "perf.third_party_origin")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["subject"], "https://cdn.example")
        self.assertIn("2 page(s)", findings[0]["message"])

    def test_first_party_hosts_are_not_third_parties(self):
        """Same host with or without `www` is one site (D38's spelling rule).

        A subdomain is reported: the markup cannot show whether
        `static.example.com` is the site's own CDN or a CNAME to someone
        else's tracker, so attribution stays human and the rule only names.
        """
        result = _audit({
            "index.html": "<html><head>"
                          '<script src="https://example.com/js/a.js" defer></script>'
                          '<script src="https://www.example.com/js/w.js" defer></script>'
                          '<script src="https://static.example.com/js/b.js" defer></script>'
                          "</head><body><p>x</p></body></html>",
        })
        findings = _by_rule(result, "perf.third_party_origin")
        self.assertEqual([f["subject"] for f in findings],
                         ["https://static.example.com"])

    def test_data_urls_are_not_origins(self):
        result = _audit({
            "index.html": "<html><head></head><body>"
                          '<img src="data:image/gif;base64,R0lGODlhAQABAAAAACw=">'
                          "</body></html>",
        })
        self.assertEqual(_by_rule(result, "perf.third_party_origin"), [])


class ContractTest(unittest.TestCase):
    def test_checks_covers_every_rule_a_page_set_can_emit(self):
        result = _audit({
            "index.html": "<html><head>"
                          '<link rel="stylesheet" href="/css/big.css">'
                          '<script src="/js/a.js"></script>'
                          '<link rel="preload" href="/fonts/gone.woff2" as="font">'
                          '<script src="https://cdn.example/lib.js" defer></script>'
                          "</head><body><p>x</p></body></html>",
            "css/big.css": "@font-face{font-family:A;src:url('/fonts/h.woff2');}"
                            + ("/*pad*/" * 30000),
            "js/a.js": "var a = 1;",
            "fonts/h.woff2": _pad(100),
        })
        self.assertEqual(set(_ids(result)) - set(perf.CHECKS), set())
        self.assertEqual(set(perf.CHECKS) - set(_ids(result)), set())

    def test_a_live_run_refuses_instead_of_weighing_a_crawl(self):
        config = SiteConfig(
            site_url="https://example.com", domain="example.com",
            static_dir=Path("does-not-matter"), workspace_root=Path("."),
        )
        with self.assertRaises(CapabilityError) as caught:
            perf.run(config, live=True)
        self.assertIn("whole build", str(caught.exception))
        self.assertIn("performance", str(caught.exception))

    def test_the_report_conforms_to_its_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pages = _write_site(root, {
                "index.html": "<html><head></head><body><p>x</p></body></html>",
            })
            result = perf.audit_pages(pages, root, "example.com")
            report = perf.to_report(
                result, "example.com", "https://example.com",
                {"kind": "static_dir", "path": "public"})
            self.assertEqual(jsonschema.validate(report, json.loads(SCHEMA.read_text())), [])


if __name__ == "__main__":
    unittest.main()
