"""Fact extraction: fields in, page prose out."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wo.page import Page, extract_page, extract_page_from_html  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "site" / "public"


class ExtractionTest(unittest.TestCase):
    def setUp(self):
        self.index = extract_page(FIXTURES / "index.html", "index.html")
        self.clean = extract_page(FIXTURES / "ueber-uns" / "index.html", "ueber-uns/index.html")
        self.notfound = extract_page(FIXTURES / "404.html", "404.html")

    def test_head_and_language(self):
        self.assertEqual(self.index.lang, "de")
        self.assertIn("Kinnarpsessel", self.index.title)
        self.assertTrue(self.index.title_found)
        self.assertEqual(self.index.canonical, "https://example.com/")
        self.assertGreater(self.index.description_length, 30)

    def test_open_graph_and_twitter_are_extracted_separately(self):
        self.assertEqual(self.index.og.get("og:image"), "/images/og-default.jpg")
        self.assertIsNone(self.index.og.get("og:description"))
        self.assertNotIn("twitter:card", self.index.twitter)
        self.assertEqual(self.clean.twitter.get("twitter:card"), "summary_large_image")

    def test_json_ld_types_include_graph_members(self):
        self.assertIn("WebSite", self.index.schemas)
        self.assertIn("Organization", self.index.schemas)

    def test_structural_counts(self):
        self.assertEqual(self.index.h1_count, 1)
        self.assertTrue(self.index.has_main)
        self.assertTrue(self.index.has_skip_link)
        self.assertEqual(self.index.images_total, 2)
        self.assertEqual(self.index.images_missing_alt, 1)

    def test_404_is_flagged_for_relaxed_rules(self):
        self.assertTrue(self.notfound.is_404)

    def test_page_retains_no_body_prose(self):
        """The scope rule of D13, asserted rather than assumed."""
        blob = repr(self.index.__dict__)
        self.assertNotIn("Fließtext", blob)
        self.assertNotIn("absichtlich lang", blob)

    def test_extractor_keeps_only_two_sinks(self):
        parser_fields = set(Page().__dict__)
        self.assertIn("title", parser_fields)
        self.assertNotIn("body", parser_fields)
        self.assertNotIn("text", parser_fields)

    def test_a_link_keeps_its_target_and_drops_its_words(self):
        """The `links` capability needs the graph, not the prose.

        Both halves of `<a href="…">…</a>` are one element, and the decision is
        deliberately asymmetric: the target is a field, the words are authored
        prose and D13 has no place for them. The cost is named rather than
        hidden — anchor-text quality is a rule this tool cannot measure.
        """
        page = extract_page_from_html(
            '<html><body><a href="/werke/">Werke ansehen</a>'
            '<a name="top">no target here</a></body></html>'
        )
        self.assertEqual(page.links, [{"href": "/werke/"}])
        self.assertNotIn("Werke ansehen", repr(page.__dict__))


if __name__ == "__main__":
    unittest.main()