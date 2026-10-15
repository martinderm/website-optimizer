---
type: object
cluster: logic
universe: live
status: verified
entity: scripts/wo/capabilities/schema/audit.py
verified_at: 2026-10-15
revision: a2dda236b34e6222be84c6068d84203f340219a8
---

# Schema

JSON-LD-Struktur und Vollständigkeit. **Keine** Vokabularvalidierung.

## Why this shape
Die Grenze ist hier die Architekturentscheidung (D28). Das Vokabular von
schema.org sind Zehntausende Terme mit Klassen-Hierarchien; es zu laden machte
eine Build-Verzeichnis-Prüfung netzabhängig, und eine lokale Kopie wäre eine
zweite Wahrheit, die still altert. Der Report verweist stattdessen im eigenen
`references`-Block auf Validator und Rich Results Test.

Der Fehler, den das Werkzeug tatsächlich findet, ist lokal entscheidbar: ein
Block, der nicht parst; ein `@type`, das behauptet, aber nicht gefüllt ist; ein
`@id`, das sich widerspricht.

## Shape
`scripts/wo/capabilities/schema/audit.py` — `iter_blocks` (RegEx, weil der
Rohblock gebraucht wird), `_nodes` (steigt in `@graph` ab), `_audit_node`
(Pflichtfelder je Typ), `_duplicate_identifiers` (vergleicht **Inhalte**),
`_audit_site` (Identitäts-Typ siteweit).

Regeln: `schema.none`, `schema.block_no_types`, `schema.context_missing`,
`schema.identity_missing` (je warning); `schema.block_empty`,
`schema.block_invalid_json`, `schema.required_field_missing`,
`schema.identifier_conflicting` (je critical).

`REQUIRED_FIELDS` ist eine Tabelle dessen, ohne was ein Typ nicht arbeiten kann —
keine Vollständigkeitsrubrik. Unbekannte Typen werden nicht bemängelt.

- [scripts/wo/capabilities/schema/audit.py](../../../scripts/wo/capabilities/schema/audit.py)

## Zwei Erfahrungen, die die Karte festhält

**Derselbe `@id` auf jeder Seite ist korrekt.** Ein siteweiter `@graph` gibt den
`Person`- und `WebSite`-Knoten in jeden Head — genau das macht sie auflösbar.
`_duplicate_identifiers` vergleicht deshalb Inhalte: 173 identische Kopien sind
still, zwei widersprüchliche sind `critical`. Die erste Fassung meldete 173
identische Definitionen als Fehler, also exakt das Richtige als falsch.

**Unquotiete Attribute werden gefunden.** Minifizierter Generator-Output liefert
`<script type=application/ld+json>`. Quoten zu verlangen ließ eine vollständig
markierte Site als „keine strukturierten Daten" melden — 173 Warnungen statt
null. Ein selbstbewusster, falscher „clean" ist die schlechteste Fehlerform.

## Connected to
Gehört zu [Page](../objects/page.md) (`schemas[]`), [Audit-Report](../objects/audit-report.md),
[On-Page](../objects/on-page.md) (dessen Extraktion findet die Blöcke, diese
Capability prüft sie).
**Looks like but is not:** [Images](../objects/images.md) liest dasselbe
Verzeichnis und hat dieselbe Vakuumgrenze gegen `on-page`.

## If you change this
- **Hits:** [Page](../objects/page.md) (JSON-LD-Extraktion), [Audit-Report](../objects/audit-report.md) (`references`-Block im Schema), [Quality](../objects/quality.md), [CLI](../objects/cli.md) (`REGISTRY`), `references/structured-data.md`, `capabilities/schema/README.md`.
- **Does not hit:** [Redirects](../objects/redirects.md); [Images](../objects/images.md); die Vokabular-Validierung selbst — die liegt absichtlich extern.

## Surfaces
Aufgerufen über `wo.py schema`. Liest ausschließlich das Build-Verzeichnis, kein
Netzwerk.

## See
[capabilities/schema/README.md](../../../scripts/wo/capabilities/schema/README.md). Entscheidung D28 in [decision-log.md](../../../decision-log.md).