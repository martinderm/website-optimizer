---
type: object
cluster: interface
universe: live
status: verified
entity: scripts/wo.py
verified_at: 2026-10-15
revision: a2dda236b34e6222be84c6068d84203f340219a8
---

# CLI

Der einzige ausführbare Einstiegspunkt. Fünf Kommandos, ein Dispatch.

## Why this shape
Zwei Einstiegspunkte driften auseinander, sobald sich das Argumentparsing
einmal unterscheidet. Deshalb ist `wo.py` die einzige ausführbare Datei;
Capability-Module sind Pakete, keine Skripte. Weil `wo.py` beim Start sein eigenes
Verzeichnis auf `sys.path` legt, funktionieren die Paketimporte ohne
Pfadmanipulation — das löst das Importproblem, statt es zu verwalten (D2/D21).

Die zweite Konsequenz ist wichtiger: `run-all` führt discover → audit → compare
aus. Die Reihenfolge steht damit im Code und nicht in Ordnernamen.

## Shape
`scripts/wo.py:46` `cmd_init_site`, `:64` `_run_capability` (Auflösung über
`REGISTRY`, Capability-Deaktivierung, Schema-Validierung, Schreiben), `:108`
`cmd_on_page`, `:112` `cmd_run_all`, `:129` `cmd_runs`, `:138`
`cmd_validate_report`, `:153` `main`.

Kommandos: `init-site`, `on-page`, `run-all`, `runs`, `validate-report`.
Gemeinsame Flags: `--config`, `--workspace`, `--json`. Audit-Kommandos zusätzlich
`--strict`, `--ignore-noindex`, `--run`, `--dry-run`.

Exit-Codes: `0` Erfolg, `1` nur bei `--strict` mit kritischem Befund, `2` wenn
`success` falsch ist. Fehlerpfade liefern eine selbstkorrigierende Meldung im
Envelope, keinen Traceback.

- [scripts/wo.py](../../../scripts/wo.py) — `:64` (_run_capability), `:153` (main)
- [scripts/wo/capabilities/__init__.py](../../../scripts/wo/capabilities/__init__.py) — `REGISTRY`

## Connected to
Gehört zu [Envelope](envelope.md), [On-Page](on-page.md), [Site-Config](site-config.md). Prozesse: [Audit-Statisch](../processes/audit-static.md), [Baseline-Vergleich](../processes/compare-baseline.md).

## If you change this
- **Hits:** `REGISTRY` (Name ↔ Modulpfad), alle Kommandosamen, `scripts/README.md`, `SKILL.md` (Quick Start), [Envelope](envelope.md) (Exit-Code-Auswertung), [Qualität](quality.md).
- **Does not hit:** die Regeln in `references/*`; [Receipt](receipt.md) und [Audit-Report](audit-report.md), solange ihre Schemata unverändert bleiben.

## Surfaces
stdout/stderr. Aufgerufen von Agenten im konsumierenden Workspace, aus
`hugo-wizard` als `.agents/skills/website-optimizer/scripts/wo.py`.

## See
[scripts/README.md](../../../scripts/README.md). [Änderungsrouting](../effects/CONTEXT.md).