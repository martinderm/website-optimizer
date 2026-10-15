---
type: object
cluster: knowledge
universe: live
status: verified
entity: references/
verified_at: 2026-10-15
revision: a2dda236b34e6222be84c6068d84203f340219a8
---

# Referenzsatz

Die Regeln, ihre Herkunft und ihre Verbindlichkeit.

## Why this shape
Nicht die Existenz von Regeln ist das Problem, sondern ihre Gewichtung: ein Agent,
der „cornerstone content ist wichtig" liest, kann nicht unterscheiden, ob er
einen Fehler behebt oder eine legitime Entscheidung trifft. Deshalb trägt jede
Datei `evidence_level`, `support_level` und Quellenanker im Front Matter.

Entscheidend war D14: dafür wurde **keine** eigene Klassifikation erfunden.
`spec`/`practice`/`observed` wären ein zweites Vokabular neben den bestehenden
Achsen Zone, `evidence_level`, `trust_level` und `support_level`.

`sources.md` unterscheidet `consulted` von `inherited`. Zum Schreiben dieses
Satzes wurde keine externe Quelle abgerufen; die Anker stammen aus
`hugo-wizard`-Chore-Dokumenten, die sie zitiert hatten. Ein `inherited`-Anker ist
eine Spur, keine Verifikation — das steht so im Log, statt eine Lesefreigabe zu
behaupten, die es nicht gibt.

## Shape
Dreizehn Dateien, ein Thema pro Datei: `seo-core`, `indexing`, `internal-linking`,
`redirects`, `structured-data`, `images`, `video`, `performance`,
`accessibility`, `llm-visibility`, `static-sites`, `dynamic-sites`, `sources`.

Der Plattform-Split ist absichtlich eng: nur `static-sites.md` und
`dynamic-sites.md` unterscheiden sich nach Plattform. Alles andere ist neutral,
weil nur die *Handlung* abweicht — Build-Ausgabe gegen gerenderte Seite,
Plugin-Mechanik gegen Template.

Router: `SKILL.md`, eine Zeile pro Frage, ohne Inhalt. Das ist der Vertrag: wer
eine Regel im Router lesen muss, um sie anzuwenden, hat sie an die falsche Stelle
gelegt.

- [references/sources.md](../../../references/sources.md) — Provenienz-Spalten
- [SKILL.md](../../../SKILL.md) — Router-Tabelle

## Connected to
Gehört zu [Skill-Verhalten](skill-behavior.md) (Router, Ein-Homes-Regel). [On-Page](on-page.md) setzt Teile davon technisch um; die Karte dort weist ausdrücklich auf die Trennung hin.

## If you change this
- **Hits:** [Skill-Verhalten](skill-behavior.md) und der Router in `SKILL.md`; [On-Page](on-page.md), wenn eine Regel Text ändert; die Stubs in `hugo-wizard/memory/references/chores/`, deren Verweise dann auf die neue Fundstelle zeigen.
- **Does not hit:** [Page](page.md), [Audit-Report](audit-report.md), [Receipt](receipt.md), [Envelope](envelope.md) — Mess- und Transportverträge sind von der Regelform unabhängig.

## Surfaces
Gelesen von Agenten vor Maßnahmen. Geschrieben von Menschen mit Quellenangabe;
eine Regel ohne Quelle wird nicht aufgenommen.

## See
[SKILL.md](../../../SKILL.md). [decision-log.md](../../../decision-log.md) D14. [Änderungsrouting](../effects/CONTEXT.md).