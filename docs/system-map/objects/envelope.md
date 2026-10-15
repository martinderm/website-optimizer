---
type: object
cluster: interface
universe: live
status: verified
entity: scripts/wo/envelope.py
verified_at: 2026-10-15
revision: a2dda236b34e6222be84c6068d84203f340219a8
---

# Envelope

Rückgabevertrag jedes Kommandos. Sechs Felder, immer vorhanden.

## Why this shape
Der Authoring Guide des Shared-Skill-Repos verlangt ein strukturiertes CLI-Envelope, damit aufrufende Agenten ein Dokument parsen statt Text zu schaben. Die sechs Felder beantworten drei Fragen getrennt: was wurde versucht (`action`), wie ging es aus (`success`, `state`), und was sagt ein Mensch (`message`). `error` ist getrennt von `data`, damit ein Fehler nicht versehentlich als Ergebnis gelesen wird.

## Shape
`scripts/wo/envelope.py:14` definiert `ENVELOPE_KEYS = ("action","success","state","message","data","error")`; `:18` die geschlossene Zustandsmenge `("Succeeded","Partial","Failed","Blocked","DryRun")`; `:21` den Konstruktor; `:42` die Ausgabe (`--json` voll, sonst eine Zeile); `:53` den Fehler-Kurzweg.

`envelope()` wirft bei unbekanntem `state`. Das ist Absicht: ein Tippfehler im Zustandswert fällt dann beim Erzeugen auf, nicht beim Parsen durch den Aufrufer.

- [scripts/wo/envelope.py](../../../scripts/wo/envelope.py) — `:14` (ENVELOPE_KEYS), `:18` (STATES), `:21` (envelope), `:53` (failure)

## Connected to
Gehört zu [CLI](cli.md), [Audit-Report](audit-report.md). Prozess: [Audit-Statisch](../processes/audit-static.md).
**Looks like but is not:** das `report.json` ist kein Envelope — es ist ein Artefakt mit eigenem Schema. Das Envelope transportiert den Report, es ist nicht der Report.

## If you change this
- **Hits:** jedes Kommando in `scripts/wo.py`, jedes `failure()`/`envelope()`-Aufrufmuster, die Karten [CLI](cli.md) und [Audit-Report](audit-report.md), `scripts/README.md` (Envelope-Abschnitt), [Qualität](quality.md) (die States-Tests).
- **Does not hit:** `references/*` — die Regeln sind envelope-unabhängig; [Receipt](receipt.md) — er hat ein anderes Schema; [Page](page.md).

## Surfaces
stdout bei `--json`, sonst eine Kompaktzeile. Gelesen von aufrufenden Agenten und CI-Logiken; `--strict` wertet `data.summary.total_critical_issues` aus.

## See
[scripts/README.md](../../../scripts/README.md). [Änderungsrouting](../effects/CONTEXT.md).