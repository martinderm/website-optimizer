"""The system map must not describe a tool that no longer exists.

Two weeks of work produced this failure three times: a rule is added, and the map
keeps describing the rule set as it was. The code has a guard — the round-trip
test between `CHECKS` and the rules a capability can emit — and the map had none.

What this file checks, and deliberately what it does not:

**It does not require the map to list every rule.** The map is a map, not a
specification. A card that enumerates the full rule set duplicates `CHECKS`, and a
duplicate is the thing that goes stale. `on-page.md` names its rules in prose —
`lang`, `h1`, `og:title` — which is a description, and forcing it into eighteen
full identifiers would make it a second source of truth.

**It does check that every rule identifier the map does write out exists.** A full
identifier is a citation, and a citation to something that was renamed or removed
is drift with a wrong answer in it. That is the direction that can be checked
without turning cards into tables.

**And it checks the map's own structure**: every card points at a file that
exists, and every card is reachable from the index. Both are mechanical failures
that read as complete.
"""

from __future__ import annotations

import importlib
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from wo.capabilities import REGISTRY  # noqa: E402
from wo.capabilities.compare.audit import KINDS  # noqa: E402

MAP_DIR = ROOT / "docs" / "system-map"

# A rule identifier never ends in a file extension. Without this the pattern
# matches `schema.json`, `schema.md` and `schema.org`, which are a schema file, a
# card and a vocabulary — three things that are not rules.
FILE_SUFFIXES = {
    "json", "md", "org", "py", "toml", "yaml", "yml", "xml", "html",
    "csv", "tsv", "txt", "conf", "sh", "ps1",
}


def _rules_run() -> set[str]:
    """Every rule identifier the tool can report, from the tool itself."""
    ids: set[str] = set()
    for entry in REGISTRY.values():
        module = importlib.import_module(entry["module"])
        ids |= set(getattr(module, "CHECKS", ()) or ())
    ids |= set(KINDS)
    ids |= {f"compare.{kind}" for kind in KINDS}
    return ids


def _namespaces(ids: set[str]) -> set[str]:
    return {i.split(".")[0] for i in ids}


def _cited_rules(text: str, namespaces: set[str]) -> set[str]:
    pattern = re.compile(
        r"\b(" + "|".join(sorted(map(re.escape, namespaces))) + r")\.[a-z][a-z0-9_]*\b"
    )
    found = {m.group(0) for m in pattern.finditer(text)}
    return {t for t in found if t.split(".", 1)[1] not in FILE_SUFFIXES}


def _map_files() -> list[Path]:
    return sorted(MAP_DIR.rglob("*.md"))


class CitedRulesExistTest(unittest.TestCase):
    """A rule identifier written out in a card has to be a rule that exists."""

    def test_every_cited_rule_identifier_is_a_real_rule(self):
        known = _rules_run()
        namespaces = _namespaces(known)

        stale: dict[str, set[str]] = {}
        for md in _map_files():
            for token in _cited_rules(md.read_text(encoding="utf-8"), namespaces):
                if token not in known:
                    stale.setdefault(token, set()).add(md.name)

        self.assertEqual(
            stale, {},
            "The map cites rule identifiers the tool cannot emit. Either the rule "
            "was renamed or removed and the card was not, or the card invented one. "
            f"Stale: { {k: sorted(v) for k, v in stale.items()} }\n"
            f"Known identifiers: {sorted(known)}",
        )

    def test_the_check_can_actually_fail(self):
        """A guard that cannot fail is decoration.

        The map cites dozens of dotted tokens that are not rules — file names,
        the schema.org domain. If the filter were wrong, the test above would pass
        for the wrong reason on every run.
        """
        namespaces = _namespaces(_rules_run())
        text = "See `report-base.schema.json` and `schema.org` and `image.not_a_rule`."
        cited = _cited_rules(text, namespaces)
        self.assertIn("image.not_a_rule", cited)
        self.assertNotIn("schema.json", cited)
        self.assertNotIn("schema.org", cited)


class StructureTest(unittest.TestCase):
    """Mechanical failures in the map that read as a complete map."""

    def test_every_card_points_at_a_file_that_exists(self):
        missing: list[str] = []
        for md in _map_files():
            if md.parent.name == "_templates":
                continue
            text = md.read_text(encoding="utf-8")
            front = text.split("---", 2)
            if len(front) < 3:
                continue
            entity = re.search(r"^entity:\s*(\S+)\s*$", front[1], re.M)
            if not entity:
                continue
            target = ROOT / entity.group(1)
            if not target.exists():
                missing.append(f"{md.name} -> {entity.group(1)}")
        self.assertEqual(missing, [], f"Cards cite files that are gone: {missing}")

    def test_every_object_card_is_reachable_from_the_index(self):
        """A card nobody links to is a card nobody reads."""
        index = (MAP_DIR / "objects" / "_index.md").read_text(encoding="utf-8")
        cards = sorted(
            p.stem for p in (MAP_DIR / "objects").glob("*.md")
            if p.name not in ("_index.md", "CONTEXT.md")
        )
        unreachable = [c for c in cards if f"({c}.md)" not in index]
        self.assertEqual(unreachable, [], f"Not listed in _index.md: {unreachable}")

    def test_every_process_card_is_reachable(self):
        context = (MAP_DIR / "processes" / "CONTEXT.md").read_text(encoding="utf-8")
        cards = sorted(
            p.stem for p in (MAP_DIR / "processes").glob("*.md")
            if p.name != "CONTEXT.md"
        )
        unreachable = [c for c in cards if f"({c}.md)" not in context]
        self.assertEqual(unreachable, [], f"Not listed in processes/CONTEXT.md: {unreachable}")

    def test_every_capability_has_a_card(self):
        """A capability the map never mentions is one nobody knows to change."""
        listed = " ".join(
            p.read_text(encoding="utf-8").lower() for p in _map_files()
        )
        absent = [c for c in REGISTRY if c.replace("-", " ") not in listed
                  and c not in listed]
        self.assertEqual(absent, [], f"Capabilities missing from the map: {absent}")

    def test_the_generated_twins_are_byte_identical(self):
        """routing.md and AGENTS.md are copies of README.md, never hand-edited.

        A twin that drifts is worse than no twin: two files that look like the
        same document and disagree.
        """
        base = (MAP_DIR / "README.md").read_bytes()
        for twin in ("AGENTS.md", "routing.md"):
            self.assertEqual(
                (MAP_DIR / twin).read_bytes(), base,
                f"{twin} differs from README.md. Regenerate it: "
                f"copy README.md over it, do not edit it.",
            )


if __name__ == "__main__":
    unittest.main()