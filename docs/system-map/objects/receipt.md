---
type: object
cluster: interface
universe: live
status: verified
entity: scripts/wo/report.py
verified_at: 2026-10-15
revision: a2dda236b34e6222be84c6068d84203f340219a8
---

# Receipt

Der Daten-Zonen-Beleg eines Laufs, nach `data-zone-artifact.schema.json`.

## Why this shape
Ein Beleg, den kein Werkzeug lesen kann, ist Dekoration. Deshalb verwendet das
Receipt die Haus-Feldnamen (`source_version`, `synced_at`, `converter`,
`artifact_sha256`, `promotion_policy`) statt eines privaten
`provenance`-Blocks. Verifiziert wurde gegen das echte Schema aus
`agent-architecture`, nicht nur gegen eine lokale Teilmenge.

Die zweite Entscheidung ist der Speicherort. Evidence ist logisch append-only:
Korrekturen kommen als neuer Eintrag, nicht durch Überschreiben. Deshalb ein
Ordner pro Lauf und kein `baseline.json`, das bei jedem Lauf neu geschrieben
würde.

## Shape
`scripts/wo/report.py:35` `RECEIPT_CONFORMANCE` — die lokal durchgesetzte
Teilmenge, mit Haus-Vokabular. `:79` `atomic_write` (tempfile + `os.replace`),
`:101` `list_runs`, `:109` `build_receipt`, `:140` `write_run`.

Belegte Felder: `zone: evidence`, `trust_level: observed`, `status: active`,
`owner` = Workspace-Slug (D17), `data_classification` mit Eskalation auf
`confidential`, `retention_class`, `instructions_are_data: true` (D13),
`promotion_policy: approval_required`.

Ablage:
`<workspace>/memory/evidence/websites/<domain>/runs/<run-id>/{report,receipt}.json`
Die Run-ID ist ein UTC-Zeitstempel ohne Doppelpunkte — Windows verbietet sie in
Pfaden.

- [scripts/wo/report.py](../../../scripts/wo/report.py) — `:35`, `:79`, `:109`, `:140`

## Connected to
Gehört zu [Audit-Report](audit-report.md) (dessen Hash steht im Beleg), [Site-Config](site-config.md) (liefert `owner` und Klassifikation). Prozesse: [Audit-Statisch](../processes/audit-static.md).

## If you change this
- **Hits:** `write_run` und alles, was einen Lauf erzeugt; die Zonen-Zuordnung im konsumierenden Workspace; [Audit-Report](audit-report.md) bei Hash-Änderungen; [Qualität](quality.md) (Receipt-Tests); diese Karte.
- **Does not hit:** [Page](page.md); [Envelope](envelope.md) — der Beleg ist kein Envelope; [Referenzsatz](reference-set.md).

## Surfaces
`memory/evidence/websites/<domain>/runs/<run-id>/receipt.json`. Gelesen vom
Workspace-Linter (`WS-D01`/`WS-D02`) und von `wo.py runs`.

## See
[scripts/README.md](../../../scripts/README.md). [Änderungsrouting](../effects/CONTEXT.md).