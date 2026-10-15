"""Configuration loading, including the portable/local layering."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wo import config as config_module  # noqa: E402

PORTABLE = """\
[site]
url = "https://example.com"
static_dir = "public"

[audit]
capabilities = ["on-page"]
ignore_path = "admin/.*"
strict = false
"""

LOCAL = """\
[site]
static_dir = "D:/sites/example/public"

[audit]
strict = true
"""


LOCAL_COMPLETE = """\
[site]
url = "https://example.com"
static_dir = "D:/sites/example/public"

[audit]
strict = true
"""


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / config_module.CONFIG_NAMES[0]).write_text(PORTABLE, encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_portable_only(self):
        cfg = config_module.load(workspace_root=self.root)
        self.assertEqual(cfg.site_url, "https://example.com")
        self.assertEqual(cfg.domain, "example.com")
        self.assertEqual(cfg.static_dir, self.root / "public")
        self.assertFalse(cfg.strict)

    def test_local_overrides_are_merged_not_replacing(self):
        (self.root / config_module.CONFIG_NAMES[1]).write_text(LOCAL, encoding="utf-8")
        cfg = config_module.load(workspace_root=self.root)
        # Overridden by the local file.
        self.assertEqual(cfg.static_dir, Path("D:/sites/example/public"))
        self.assertTrue(cfg.strict)
        # Not mentioned locally, so the portable values survive.
        self.assertEqual(cfg.ignore_path, "admin/.*")
        self.assertEqual(cfg.capabilities, ["on-page"])
        self.assertEqual(cfg.site_url, "https://example.com")

    def test_explicit_config_still_applies_the_local_layer(self):
        """--config names the base file; the sibling overlay still applies.

        Regression: the local file was only merged in the auto-discovery
        branch, so the documented call `--config site.optimizer.toml` dropped
        every machine-specific path and then failed with a directory that
        looked configured but was not. Found while verifying the image audit
        against a real site, not by a test.
        """
        (self.root / config_module.CONFIG_NAMES[1]).write_text(LOCAL, encoding="utf-8")
        cfg = config_module.load(path=self.root / config_module.CONFIG_NAMES[0],
                                 workspace_root=self.root)
        self.assertEqual(cfg.static_dir, Path("D:/sites/example/public"))
        self.assertTrue(cfg.strict)

    def test_explicitly_naming_the_local_file_is_not_double_applied(self):
        """A complete local file is valid on its own, and merges only once."""
        (self.root / config_module.CONFIG_NAMES[1]).write_text(LOCAL_COMPLETE, encoding="utf-8")
        cfg = config_module.load(path=self.root / config_module.CONFIG_NAMES[1],
                                 workspace_root=self.root)
        self.assertEqual(cfg.static_dir, Path("D:/sites/example/public"))
        self.assertEqual(cfg.site_url, "https://example.com")

    def test_overlay_alone_is_rejected_because_it_is_not_a_config(self):
        """The local file carries overrides, not a site identity."""
        (self.root / config_module.CONFIG_NAMES[1]).write_text(LOCAL, encoding="utf-8")
        with self.assertRaises(config_module.ConfigError):
            config_module.load(path=self.root / config_module.CONFIG_NAMES[1],
                               workspace_root=self.root)

    def test_explicit_config_without_sibling_local_is_unchanged(self):
        other = self.root / "elsewhere"
        other.mkdir()
        target = other / config_module.CONFIG_NAMES[0]
        target.write_text(PORTABLE, encoding="utf-8")
        cfg = config_module.load(path=target, workspace_root=self.root)
        self.assertEqual(cfg.static_dir, self.root / "public")

    def test_missing_config_names_the_fix(self):
        empty = self.root / "empty"
        empty.mkdir()
        with self.assertRaises(config_module.ConfigError) as caught:
            config_module.load(workspace_root=empty)
        self.assertIn("init-site", str(caught.exception))

    def test_missing_url_names_the_fix(self):
        (self.root / config_module.CONFIG_NAMES[0]).write_text("[audit]\n", encoding="utf-8")
        with self.assertRaises(config_module.ConfigError) as caught:
            config_module.load(workspace_root=self.root)
        self.assertIn("[site] url", str(caught.exception))

    def test_invalid_classification_is_rejected(self):
        (self.root / config_module.CONFIG_NAMES[0]).write_text(
            '[site]\nurl = "https://x.example"\n\n[audit]\ndata_classification = "topsecret"\n',
            encoding="utf-8",
        )
        with self.assertRaises(config_module.ConfigError) as caught:
            config_module.load(workspace_root=self.root)
        self.assertIn("data_classification", str(caught.exception))

    def test_classification_escalates_when_private_surface_was_touched(self):
        (self.root / config_module.CONFIG_NAMES[0]).write_text(
            '[site]\nurl = "https://x.example"\n\n[audit]\ncontacted_private_surface = true\n',
            encoding="utf-8",
        )
        cfg = config_module.load(workspace_root=self.root)
        self.assertEqual(cfg.classification, "confidential")

    def test_owner_defaults_to_workspace_slug(self):
        cfg = config_module.load(workspace_root=self.root)
        self.assertEqual(cfg.owner, self.root.name)


if __name__ == "__main__":
    unittest.main()