"""Live crawl: settings, URL resolution, and the guard that refuses a wall.

No network and no browser here. `BrowserSession` takes a runner callable, so a
crawl can be driven from a list of strings; the tests use that to check the
decisions rather than the browser.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wo import crawl  # noqa: E402
from wo.config import SiteConfig, crawl_settings  # noqa: E402
from wo.errors import ConfigError  # noqa: E402


def _fake_runner(pages: dict[str, str], log: list | None = None):
    """A stand-in for the CLI. `goto` moves a cursor; `eval` answers from it."""
    state = {"at": None}

    def run(session, args, timeout, command=None):
        if log is not None:
            log.append((session, args))
        if not args:
            return _proc(0, "")
        verb = args[0]
        if verb == "open":
            return _proc(0, "opened")
        if verb == "close":
            return _proc(0, "closed")
        if verb == "goto":
            state["at"] = args[1]
            return _proc(0, "")
        if verb == "eval":
            import json
            return _proc(0, json.dumps(pages.get(state["at"], "")))
        return _proc(1, f"unknown verb {verb}")

    return run


def _proc(code: int, out: str, err: str = ""):
    class R:
        returncode = code
        stdout = out
        stderr = err
    return R()


def _config(tmp: str, **crawl_kwargs) -> SiteConfig:
    return SiteConfig(
        site_url="https://example.com",
        domain="example.com",
        static_dir=Path(tmp) / "public",
        workspace_root=Path(tmp),
        crawl=crawl_settings({"crawl": crawl_kwargs}),
    )


class WallDetectionTest(unittest.TestCase):
    """The consent-wall guard. Its whole value is that it refuses to guess."""

    def test_identical_markup_across_many_urls_is_a_wall(self):
        html = ["<html><body><div id=consent>Accept</div></body></html>"] * 6
        suspected, reason = crawl._looks_like_a_wall(html)
        self.assertTrue(suspected)
        self.assertIn("identical", reason)
        self.assertIn("consent", reason)

    def test_distinct_pages_are_not_a_wall(self):
        html = [f"<html><body><h1>Page {i}</h1></body></html>" for i in range(6)]
        suspected, _ = crawl._looks_like_a_wall(html)
        self.assertFalse(suspected)

    def test_two_pages_are_never_enough_evidence(self):
        """With nothing to compare there is no evidence, and no refusal either."""
        same = ["<html><body>same</body></html>"] * 2
        suspected, _ = crawl._looks_like_a_wall(same)
        self.assertFalse(suspected)

    def test_one_repeated_page_among_many_does_not_trip_it(self):
        """A single duplicate is ordinary; a wall repeats on every page."""
        html = ["<html>a</html>", "<html>b</html>", "<html>c</html>", "<html>b</html>"]
        suspected, _ = crawl._looks_like_a_wall(html)
        self.assertFalse(suspected)

    def test_javascript_shell_is_caught_without_a_consent_marker(self):
        html = ["<html><body><div id=root></div><script>app()</script></body></html>"] * 5
        suspected, reason = crawl._looks_like_a_wall(html)
        self.assertTrue(suspected)
        self.assertIn("JavaScript", reason)


import urllib.request

# Saved once, at import. Saving it inside a test would save whichever patch was
# already in place, and one test would leak into the next.
_REAL_URLOPEN = urllib.request.urlopen


def _restore_urlopen():
    urllib.request.urlopen = _REAL_URLOPEN


class SitemapTest(unittest.TestCase):
    """A sitemap is not always a list of pages.

    Regression: WordPress Core and Yoast both emit a *sitemap index* - a list of
    further sitemap files. The original reader took every <loc> as a page, so on
    a WordPress site the crawl would have visited the XML files themselves and
    reported on documents that are not documents.
    """

    INDEX = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<sitemap><loc>https://example.com/post-sitemap.xml</loc></sitemap>
<sitemap><loc>https://example.com/page-sitemap.xml</loc></sitemap>
</sitemapindex>"""

    URLSET = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>https://example.com/one/</loc></url>
<url><loc>https://example.com/two/</loc></url>
</urlset>"""

    def _serve(self, files: dict, missing_ok: tuple = ()):
        def urlopen(url, timeout=None):
            for pattern in missing_ok:
                if pattern in url:
                    raise OSError("404")
            if url not in files:
                raise OSError(f"404 {url}")
            return _Body(files[url])

        urllib.request.urlopen = urlopen
        self.addCleanup(_restore_urlopen)
        return urlopen

    def test_index_is_followed_to_the_pages(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = _config(tmp)
            self._serve({
                "https://example.com/sitemap_index.xml": self.INDEX,
                "https://example.com/post-sitemap.xml": self.URLSET,
                "https://example.com/page-sitemap.xml": self.URLSET,
            })
            urls = crawl._urls_from_sitemap("https://example.com/sitemap_index.xml", cfg)

        self.assertEqual(urls, [
            "https://example.com/one/", "https://example.com/two/",
        ])
        # The decisive property: no .xml anywhere in the result.
        self.assertFalse([u for u in urls if u.endswith(".xml")])

    def test_flat_urlset_still_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = _config(tmp)
            self._serve({"https://example.com/sitemap.xml": self.URLSET})
            urls = crawl._urls_from_sitemap("https://example.com/sitemap.xml", cfg)
        self.assertEqual(len(urls), 2)

    def test_pages_are_deduplicated_across_sitemaps(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = _config(tmp)
            self._serve({
                "https://example.com/sitemap_index.xml": self.INDEX,
                "https://example.com/post-sitemap.xml": self.URLSET,
                "https://example.com/page-sitemap.xml": self.URLSET,
            })
            urls = crawl._urls_from_sitemap("https://example.com/sitemap_index.xml", cfg)
        self.assertEqual(len(urls), len(set(urls)))

    def test_max_pages_is_respected_across_all_child_sitemaps(self):
        big = ("<urlset><url><loc>https://example.com/p%d/</loc></url></urlset>"
               % 0).replace("p%d/", "".join(f"p{i}/</url><url><loc>https://example.com/" for i in range(60)))
        big = f"<urlset>{''.join(f'<url><loc>https://example.com/p{i}/</loc></url>' for i in range(60))}</urlset>"
        with tempfile.TemporaryDirectory() as tmp:
            cfg = _config(tmp, max_pages=10)
            self._serve({
                "https://example.com/sitemap_index.xml": self.INDEX,
                "https://example.com/post-sitemap.xml": big,
                "https://example.com/page-sitemap.xml": big,
            })
            urls = crawl._urls_from_sitemap("https://example.com/sitemap_index.xml", cfg)
        self.assertEqual(len(urls), 10)

    def test_missing_sitemap_raises_only_when_it_was_asked_for(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = _config(tmp)
            self._serve({}, missing_ok=("missing",))
            with self.assertRaises(crawl.CrawlError):
                crawl._urls_from_sitemap("https://example.com/missing.xml", cfg)
            # The fallback chain must not raise for every candidate it tries.
            self.assertEqual(
                crawl._urls_from_sitemap("https://example.com/missing.xml", cfg, required=False),
                [],
            )

    def test_robots_txt_is_the_first_place_looked(self):
        robots = "User-agent: *\nDisallow: /wp-admin/\nSitemap: https://example.com/from-robots.xml\n"
        with tempfile.TemporaryDirectory() as tmp:
            cfg = _config(tmp)
            self._serve({
                "https://example.com/robots.txt": robots,
                "https://example.com/from-robots.xml": self.URLSET,
            })
            urls = crawl.resolve_start_urls(cfg)
        self.assertEqual(urls, ["https://example.com/one/", "https://example.com/two/"])

    def test_known_wordpress_paths_are_tried_when_robots_is_silent(self):
        core = self.URLSET.replace("one/", "core-one/").replace("two/", "core-two/")
        with tempfile.TemporaryDirectory() as tmp:
            cfg = _config(tmp)
            self._serve({
                "https://example.com/robots.txt": "User-agent: *\n",
                "https://example.com/wp-sitemap.xml": core,
            })
            urls = crawl.resolve_start_urls(cfg)
        self.assertIn("https://example.com/core-one/", urls)

    def test_a_404_on_every_candidate_falls_back_to_the_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = _config(tmp)
            self._serve({}, missing_ok=("/",))
            urls = crawl.resolve_start_urls(cfg)
        self.assertEqual(urls, ["https://example.com/"])

    def test_configured_sitemap_beats_robots_txt(self):
        robots = "Sitemap: https://example.com/ignored.xml\n"
        with tempfile.TemporaryDirectory() as tmp:
            cfg = _config(tmp, sitemap="/sitemap.xml")
            self._serve({
                "https://example.com/robots.txt": robots,
                "https://example.com/ignored.xml": self.URLSET,
                "https://example.com/sitemap.xml": self.URLSET,
            })
            urls = crawl.resolve_start_urls(cfg)
        self.assertEqual(len(urls), 2)


class _Body:
    def __init__(self, text):
        self._text = text

    def read(self):
        return self._text.encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class ProfileTest(unittest.TestCase):
    """A profile is how a consent wall gets past - and it is a secret."""

    def test_no_profile_means_no_profile_flag(self):
        log: list = []
        with tempfile.TemporaryDirectory() as tmp:
            original = crawl._run_cli
            crawl._run_cli = _fake_runner({"https://example.com/a/": "<html></html>"}, log)
            try:
                crawl.crawl(["https://example.com/a/"], _config(tmp, settle_ms=0), run="r")
            finally:
                crawl._run_cli = original
        open_args = [a for _s, a in log if a and a[0] == "open"][0]
        self.assertFalse(any(str(x).startswith("--profile") for x in open_args),
                         "in-memory sessions are the default; a profile is opt-in")

    def test_configured_profile_is_created_and_passed(self):
        log: list = []
        pages = {"https://example.com/a/": "<html lang=de><title>t</title></html>"}
        with tempfile.TemporaryDirectory() as tmp:
            cfg = _config(tmp, settle_ms=0, profile=".browser/wo-profile")
            target = Path(tmp) / ".browser" / "wo-profile"
            original = crawl._run_cli
            crawl._run_cli = _fake_runner(pages, log)
            try:
                crawl.crawl(["https://example.com/a/"], cfg, run="r")
            finally:
                crawl._run_cli = original
            open_args = [a for _s, a in log if a and a[0] == "open"][0]
            flag = [x for x in open_args if str(x).startswith("--profile")][0]
            # Relative resolves against the workspace, so "per workspace" and
            # "per machine" are both expressible without either being preferred.
            self.assertEqual(Path(str(flag).split("=", 1)[1]).resolve(), target.resolve())
            self.assertTrue(target.is_dir())

    def test_absolute_profile_is_left_alone(self):
        log: list = []
        pages = {"https://example.com/a/": "<html lang=de><title>t</title></html>"}
        with tempfile.TemporaryDirectory() as tmp:
            elsewhere = Path(tmp) / "machine-profiles" / "client-site"
            cfg = _config(tmp, settle_ms=0, profile=str(elsewhere))
            original = crawl._run_cli
            crawl._run_cli = _fake_runner(pages, log)
            try:
                crawl.crawl(["https://example.com/a/"], cfg, run="r")
            finally:
                crawl._run_cli = original
            open_args = [a for _s, a in log if a and a[0] == "open"][0]
            flag = [x for x in open_args if str(x).startswith("--profile")][0]
            self.assertEqual(Path(str(flag).split("=", 1)[1]).resolve(), elsewhere.resolve())

    def test_profile_must_be_a_string(self):
        with self.assertRaises(ConfigError):
            crawl_settings({"crawl": {"profile": 42}})


class CrawlSettingsTest(unittest.TestCase):
    def test_defaults(self):
        settings = crawl_settings({})
        self.assertEqual(settings["max_pages"], 200)
        self.assertEqual(settings["timeout_seconds"], crawl.DEFAULT_TIMEOUT)
        self.assertEqual(settings["start_urls"], [])

    def test_rejects_nonsense_numbers(self):
        for bad in ({"timeout_seconds": 0}, {"timeout_seconds": -1},
                    {"max_pages": 0}, {"settle_ms": -5}):
            with self.subTest(bad=bad):
                with self.assertRaises(ConfigError):
                    crawl_settings({"crawl": bad})

    def test_rejects_boolean_where_a_number_is_expected(self):
        # bool is an int subclass; True would silently mean "1 second".
        with self.assertRaises(ConfigError):
            crawl_settings({"crawl": {"timeout_seconds": True}})

    def test_start_urls_must_be_strings(self):
        with self.assertRaises(ConfigError):
            crawl_settings({"crawl": {"start_urls": [1234]}})


class StartUrlTest(unittest.TestCase):
    def test_explicit_urls_win_and_become_absolute(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = _config(tmp, start_urls=["/a/", "https://other.example/b/"])
            self.assertEqual(
                crawl.resolve_start_urls(cfg),
                ["https://example.com/a/", "https://other.example/b/"],
            )

    def test_without_configuration_the_root_is_the_guess(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = _config(tmp)
            self.assertEqual(crawl.resolve_start_urls(cfg), ["https://example.com/"])


class SlugTest(unittest.TestCase):
    def test_url_becomes_a_filesystem_safe_name(self):
        slug = crawl._slug("https://example.com/news/2026-item/")
        self.assertNotIn("/", slug)
        self.assertIn("news", slug)
        self.assertLessEqual(len(slug), 120)

    def test_root_url_does_not_collapse_to_nothing(self):
        self.assertTrue(crawl._slug("https://example.com/").strip())


class CrawlTest(unittest.TestCase):
    def test_pages_are_extracted_and_artifacts_land_beside_the_run(self):
        pages = {f"https://example.com/p{i}/": f"<html lang=de><title>T{i}</title></html>"
                 for i in range(3)}
        log: list = []
        with tempfile.TemporaryDirectory() as tmp:
            cfg = _config(tmp, settle_ms=0)
            original = crawl._run_cli
            crawl._run_cli = _fake_runner(pages, log)
            try:
                result = crawl.crawl(list(pages), cfg, run="2026-01-01T00-00-00Z")
            finally:
                crawl._run_cli = original

            self.assertEqual(result.fetched, 3)
            self.assertEqual([p.source for p in result.pages],
                             list(pages.keys()))
            self.assertEqual(result.pages[0].title, "T0")

            # D27: raw crawl output is beside the run, in the data zone.
            artifact_dir = Path(tmp) / "data" / "crawl" / "2026-01-01T00-00-00Z"
            self.assertTrue(artifact_dir.is_dir())
            written = list(artifact_dir.glob("*.html"))
            self.assertEqual(len(written), 3)
            # Each artifact says which URL produced it.
            self.assertIn("url: https://example.com/p0/", written[0].read_text(encoding="utf-8"))

    def test_one_failed_page_does_not_discard_the_crawl(self):
        pages = {"https://example.com/ok/": "<html lang=de><title>ok</title></html>"}
        with tempfile.TemporaryDirectory() as tmp:
            cfg = _config(tmp, settle_ms=0)

            def runner(session, args, timeout, command=None):
                if args and args[0] == "goto" and "bad" in args[1]:
                    return _proc(1, "", "net::ERR_NAME_NOT_RESOLVED")
                return _fake_runner(pages)(session, args, timeout, command)

            original = crawl._run_cli
            crawl._run_cli = runner
            try:
                result = crawl.crawl(
                    ["https://example.com/bad/", "https://example.com/ok/"], cfg, run="r"
                )
            finally:
                crawl._run_cli = original

            self.assertEqual(result.fetched, 1)
            self.assertEqual(len(result.failed), 1)
            self.assertIn("bad", result.failed[0]["url"])
            # The reason is the first line only: a full CLI message would put
            # page-adjacent noise into the report.
            self.assertNotIn("\n", result.failed[0]["reason"])

    def test_total_failure_raises_rather_than_writing_an_empty_report(self):
        def runner(session, args, timeout, command=None):
            if args and args[0] == "goto":
                return _proc(1, "", "timed out")
            return _proc(0, "")

        with tempfile.TemporaryDirectory() as tmp:
            cfg = _config(tmp, settle_ms=0)
            original = crawl._run_cli
            crawl._run_cli = runner
            try:
                with self.assertRaises(crawl.CrawlError):
                    crawl.crawl(["https://example.com/a/"], cfg, run="r")
            finally:
                crawl._run_cli = original

    def test_a_wall_stops_the_audit_from_producing_findings(self):
        wall = "<html><body><div id=consent-gate>Bitte akzeptieren</div></body></html>"
        pages = {f"https://example.com/p{i}/": wall for i in range(5)}
        with tempfile.TemporaryDirectory() as tmp:
            cfg = _config(tmp, settle_ms=0)
            original = crawl._run_cli
            crawl._run_cli = _fake_runner(pages)
            try:
                result = crawl.crawl(list(pages), cfg, run="r")
            finally:
                crawl._run_cli = original
            self.assertTrue(result.wall_suspected)
            self.assertIn("consent", result.wall_reason)

    def test_session_is_closed_even_when_a_page_fails(self):
        log: list = []
        pages = {"https://example.com/ok/": "<html lang=de><title>t</title></html>"}
        with tempfile.TemporaryDirectory() as tmp:
            cfg = _config(tmp, settle_ms=0)
            original = crawl._run_cli
            crawl._run_cli = _fake_runner(pages, log)
            try:
                crawl.crawl(list(pages), cfg, run="r")
            finally:
                crawl._run_cli = original
            verbs = [args[0] for _session, args in log if args]
            self.assertIn("open", verbs)
            self.assertIn("close", verbs)

    def test_session_name_carries_the_domain(self):
        """Two harnesses must not share a browser session."""
        log: list = []
        pages = {"https://example.com/ok/": "<html lang=de><title>t</title></html>"}
        with tempfile.TemporaryDirectory() as tmp:
            cfg = _config(tmp, settle_ms=0)
            original = crawl._run_cli
            crawl._run_cli = _fake_runner(pages, log)
            try:
                crawl.crawl(list(pages), cfg, run="r")
            finally:
                crawl._run_cli = original
            self.assertTrue(all(s == "wo-example.com" for s, _ in log))


class EncodingTest(unittest.TestCase):
    """Regression: page bytes are not the terminal's encoding."""

    def test_utf8_bytes_survive_a_decode(self):
        import subprocess
        completed = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout="<html><title>Patrícia – Über</title></html>".encode("utf-8"),
            stderr=b"",
        )
        decoded = completed.stdout.decode("utf-8", "replace")
        self.assertIn("Patrícia", decoded)

    def test_undecodable_bytes_do_not_raise(self):
        """cp1252 would raise here; 'replace' keeps the audit alive."""
        raw = b"<html><title>\x90\xfe</title></html>"
        self.assertIsInstance(raw.decode("utf-8", "replace"), str)


if __name__ == "__main__":
    unittest.main()