---
type: object
cluster: logic
universe: live
status: verified
entity: scripts/wo/capabilities/crawler_files/audit.py
verified_at: 2026-10-16
revision: d54632c434fd18da884ed4b491c5c50141cb01a0
---

# Crawler-Files

Die drei Dokumente, die eine Site über sich selbst veröffentlicht: `robots.txt`,
die XML-Sitemap und `llms.txt`.

## Why this shape
Dateien, die niemand liest, bis seit Monaten etwas falsch ist: ein `Disallow: /`
aus einer nie aufgehobenen Staging-Sperre sieht aus wie eine gesunde Site, und eine
Sitemap, die still nicht mehr erzeugt wird, sieht aus wie eine Site ohne Inhalte.

**Zwei Quellen, ein Regelsatz.** Statisch sind es Dateien im Build, live sind es
drei URLs. Die Regeln darüber können das nicht unterscheiden — dieselbe Anordnung,
die `pages` den seitenlesenden Capabilities gibt (D33), hier auf Dokumente
angewandt.

**Anders als [Links](links.md) verweigert sie den Crawl nicht.** Ein `Disallow: /`
ist auf jeder Site ein Fund, auch ohne Build. Der Live-Lauf meldet deshalb
*weniger* statt nichts: `sitemap.absent_page` und `sitemap.unsupported_url`
verlassen `rules_run`, und damit ist für den Leser sichtbar, dass sie übersprungen
und nicht bestanden wurden (D55). Vier Dokumente werden geholt, kein Browser
gestartet.

**Aus einer unlesbaren Sitemap wird keine Deckung behauptet** (D56). Fehlt die
Sitemap, ist sie unlesbar oder leer, entfallen die beiden Deckungsregeln
vollständig — sonst machte eine Sitemap, die nicht parst, jede Seite der Site zu
einer fehlenden, hundertfach und jedes Mal plausibel. `checked_pages: 0` heißt
deshalb *keine Deckung behauptet*, nicht *keine Seiten geprüft*.

## Shape
`scripts/wo/capabilities/crawler_files/audit.py` — `groups` (robots.txt-Gruppen:
die Zugehörigkeit zu `User-agent: *` ist die ganze Aussage), `sitemap_directives`,
`locks_out_everyone`, `blocked_assets`, `read_sitemap`, `audit_sources`,
`active_checks`.

Regeln: `robots.blocks_site`, `sitemap.unreadable`, `sitemap.empty`,
`sitemap.unsupported_url` (critical); `robots.missing`, `robots.blocks_asset`,
`robots.sitemap_missing`, `sitemap.missing`, `sitemap.absent_page`, `llms.missing`,
`llms.empty` (warning).

`STATIC_ONLY` nennt die zwei Regeln, die einen Build brauchen; `active_checks()`
leitet daraus `rules_run` ab.

Die Sitemap-*Syntax* liegt in `scripts/wo/sitemaps.py` (`KNOWN_NAMES`,
`locs`, `is_index`), die URL-Schreibweisen in [URLs](urls.md). Beide wurden
extrahiert, als diese Capability der zweite Aufrufer wurde (D57); die
Steuerschleifen blieben getrennt, weil der Crawl „welche URLs rendere ich" fragt
und diese Capability „was listet die Sitemap, vollständig, und war es überhaupt
eine".

**Sitemap-Suche in der Reihenfolge von D37:** erst die `Sitemap:`-Zeile aus
robots.txt — die Site benennt ihre eigene Datei —, dann die bekannten Namen
(`/wp-sitemap.xml`, `/sitemap_index.xml`, `/sitemap.xml`, `/sitemap-index.xml`).
Ein Index wird verfolgt.

- [scripts/wo/capabilities/crawler_files/audit.py](../../../scripts/wo/capabilities/crawler_files/audit.py)

## Connected to
Gehört zu [URLs](urls.md), [Site-Config](site-config.md),
[Audit-Report](audit-report.md). Liest in beiden Modi dieselben drei Dokumente;
in [Audit-Live](../processes/audit-live.md) ohne Browser.

**Looks like but is not:** [On-Page](on-page.md) besitzt die `noindex`-Meta-Angabe
*einer Seite* — sie ist hier nur der Grund, eine Seite von `sitemap.absent_page`
auszunehmen.

## If you change this
- **Hits:** `references/indexing.md` und `references/llm-visibility.md` (Regeltexte);
  `capabilities/crawler_files/README.md`; [CLI](cli.md) (`REGISTRY`) und die
  Versionskopplung in [Audit-Report](audit-report.md) (D43); [URLs](urls.md) und
  `scripts/wo/sitemaps.py`, wenn sich Schreibweisen ändern.
- **Does not hit:** [Links](links.md) — die Capabilities teilen Syntax, nicht
  Schlüsse; [Redirects](redirects.md), [Images](images.md), [Schema](schema.md);
  [Receipt](receipt.md).

## Surfaces
Aufgerufen über `wo.py crawler-files`, mit `--live` gegen die Site statt gegen den
Build. Findungen erscheinen im Envelope und in `report.json`.

## See
[capabilities/crawler_files/README.md](../../../scripts/wo/capabilities/crawler_files/README.md).
Entscheidungen D55–D57 in [decision-log.md](../../../decision-log.md).
[Änderungsrouting](../effects/CONTEXT.md).
