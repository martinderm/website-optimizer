# Änderungsauswirkungen — Routing

Inputs: Änderungsauftrag. Nicht den gesamten Baum laden; die Karten tragen die
Details.

| Änderung | Zuerst öffnen |
| :--- | :--- |
| Neue Capability hinzufügen | [CLI](../objects/cli.md), [On-Page](../objects/on-page.md) als Vorbild, [Qualität](../objects/quality.md) |
| Regel hinzufügen, ändern oder entfernen | [On-Page](../objects/on-page.md), [Referenzsatz](../objects/reference-set.md) — beide, Regeltext und Messung wandern synchron |
| Report-Struktur oder Schema ändern | [Audit-Report](../objects/audit-report.md), [Receipt](../objects/receipt.md) |
| Receipt-Felder, Klassifikation, Retention | [Receipt](../objects/receipt.md), [Site-Config](../objects/site-config.md) |
| Konfigurationsoptionen, Config-Ebenen | [Site-Config](../objects/site-config.md), [CLI](../objects/cli.md) |
| Extraktionsgrenze, neue Seitenfelder | [Page](../objects/page.md), [On-Page](../objects/on-page.md), [Qualität](../objects/quality.md) |
| Envelope-Felder, Zustände, Exit-Codes | [Envelope](../objects/envelope.md), [CLI](../objects/cli.md) |
| Neue Reference-Datei | [Referenzsatz](../objects/reference-set.md), [Skill-Verhalten](../objects/skill-behavior.md) für die Router-Zeile |
| `scripts/README.md`, `SKILL.md`, Katalogeintrag | [Skill-Verhalten](../objects/skill-behavior.md), [CLI](../objects/cli.md) |
| `tests/` erweitern | [Qualität](../objects/quality.md) |

**Process:** Hits/Does-not-hit der Karten gegen den konkreten Diff prüfen; Scope
und passende Tests ableiten. Skript, Rule-Text und Map im selben Arbeitsschritt
synchron halten — Kartierung, die hinter dem Code zurückbleibt, ist schlimmer als
keine Kartierung.

**Outputs:** Änderungsliste und synchron aktualisierte Karten. Offene Arbeit als
GitHub Issue.

**Human Check:** SKILL.md, Skriptverhalten und System-Map widersprechen sich
nicht; Quelllinks bleiben gültig.