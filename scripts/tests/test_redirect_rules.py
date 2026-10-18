"""Redirect sources as a shared syntax: one home, two callers (D57).

The `redirects` capability probes rules live; `links` accepts their sources as
existing targets. Both read the same file formats, so the parsers live here
rather than in either capability. Three tests matter more than the rest:

- **An alternation is not its first branch.** A RewriteRule naming
  `(?:portfolio/items|project)/…` covers both spellings; matching only the
  cleaned sample path would keep reporting the second branch as broken. The
  rule is matched as a regex, the way the server matches it.
- **A canonical catch-all is not a route.** `^(.*)$ → https://…` answers
  everything and routes nothing; it must never blanket-accept missing targets.
- **Absent files are silence, not an error.** A build without redirect files
  behaves exactly as before — the matcher set is empty, not failed.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wo import redirect_rules as rules  # noqa: E402


def _write(root: Path, files: dict[str, str]) -> Path:
    for rel, body in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    return root


class RedirectsFileTest(unittest.TestCase):
    def test_exact_sources_and_splat_prefixes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _write(Path(tmp), {
                "_redirects": (
                    "# comment\n"
                    "/bio/ /about/ 301\n"
                    "/project/* /projects/:splat 301\n"
                ),
            })
            sources = rules.sources_from_redirects_file(root / "_redirects")
        self.assertEqual(sources["exact"], {"/bio"})
        self.assertEqual(sources["prefix"], {"/project/"})
        self.assertTrue(rules.matches(sources, "/bio"))
        self.assertTrue(rules.matches(sources, "/project/anything/"))
        self.assertTrue(rules.matches(sources, "/project"))
        self.assertFalse(rules.matches(sources, "/other/"))

    def test_missing_file_is_empty_not_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            sources = rules.sources_from_redirects_file(Path(tmp) / "_redirects")
        self.assertFalse(rules.matches(sources, "/bio/"))

    def test_bare_splat_never_blanket_accepts(self):
        """`/*` answers everything and routes nothing. Accepting it would
        silence the entire missing-target rule on maintenance pages and SPA
        fallbacks alike."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _write(Path(tmp), {"_redirects": "/* /maintenance.html 301\n"})
            sources = rules.sources_from_redirects_file(root / "_redirects")
        self.assertFalse(rules.matches(sources, "/no-such-page"))


class HtaccessTest(unittest.TestCase):
    HTACCESS = """\
RewriteEngine On
RewriteRule ^(.*)$ https://example.com/$1 [R=301,L]
RewriteRule ^bio/?$ /about/ [R=301,L]
RewriteRule ^(?:portfolio/items|project)/mudgroup3/?$ /projects/coffee-table/ [R=301,L]
RewriteRule ^old/?$ /new/ [L]
Redirect 301 /statement /works/
"""

    def test_alternation_matches_both_branches(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _write(Path(tmp), {".htaccess": self.HTACCESS})
            sources = rules.sources_from_htaccess(root / ".htaccess")
        self.assertTrue(rules.matches(sources, "/portfolio/items/mudgroup3"))
        self.assertTrue(rules.matches(sources, "/project/mudgroup3"))
        self.assertTrue(rules.matches(sources, "/project/mudgroup3/"))
        self.assertTrue(rules.matches(sources, "/bio"))
        self.assertTrue(rules.matches(sources, "/statement"))

    def test_canonical_catchall_and_plain_rewrites_do_not_accept(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _write(Path(tmp), {".htaccess": self.HTACCESS})
            sources = rules.sources_from_htaccess(root / ".htaccess")
        self.assertFalse(rules.matches(sources, "/definitely-gone/"))
        self.assertFalse(rules.matches(sources, "/old"))

    def test_anchors_survive_so_prefixes_of_a_source_still_report(self):
        """`^bio/?$` answers `/bio`, not `/biodiesel`. The probing regex
        consumes the anchors; acceptance matching keeps them verbatim."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _write(Path(tmp), {".htaccess": self.HTACCESS})
            sources = rules.sources_from_htaccess(root / ".htaccess")
        self.assertFalse(rules.matches(sources, "/biodiesel"))
        self.assertFalse(rules.matches(sources, "/bio-anything"))

    def test_bare_dot_star_never_accepts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _write(Path(tmp), {
                ".htaccess": "RewriteRule .* https://example.com/ [R=301,L]\n",
            })
            sources = rules.sources_from_htaccess(root / ".htaccess")
        self.assertFalse(rules.matches(sources, "/definitely-gone"))

    def test_unanchored_patterns_match_like_the_server(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _write(Path(tmp), {
                ".htaccess": "RewriteRule old /new/ [R=301,L]\n",
            })
            sources = rules.sources_from_htaccess(root / ".htaccess")
        self.assertTrue(rules.matches(sources, "/x/old"))

    def test_missing_file_is_empty_not_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            sources = rules.sources_from_htaccess(Path(tmp) / ".htaccess")
        self.assertFalse(rules.matches(sources, "/bio/"))


class BuildSourcesTest(unittest.TestCase):
    def test_both_files_combine_and_absent_files_silence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _write(Path(tmp), {
                "_redirects": "/bio/ /about/ 301\n",
                ".htaccess": "RewriteRule ^x/?$ /y/ [R=301,L]\n",
            })
            both = rules.sources_from_build(root)
            neither = rules.sources_from_build(root / "empty")
        self.assertTrue(rules.matches(both, "/bio"))
        self.assertTrue(rules.matches(both, "/x"))
        self.assertFalse(rules.matches(neither, "/bio"))
        self.assertFalse(rules.matches(neither, "/x"))


if __name__ == "__main__":
    unittest.main()
