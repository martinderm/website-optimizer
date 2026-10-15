---
type: process
universe: live
status: verified
entity: scripts/wo/capabilities/compare/audit.py
verified_at: 2026-10-15
revision: a2dda236b34e6222be84c6068d84203f340219a8
consumes:
  - ../objects/audit-report.md
  - ../objects/receipt.md
produces:
  - ../objects/audit-report.md
---

# Baseline-Vergleich

## Input → Movement → Output

**Input:** zwei Läufe desselben Workspace und derselben Domain, die mindestens eine
Capability gemeinsam haben.

**Movement:** beide Laufordner werden gelesen und nach Capability geordnet. Für jede
gemeinsame Capability werden die Befundmengen über `(rule_id, subject)` verglichen
und jede Differenz einem Grund zugeordnet — Regression, Verbesserung,
Prüfänderung oder Änderung der Site.

**Output:** `comparison.json` in einem **eigenen** neuen Laufordner, mit Receipt.
Die verglichenen Läufe bleiben unverändert.

## Why this shape
**Nie verweigern, immer begründen.** Der naheliegende Entwurf wäre, bei
abweichender `source_version` gar nicht zu vergleichen. Das taugt nicht: die
Werkzeugversion ändert sich bei jedem Release, also würde genau dann nicht
verglichen, wenn man es braucht. Eine Abweichung der Provenienz ist deshalb eine
*Angabe zum Vergleich*, kein Filter.

Die Prüfänderung ist der eigentliche Grund für die Klassifikation. Ohne die
Menge der gelaufenen Regeln ist „neue Regel ergänzt" nicht von „Seite kaputt"
zu unterscheiden — und genau diese Verwechslung macht ein Vergleichstool
unbrauchbar.

## Die vier Klassen

| Klasse | Bedingung |
|---|---|
| `regression` | `critical` neu, oder Schweregrad verschlechtert |
| `improvement` | Befund verschwunden, Regel existiert weiterhin |
| `check-change` | `rule_id` nur in einer der beiden Regelmengen |
| `site-change` | gleiche Regeln, Befund hinzugekommen oder weg mit gesunkener Schwere |

Eine Baseline **ohne** `rules_run` fällt bewusst auf die Schweregrad-Regel
zurück: „Prüfänderung" zu raten würde jede echte Regression gegen einen älteren
Lauf verschlucken.

## Steps

1. `run` bestimmt den aktuellen Lauf zuerst und sucht die Baseline dahinter.
   Umgekehrt aufgelöst vergleicht ein Lauf mit sich selbst.
   — [scripts/wo/capabilities/compare/audit.py](../../../scripts/wo/capabilities/compare/audit.py)
2. `pick_baseline` überspringt Läufe ohne gemeinsame Capability — Capabilities
   laufen nicht alle bei jedem Durchlauf.
   — `scripts/wo/capabilities/compare/audit.py`
3. `_reports_by_capability` erkennt ältere Reports ohne `capability`-Feld über
   `source.kind` und Befunde ohne `subject` über das frühere `page`.
   — `scripts/wo/capabilities/compare/audit.py`
4. `classify` attribuiert jede Differenz; Regressionen werden zusätzlich als
   Befunde ausgegeben, damit `--strict` unverändert funktioniert.
   — `scripts/wo/capabilities/compare/audit.py`
5. Das Ergebnis wird als `comparison.json` in einem neuen Laufordner abgelegt.
   — [scripts/wo/report.py](../../../scripts/wo/report.py) (`write_run`)

## If you change this
- **Hits:** [Audit-Report](../objects/audit-report.md) (`rules_run` und `capability` sind Voraussetzung), [CLI](../objects/cli.md) (`--baseline`/`--current`, `META`), [Quality](../objects/quality.md), `references/`-Regeltexte, wenn `CHECKS` je Capability sich ändert.
- **Does not hit:** [On-Page](../objects/on-page.md) und [Redirects](../objects/redirects.md) — sie erzeugen die Eingaben, werden aber nicht geändert; [Page](../objects/page.md); [Receipt](../objects/receipt.md), sofern sich die Zonenmetadaten nicht ändern.

## Surfaces
Kommandozeile: `wo.py compare [--baseline RUN] [--current RUN]`. Schreibt in die
Evidence-Zone des Workspace.

## See
[capabilities/compare/README.md](../../../scripts/wo/capabilities/compare/README.md). Entscheidung D25 in [decision-log.md](../../../decision-log.md).