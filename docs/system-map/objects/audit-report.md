---
type: object
cluster: interface
universe: live
status: verified
entity: scripts/schemas/audit-report.schema.json
verified_at: 2026-10-15
revision: a2dda236b34e6222be84c6068d84203f340219a8
---

# Audit-Report

Das Artefakt eines Laufs: Findings und Zusammenfassung, gegen ein eigenes Schema
validiert.

## Why this shape
Zwei Entscheidungen stecken darin. Erstens sind Findings **atomar** — `rule_id`,
`observed`, `expected`, `page`, `location` statt zweier lose String-Listen. Damit
ist ein Befund prüfbar, ohne die Seite erneut zu laden, und ein Urteil lässt sich
aus den Befunden ableiten statt in ihnen zu stehen (D15). Zweitens ist das Schema
eine Datei und keine Prosa: `validate-report` prüft sie maschinell, und
`_run_capability` verweigert das Schreiben, wenn die Validierung fehlschlägt.

`additionalProperties: false` auf allen Ebenen. Ein Report mit unbekanntem Feld
ist ein Report auf einem anderen Stand, und das soll auffallen.

## Shape
`scripts/schemas/audit-report.schema.json` — Pflichtfelder: `report_version`,
`tool`, `generated_at`, `crawl_mode`, `site`, `source`, `summary`, `pages`,
`findings`. `crawl_mode` ist `enum [static, live]`; `severity` in Findings ist
`enum [critical, warning]`; `observed` und `expected` sind bewusst untypisiert,
weil der beobachtete Wert je nach Regel Boolean, Integer oder String ist.

Validierung: `scripts/wo/jsonschema.py` (Untermenge, siehe dort `SUPPORTED`).
`_run_capability` ruft `jsonschema.validate` vor `write_run`.

- [scripts/schemas/audit-report.schema.json](../../../scripts/schemas/audit-report.schema.json)
- [scripts/wo/jsonschema.py](../../../scripts/wo/jsonschema.py) — `:23` (SUPPORTED, die abgedeckte Untermenge), `:52` (validate), `:109` (assert_valid)

## Connected to
Gehört zu [Envelope](envelope.md), [On-Page](on-page.md), [Receipt](receipt.md). Prozesse: [Audit-Statisch](../processes/audit-static.md), [Baseline-Vergleich](../processes/compare-baseline.md).

## If you change this
- **Hits:** `run()` in [On-Page](on-page.md) (erzeugt die Struktur), [Receipt](receipt.md) (dessen `artifact_sha256` ist der Hash dieses Dokuments), `validate-report` in [CLI](cli.md), die Test-Fixtures in [Qualität](quality.md), und diese Karte — Schemaänderungen sind vertragsrelevant.
- **Does not hit:** [Page](page.md) (Extraktion, nicht Struktur); [Site-Config](site-config.md); die Regel*inhalte* in `references/*`.

## Surfaces
`memory/evidence/websites/<domain>/runs/<run-id>/report.json` im konsumierenden
Workspace. Gelesen von `compare` (geplant) und von Menschen.

## See
[scripts/README.md](../../../scripts/README.md). [Änderungsrouting](../effects/CONTEXT.md).