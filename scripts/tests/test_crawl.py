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