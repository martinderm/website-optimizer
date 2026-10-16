---
type: object
cluster: logic
universe: live
status: verified
entity: scripts/wo/capabilities/images/audit.py
verified_at: 2026-10-15
revision: a2dda236b34e6222be84c6068d84203f340219a8
---

# Images

Bildauslieferung, Dimensionen, Formate und Icons — über das Build-Verzeichnis,
nicht über eine einzelne Seite.

## Why this shape
Die Hälfte der Befunde ist nur siteweit sichtbar: ein Icon, das auf jeder Seite
deklariert, aber vom Build nie erzeugt wurde, sieht man in keiner Einzelansicht.
Diese Capability liest deshalb das Verzeichnis.

Und sie hat eine **Grenze**, die wichtiger ist als ihre Regeln: die `alt`-Prüfung
gehört `on-page` und wird nicht wiederholt. Ein Defekt mit zwei `rule_id`s, zwei
Schweregraden und zwei Wohnorten ist genau der Fehler, den dieses Projekt
beseitigen soll. Gelesen wird von `alt` nur Anwesenheit und Länge; der Wert
selbst ist redaktionelle Prosa und in einem Report nutzlos.

## Shape
`scripts/wo/capabilities/images/audit.py` — `RULES` (sechs Regeln je Bild),
`icons_declared`, `icon_files_present` (braucht das Verzeichnis),
`og_image_absolute`.

Regeln: `image.src_missing`, `image.dimensions_missing` (critical),
`icon.file_missing` (critical), `video.poster_file_missing` (critical),
`image.srcset_missing`, `image.sizes_missing`, `image.format_legacy`,
`image.loading_unset`, `image.loading_partial`, `image.og_relative`,
`icon.none_declared`, `video.poster_missing`, `video.preload_unset` (je warning).

**Die Video-Regeln wohnen hier, weil der Mechanismus derselbe ist:** etwas im
Markup Deklariertes wird gegen das geprüft, was der Build erzeugt hat.
`video.poster_file_missing` ist `icon.file_missing` einen Elementtyp weiter, und
für zwei Regeln entsteht kein dritter Ordner. Untertitel werden bewusst **nicht**
geprüft: die Anwesenheit eines `<track>` wäre leicht zu messen, ihre Richtigkeit
braucht einen Menschen, und ein sauber gemeldetes Video läse sich als geprüft.

`width="100%"` zählt nicht als Dimension: nur eine Zahl reserviert Platz.

**Ein `<img>` ohne `src` wird einmal gemeldet, nicht dreimal** (D31). Nichts wird
geladen, also reserviert es keinen Platz und passt sich nichts an. Auf der
Referenzseite waren das 140 der 469 kritischen Befunde — dieselbe Lightbox-
Vorlage, drei Rule-Treffer pro Element. Bei 37 davon ist das Attribut *leer*
statt abwesend: `<img src alt>` parst zu `src=""`, löst gegen das Dokument auf,
und der Browser stellt tatsächlich eine Anfrage nach der Seite selbst als Bild.

**Beide `loading`-Regeln melden einmal pro Seite, nicht pro Bild** — eine Site,
die nichts lazy lädt, hat ein Problem, nicht zweihundert. Der Unterschied
zwischen ihnen ist die Aussage: `loading_unset` heißt *kein* Bild deklariert eine
Strategie, das ist an jedem ein Defekt. `loading_partial` heißt *manche tun es*,
und das ist eine **offene Frage, kein Urteil** (D40): das Hero-Bild ist vermutlich
absichtlich eager, ob die anderen lazy-Kandidaten sind, weiß man statisch nicht.
Vor dieser Regel blieben 121 Seiten der Referenzseite und 26 von 29 einer
WordPress-Seite still — darunter eine mit 42 OpenStreetMap-Kacheln, die der
Browser alle sofort lädt. Stille las sich als sauber.

`icon.file_missing` fällt im Live-Modus aus `rules_run` heraus: ein Crawl hat kein
Build-Verzeichnis, in dem die Datei liegen könnte, und eine Regel, die nicht laufen
kann, darf nicht als eine gemeldet werden, die nichts fand.

- [scripts/wo/capabilities/images/audit.py](../../../scripts/wo/capabilities/images/audit.py)

## Connected to
Gehört zu [Page](../objects/page.md) (liefert `images[]` und `icons[]`),
[Audit-Report](../objects/audit-report.md), [On-Page](../objects/on-page.md).
**Looks like but is not:** `on-page` besitzt den `alt`-Defekt. Diese Karte
besitzt die Auslieferung.

## If you change this
- **Hits:** [Page](../objects/page.md) — jedes neue Bildfeld, das diese Regeln
  brauchen, wird dort extrahiert, und das berührt auch [On-Page](../objects/on-page.md);
  [Audit-Report](../objects/audit-report.md); [Quality](../objects/quality.md);
  [CLI](../objects/cli.md) (`REGISTRY`); `references/images.md`;
  `capabilities/images/README.md`.
- **Does not hit:** [Redirects](../objects/redirects.md); [Schema](../objects/schema.md);
  die `alt`-Regel in [On-Page](../objects/on-page.md) — die Grenze ist die Absicht.

## Surfaces
Aufgerufen über `wo.py images`. Liest ausschließlich das Build-Verzeichnis.

## See
[capabilities/images/README.md](../../../scripts/wo/capabilities/images/README.md). [Änderungsrouting](../effects/CONTEXT.md).