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

Regeln: `image.dimensions_missing` (critical), `image.srcset_missing`,
`image.sizes_missing`, `image.format_legacy`, `image.loading_unset`,
`image.og_relative`, `icon.none_declared` (je warning),
`icon.file_missing` (critical).

`width="100%"` zählt nicht als Dimension: nur eine Zahl reserviert Platz.

`image.loading_unset` meldet **einmal pro Seite**, nicht pro Bild — eine Site,
die nichts lazy lädt, hat ein Problem, nicht zweihundert.

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