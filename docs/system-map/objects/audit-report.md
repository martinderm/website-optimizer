---
type: object
cluster: interface
universe: live
status: verified
entity: scripts/schemas/report-base.schema.json
verified_at: 2026-10-16
revision: a2dda236b34e6222be84c6068d84203f340219a8
---

# Audit-Report

Das Artefakt eines Laufs: Findings und Zusammenfassung, gegen ein eigenes Schema
validiert.

## Why this shape
Drei Entscheidungen stecken darin.

**Findings sind atomar** — `rule_id`, `observed`, `expected`, `subject`,
`location` statt zweier lose String-Listen. Damit ist ein Befund prüfbar, ohne
die Seite erneut zu laden, und ein Urteil lässt sich aus den Befunden ableiten
statt in ihnen zu stehen (D15).

**Das Schema ist eine Datei und keine Prosa.** `validate-report` prüft sie
maschinell, und `_run_capability` verweigert das Schreiben, wenn die Validierung
fehlschlägt.

**Es gibt eine Basis und Capability-Erweiterungen.** `report-base.schema.json`
trägt, was jeder Report braucht (`report_version`, `tool`, `crawl_mode`, `site`,
`findings`). Jede Capability hat ein eigenes Schema, das per `allOf` einbindet.
Der Auslöser war die zweite Capability: eine `summary`-Struktur für `on-page`
ließ sich nicht auf `redirects` anwenden, ohne entweder eine gemeinsame
Superstruktur zu erfinden oder genau die Kopplung zu bauen, die das Skill-Projekt
vermeiden sollte (D23).

`additionalProperties: false` auf allen Ebenen. Ein Report mit unbekanntem Feld
ist ein Report auf einem anderen Stand, und das soll auffallen.

## Shape
`scripts/schemas/report-base.schema.json` — gemeinsame Pflichtfelder und die
Finding-Definition. `subject` heißt so statt `page`, weil nicht jede Capability
über Seiten spricht: ein Redirect-Befund hat eine Quelle, keine Seite.

`scripts/schemas/on-page-report.schema.json` — `source.kind` ist jetzt ein
Enum aus `static_dir` und `live_render`, `summary` mit `audited_pages`, `pages[]`.
`scripts/schemas/redirects-report.schema.json` — `source.kind: redirect_file`,
`summary` mit `passed`/`failed`, `checks[]` (eine Zeile pro geprüfter Regel).

**`crawl` ist nur bei Live-Läufen Pflicht, und genau deshalb Pflicht.** Ein Report
über 0 Befunde aus 3 abgerufenen Seiten bedeutet etwas anderes als derselbe
Report über 400. Ohne den Block wären beide ununterscheidbar, und die
Befundzahl antwortet auf „was ist falsch", nie auf „wie viel hast du gesehen"
(D32).

`scripts/wo/jsonschema.py:52` `validate`, `:109` `assert_valid`, `:23`
`SUPPORTED`, dazu `load_schema` für `$ref`-Auflösung.

- [scripts/schemas/report-base.schema.json](../../../scripts/schemas/report-base.schema.json)
- [scripts/schemas/on-page-report.schema.json](../../../scripts/schemas/on-page-report.schema.json)
- [scripts/schemas/redirects-report.schema.json](../../../scripts/schemas/redirects-report.schema.json)
- [scripts/wo/jsonschema.py](../../../scripts/wo/jsonschema.py) — `:23` (SUPPORTED), `:52` (validate)

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