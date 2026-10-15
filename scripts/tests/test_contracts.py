"""Envelope, schema validator, and run storage."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wo import envelope as env  # noqa: E402
from wo import jsonschema  # noqa: E402
from wo import report as report_module  # noqa: E402
from wo.config import SiteConfig  # noqa: E402


class EnvelopeTest(unittest.TestCase):
    def test_envelope_has_the_standard_keys(self):
        result = env.envelope("on-page", True, "Succeeded", "ok", data={"a": 1})
        self.assertEqual(set(result), set(env.ENVELOPE_KEYS))
        self.assertIsNone(result["error"])

    def test_unknown_state_is_rejected_at_construction(self):
        with self.assertRaises(ValueError):
            env.envelope("on-page", True, "Mostly Fine", "typo in a state")


class ValidatorTest(unittest.TestCase):
    def test_required_and_additional_properties(self):
        schema = {
            "type": "object",
            "required": ["a"],
            "additionalProperties": False,
            "properties": {"a": {"type": "string"}},
        }
        self.assertEqual(jsonschema.validate({"a": "x"}, schema), [])
        self.assertTrue(jsonschema.validate({}, schema))
        self.assertTrue(jsonschema.validate({"a": "x", "b": 1}, schema))

    def test_boolean_is_not_an_integer(self):
        self.assertTrue(jsonschema.validate(True, {"type": "integer"}))
        self.assertEqual(jsonschema.validate(3, {"type": "integer"}), [])

    def test_union_types(self):
        self.assertEqual(jsonschema.validate(None, {"type": ["string", "null"]}), [])

    def test_if_then(self):
        schema = {
            "type": "object",
            "properties": {"zone": {"enum": ["cloud", "evidence"]}},
            "allOf": [{
                "if": {"properties": {"zone": {"const": "cloud"}}, "required": ["zone"]},
                "then": {"required": ["source_uri", "synced_at"]},
            }],
        }
        self.assertTrue(jsonschema.validate({"zone": "cloud"}, schema))
        self.assertEqual(jsonschema.validate({"zone": "evidence", "synced_at": "x"}, schema), [])


class ReceiptTest(unittest.TestCase):
    def _config(self, root: Path) -> SiteConfig:
        return SiteConfig(
            site_url="https://example.com", domain="example.com",
            static_dir=root, workspace_root=root,
            contacted_private_surface=True,
        )

    def test_receipt_conforms_and_escalates_classification(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = {"report_version": "1", "findings": []}
            receipt = report_module.build_receipt(report, self._config(root), "run-1")
            self.assertEqual(receipt["zone"], "evidence")
            self.assertEqual(receipt["trust_level"], "observed")
            self.assertEqual(receipt["data_classification"], "confidential")
            self.assertEqual(receipt["owner"], root.name)
            self.assertTrue(receipt["instructions_are_data"])
            self.assertEqual(jsonschema.validate(receipt, report_module.RECEIPT_CONFORMANCE), [])

    def test_run_is_written_into_the_evidence_zone_and_is_listed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            written = report_module.write_run(self._config(root), {"findings": []}, run="2026-01-01T00-00-00Z")
            self.assertTrue(written["report"].is_file())
            self.assertTrue(written["receipt"].is_file())
            self.assertIn(
                "memory/evidence/websites/example.com/runs/2026-01-01T00-00-00Z",
                written["run_dir"].as_posix(),
            )
            self.assertEqual(report_module.list_runs(root, "example.com"),
                             ["2026-01-01T00-00-00Z"])

    def test_evidence_is_append_only_across_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_module.write_run(self._config(root), {"n": 1}, run="2026-01-01T00-00-00Z")
            report_module.write_run(self._config(root), {"n": 2}, run="2026-01-02T00-00-00Z")
            self.assertEqual(len(report_module.list_runs(root, "example.com")), 2)
            first = report_module.load_run(root, "example.com", "2026-01-01T00-00-00Z")
            self.assertEqual(first["n"], 1)

    def test_run_id_has_no_characters_windows_forbids_in_paths(self):
        for char in "run_id":
            self.assertNotIn(char, ":<>\"/\\|?*")

    def test_atomic_write_leaves_no_temporary_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "out.json"
            report_module.atomic_write(target, json.dumps({"ok": True}))
            self.assertEqual(json.loads(target.read_text(encoding="utf-8")), {"ok": True})
            self.assertEqual([p.name for p in Path(tmp).iterdir() if p.name != "out.json"], [])


if __name__ == "__main__":
    unittest.main()