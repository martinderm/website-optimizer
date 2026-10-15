---
type: object
cluster: interface
universe: live
status: verified
entity: scripts/wo/pages.py
verified_at: 2026-10-15
revision: 8450d5b
---

# Page-Set

Die eine Stelle, an der entschieden wird, woher die Seiten eines Laufs kommen —
und die deshalb der Grund ist, warum keine Capability einen `--live`-Zweig hat.

## Why this shape
Ein doppelter Codepfad ist eine Gelegenheit, dass die beiden Versionen
auseinanderlaufen, und die Abweichung fällt erst auf, wenn dieselbe Seite je nach
Auditart andere Befunde für denselben Defekt liefert. `resolve()` gibt
`Page`-Objekte zurück, und die Regeln darüber können nicht unterscheiden, ob sie
vom Dateisystem oder aus einem Browser stammen (D33).

Verifiziert an 25 echten Seiten, statisch gegen live, Seite für Seite und
Capability für Capability: identisch, in beide Richtungen.

## Shape
`scripts/wo/pages.py` — `resolve(config, live, run)` liefert ein `PageSet` mit
`pages`, `mode`, `source`, `crawl`, `ignored` und `raw`. `_resolve_static()` liest
das Build-Verzeichnis, `_resolve_live()` ruft [Crawl](crawl.md).

`raw` trägt gerendertes Markup, nur im Live-Fall. Die meisten Regeln brauchen nur
die extrahierten Felder; `schema` braucht das Dokument selbst, weil JSON-LD
eine Datei ist und keine Liste von Typnamen. Es liegt bewusst *nicht* in
[Page](page.md) — dort gilt D13, kein Seitenprosa.

## Connected to
Gehört zu [Crawl](crawl.md). Prozess: [Audit-Statisch](../processes/audit-static.md), [Audit-Live](../processes/audit-live.md).
**Looks like but is not:** `PageSet` ist kein Report-Schema und keine
Zwischenablage auf Platte. Es existiert nur während eines Laufs.

## If you change this
- **Hits:** [On-Page](on-page.md), [Images](images.md), [Schema](schema.md) — alle drei beziehen ihre Seiten hier; [CLI](cli.md) — `--live`; [Audit-Report](audit-report.md) — `source` und `crawl` kommen von hier.
- **Does not hit:** [Redirects](redirects.md) — kennt den Resolver nicht; [Receipt](receipt.md); die Referenztexte, die beschreiben, was korrekt ist, nicht woher die Seite stammt.

## Surfaces
Keine. Interne Grenze zwischen dem Entry Point und den Capabilities.

## See
Quellmodul: [scripts/wo/pages.py](../../../scripts/wo/pages.py). D32, D33 in [decision-log.md](../../../decision-log.md).