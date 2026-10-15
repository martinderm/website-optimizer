---
type: object
cluster: interface
universe: live
status: verified
entity: scripts/wo/page.py
verified_at: 2026-10-15
revision: a2dda236b34e6222be84c6068d84203f340219a8
---

# Page

Die Felder, die aus einer HTML-Seite gewonnen werden dürfen — und der Ort, an dem
festgelegt ist, was *nicht* gewonnen wird.

## Why this shape
Der Skill auditiert fremde Webseiten. Jede gecrawlte Seite ist kontrollierter
Inhalt und damit eine Injection-Fläche (Entscheidung D13). Die Antwort darauf ist
eine Extraktionsgrenze, keine Filterliste: `Page` hat kein Attribut für
Fließtext, Kommentare oder Seiteninhalt. `_Extractor.handle_data` hat genau zwei
Senken — `<title>` und JSON-LD. Alles andere fällt weg, bevor es existiert.

Zusätzlich trennt die Trennung Messung von Urteil: eine Regel sieht nur diese
Felder, nie eine Aussage über die Seite (D15).

## Shape
`scripts/wo/page.py:25` `class Page` — Felder: `source`, `is_404`, `title`, `title_found`, `lang`, `description`, `canonical`, `robots`, `og`, `twitter`, `h1_count`, `has_main`, `has_skip_link`, `images_total`, `images_missing_alt`, `schemas`, plus `description_length`. `:149` `extract_page()`, `:162` `iter_html_files()`.

`schemas` sammelt jeden `@type` auch aus innerhalb von `@graph`
(`_collect_types`). Fehlerhaftes JSON-LD wird stillschweigend übersprungen —
ein Syntaxfehler ist ein Seitendefekt, kein Crash, und wird von der
Schema-Capability gemeldet, sobald sie existiert.

- [scripts/wo/page.py](../../../scripts/wo/page.py) — `:25` (Page), `:149` (extract_page), `:162` (iter_html_files)

## Connected to
Gehört zu [On-Page](on-page.md). Prozess: [Audit-Statisch](../processes/audit-static.md).
**Looks like but is not:** `Page` ist keine Website-Record-Karte im Workspace und keine `memory/references/`-Zone. Es ist ein Laufzeit-Objekt eines Audits.

## If you change this
- **Hits:** [On-Page](on-page.md) — jede Regel liest aus diesen Feldern; [Audit-Report](audit-report.md) — `pages[]` wird hieraus befüllt; Paritätstest in [Qualität](quality.md), weil Feldnamen und Extraktionsgrenzen die Befunde verändern.
- **Does not hit:** [Receipt](receipt.md); die Regel*texte* in `references/*` beschreiben, was korrekt ist, nicht wie gemessen wird; [Envelope](envelope.md).

## Surfaces
Wird von [On-Page](on-page.md) gelesen. Interne Implementierungsgrenze: kein externes Modul importiert `Page` direkt.

## See
Quellmodul: [scripts/wo/page.py](../../../scripts/wo/page.py). Entscheidung D13 in [decision-log.md](../../../decision-log.md).