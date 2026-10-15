---
type: process
universe: ghost
status: stub
entity: (geplant, nicht implementiert)
verified_at: 2026-10-15
revision: a2dda236b34e6222be84c6068d84203f340219a8
consumes:
  - ../objects/audit-report.md
  - ../objects/receipt.md
produces:
  - ../objects/audit-report.md
---

# Baseline-Vergleich

**Ghost.** Diese Karte beschreibt eine Bewegung, die noch nicht existiert. Sie
ist hier, damit der geplante Vertrag feststeht und nicht später erfunden wird —
und damit niemand gegen sie implementiert, ohne sie zur `live` zu machen.

## Input → Movement → Output

**Input:** zwei Läufe desselben Workspace und derselben Domain; der spätere ist
der aktuelle, der frühere die Referenz.

**Movement:** beide Reports werden gegen das gemeinsame Schema validiert, ihre
Receipts werden auf vergleichbare Provenienz geprüft, und die Befundmengen werden
über `rule_id` + `page` verglichen. Jede Differenz wird als eigene
Vergleichsaussage ausgegeben, nicht als überschriebener Report.

**Output:** ein Vergleichsartefakt in einem neuen Laufordner. Der frühere Lauf
bleibt unverändert.

## Why this shape
Evidence ist append-only, also wird auch ein Vergleich als *eigener* Lauf
geschrieben und nicht durch Überschreiben des letzten erzeugt. Sonst wäre die
Historie, die `compare` erzeugen soll, genau die, die man dabei verliert.

## Offene Entscheidungen vor der Implementierung

- **Provenienz-Vergleich.** Ein Live-Crawl ist nicht deterministisch. Ohne
  Vergleich von `source_version` und `crawl_mode` meldet `compare` Unterschiede,
  die nie Änderungen an der Site waren. Ohne Vergleich meldet es wiederum echte
  Änderungen nicht. Diese Karte bleibt `stub`, bis die Regel feststeht.
- **Eignungsregel.** Welche Differenzen zählen als Regression? Ein neu
  aufgetretener `critical`-Befund sicher; eine entfernte `warning` sollte kein
  Feiergrund im Report sein.
- **Erfolgsfall.** Was passiert, wenn keine einzige Referenz existiert? Vorgeschlagen: Vergleich überspringen und im Envelope als `Partial` mit Begründung melden, nicht als Erfolg.

## If you change this
- **Hits:** [Audit-Report](../objects/audit-report.md) (Vergleichsschlüssel), [Receipt](../objects/receipt.md) (Provenienzfelder), [CLI](../objects/cli.md) (neues Kommando), [Qualität](../objects/quality.md).
- **Does not hit:** [On-Page](../objects/on-page.md), [Page](../objects/page.md) — der Vergleich prüft Ergebnisse, er misst nicht neu.

## Surfaces
Noch keine. Geplanter Einstieg: `wo.py compare --against <run-id>`.

## See
[PLAN.md](../../../PLAN.md) §4.2 und Runde 4.