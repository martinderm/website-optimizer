"""Images and structured-data capabilities.

Two boundary tests matter as much as the rule tests: `alt` belongs to `on-page`,
and `schema` checks structure rather than the schema.org vocabulary.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wo.capabilities.images import audit as images  # noqa: E402
from wo.capabilities.schema import audit as schema  # noqa: E402
from wo.config import SiteConfig  # noqa: E402
from wo.page import extract_page  # noqa: E402


def _page(html: str):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "p.html"
        path.write_text(html, encoding="utf-8")
        return extract_page(path, source_label="p.html")


def _ids(findings):
    return sorted(f["rule_id"] for f in findings)


class ImagesTest(unittest.TestCase):
    def test_img_without_src_is_reported_once_not_three_times(self):
        """A JavaScript placeholder is not a delivery fault.

        Regression: an <img> with no src was counted as a critical missing
        dimension and a missing srcset as well, which made 140 of 469 critical
        findings on the reference site describe elements that download nothing.
        """
        page = _page('<html lang="de"><img class="lightbox" data-image alt=""></html>')
        findings = images.audit_page(page)
        image_rules = [f["rule_id"] for f in findings if f["rule_id"].startswith("image.src")]
        self.assertEqual(image_rules, ["image.src_missing"])
        missing = next(f for f in findings if f["rule_id"] == "image.src_missing")
        self.assertEqual(missing["severity"], "warning")
        self.assertIn("no src at all", missing["message"])

    def test_empty_src_is_distinguished_from_absent_src(self):
        """A bare `src` attribute parses as src="", which fetches the page."""
        page = _page('<html lang="de"><img src alt=""></html>')
        findings = [f for f in images.audit_page(page) if f["rule_id"] == "image.src_missing"]
        self.assertEqual(len(findings), 1)
        self.assertIn("empty src", findings[0]["message"])
        self.assertIn("requests the page URL", findings[0]["message"])

    def test_missing_dimensions_is_critical(self):
        page = _page('<html lang="de"><img src="/a.jpg"></html>')
        findings = [f for f in images.audit_page(page) if f["rule_id"] == "image.dimensions_missing"]
        self.assertEqual(findings[0]["severity"], "critical")
        self.assertEqual(sorted(findings[0]["observed"]), ["height", "width"])

    def test_declared_dimensions_silence_the_rule(self):
        page = _page('<html lang="de"><img src="/a.webp" width="800" height="600" '
                     'srcset="/a.webp 800w" sizes="100vw"></html>')
        self.assertNotIn("image.dimensions_missing", _ids(images.audit_page(page)))

    def test_non_numeric_dimensions_do_not_count(self):
        page = _page('<html lang="de"><img src="/a.webp" width="100%" height="auto"></html>')
        self.assertIn("image.dimensions_missing", _ids(images.audit_page(page)))

    def test_srcset_without_sizes_is_flagged(self):
        page = _page('<html lang="de"><img src="/a.webp" width="8" height="6" '
                     'srcset="/a.webp 800w, /b.webp 1400w"></html>')
        self.assertIn("image.sizes_missing", _ids(images.audit_page(page)))

    def test_legacy_format_is_flagged_but_a_candidate_may_be_modern(self):
        legacy = _page('<html lang="de"><img src="/a.jpg" width="8" height="6"></html>')
        self.assertIn("image.format_legacy", _ids(images.audit_page(legacy)))
        mixed = _page('<html lang="de"><img src="/a.jpg" width="8" height="6" '
                      'srcset="/a.jpg 800w, /a.webp 1400w" sizes="100vw"></html>')
        self.assertNotIn("image.format_legacy", _ids(images.audit_page(mixed)))

    def test_alt_is_not_checked_here(self):
        """Boundary: `alt` belongs to on-page. Duplicating it would be two truths."""
        page = _page('<html lang="de"><img src="/a.webp" width="8" height="6" '
                     'srcset="/a.webp 8w" sizes="100vw"></html>')
        self.assertNotIn("img.alt.missing", _ids(images.audit_page(page)))
        self.assertNotIn("image.alt_missing", _ids(images.audit_page(page)))

    def test_declared_but_absent_icon_is_critical(self):
        page = _page('<html lang="de"><link rel="icon" href="/favicon.ico"></html>')
        with tempfile.TemporaryDirectory() as root:
            findings = [f for f in images.audit_page(page, Path(root))
                        if f["rule_id"] == "icon.file_missing"]
        self.assertEqual(findings[0]["severity"], "critical")

    def test_present_icon_is_silent(self):
        page = _page('<html lang="de"><link rel="icon" href="/favicon.ico"></html>')
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / "favicon.ico").write_bytes(b"x")
            self.assertNotIn("icon.file_missing", _ids(images.audit_page(page, Path(root))))

    def test_relative_og_image_is_flagged(self):
        page = _page('<html lang="de"><meta property="og:image" content="/og.jpg"></html>')
        self.assertIn("image.og_relative", _ids(images.audit_page(page)))

    def test_checks_declares_every_emitted_rule(self):
        """Two fixtures between them trip every rule, so neither set can drift.

        One fixture cannot do it: declaring no icon and declaring an absent one
        are mutually exclusive states, and `CHECKS` has to cover both.
        """
        no_icons = _page(
            '<html lang="de"><meta property="og:image" content="/og.jpg">'
            '<img src="/a.jpg">'
            '<img class="lightbox" data-image alt="">'
            '<img src="/b.jpg" width="8" height="6" srcset="/b.jpg 800w"></html>'
        )
        with_icons = _page('<html lang="de"><link rel="icon" href="/favicon.ico"></html>')
        with tempfile.TemporaryDirectory() as root:
            emitted = set(_ids(images.audit_page(no_icons, Path(root))))
            emitted |= set(_ids(images.audit_page(with_icons, Path(root))))
        self.assertEqual(emitted - set(images.CHECKS), set())
        self.assertEqual(set(images.CHECKS) - emitted, set())


class SchemaTest(unittest.TestCase):
    def _audit(self, html: str):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "p.html"
            path.write_text(html, encoding="utf-8")
            return schema.audit_page(path, "p.html")

    def test_unquoted_type_attribute_is_still_found(self):
        """Regression: minified generator output drops attribute quotes.

        Requiring quotes made a fully marked-up site report as having no
        structured data at all — a confident, wrong "clean".
        """
        minified = ('<script type=application/ld+json>{"@context":"https://schema.org",'
                    '"@type":"WebSite","name":"X","url":"https://x"}</script>')
        findings, types, _, blocks = self._audit(minified)
        self.assertEqual(findings, [])
        self.assertEqual(types, ["WebSite"])
        self.assertEqual(blocks, 1)

    def test_single_quoted_type_attribute_is_found(self):
        single = "<script type='application/ld+json'>{\"@context\":\"https://schema.org\","
        single += '"@type":"Person","name":"X"}</script>'
        _, types, _, _ = self._audit(single)
        self.assertEqual(types, ["Person"])

    def test_other_script_types_are_ignored(self):
        _, types, _, blocks = self._audit(
            '<script type="text/javascript">var a=1;</script>'
            '<script src="/x.js"></script>')
        self.assertEqual((types, blocks), ([], 0))

    def test_closing_tag_without_space_is_handled(self):
        unspaced = '<script type=application/ld+json>{"@context":"https://schema.org",'
        unspaced += '"@type":"Person","name":"X"}</script>'
        _, types, _, _ = self._audit(unspaced)
        self.assertEqual(types, ["Person"])

    def test_missing_block_is_a_warning(self):
        findings, types, ids, blocks = self._audit("<html><body>nothing</body></html>")
        self.assertEqual(_ids(findings), ["schema.none"])
        self.assertEqual(types, [])

    def test_broken_json_is_critical_and_reports_the_position(self):
        findings, _, _, _ = self._audit(
            '<script type="application/ld+json">{"@type":"WebSite",}</script>')
        self.assertIn("schema.block_invalid_json", _ids(findings))
        self.assertEqual(findings[0]["severity"], "critical")

    def test_empty_block_is_critical(self):
        findings, _, _, _ = self._audit('<script type="application/ld+json">   </script>')
        self.assertIn("schema.block_empty", _ids(findings))

    def test_graph_members_are_found_and_required_fields_checked(self):
        block = ('<script type="application/ld+json">{"@context":"https://schema.org",'
                 '"@graph":[{"@type":"WebSite","name":"X","url":"https://x"},'
                 '{"@type":"Organization","@id":"https://x/#o"}]}</script>')
        findings, types, ids, blocks = self._audit(block)
        self.assertIn("schema.required_field_missing", _ids(findings))
        self.assertEqual(sorted(set(types)), ["Organization", "WebSite"])
        self.assertEqual([i for i, _, _ in ids], ["https://x/#o"])
        self.assertEqual(blocks, 1)

    def test_complete_nodes_are_silent(self):
        block = ('<script type="application/ld+json">{"@context":"https://schema.org",'
                 '"@graph":[{"@type":"WebSite","name":"X","url":"https://x"},'
                 '{"@type":"Organization","name":"X"}]}</script>')
        findings, _, _, _ = self._audit(block)
        self.assertEqual(findings, [])

    def test_missing_required_field_names_the_fields(self):
        block = ('<script type="application/ld+json">{"@context":"https://schema.org",'
                 '"@type":"Article","headline":"H"}</script>')
        findings, _, _, _ = self._audit(block)
        missing = findings[0]["observed"]
        self.assertEqual(sorted(missing), ["author", "datePublished"])

    def test_vocabulary_is_referenced_not_fetched(self):
        """The approved scope: structure locally, authority by reference."""
        self.assertEqual(schema.VOCABULARY_REFERENCE, "https://schema.org/docs/full.html")
        self.assertIn("validator.schema.org", schema.VALIDATOR_REFERENCE)

    def test_identical_ids_across_pages_are_correct_not_flagged(self):
        """A site-wide @graph repeats the same @id in every head. That is the point."""
        payload = '{"@type":"WebSite","name":"X"}'
        self.assertEqual(
            schema._duplicate_identifiers([
                ("https://x/#website", "a.html", payload),
                ("https://x/#website", "b.html", payload),
                ("https://x/#website", "c.html", payload),
            ]),
            [],
        )

    def test_conflicting_ids_are_critical(self):
        findings = schema._duplicate_identifiers([
            ("https://x/#website", "a.html", '{"@type":"WebSite","name":"X"}'),
            ("https://x/#website", "b.html", '{"@type":"WebSite","name":"Other"}'),
        ])
        self.assertEqual(_ids(findings), ["schema.identifier_conflicting"])
        self.assertEqual(findings[0]["severity"], "critical")

    def test_a_single_definition_is_not_flagged(self):
        self.assertEqual(
            schema._duplicate_identifiers([("https://x/#website", "a.html", "{}")]), [])

    def test_identity_type_is_required_site_wide(self):
        self.assertEqual(schema._audit_site(["WebSite"]), [])
        self.assertEqual(_ids(schema._audit_site(["Article", "FAQPage"])),
                         ["schema.identity_missing"])
        # No types at all means no markup at all, which each page already reports.
        self.assertEqual(schema._audit_site([]), [])


if __name__ == "__main__":
    unittest.main()