---
type: object
cluster: logic
universe: live
status: verified
entity: scripts/wo/capabilities/performance/audit.py
verified_at: 2026-10-18
revision: 862727dc7f40cf727b30c352d142924540f01b1d
---

# Performance

Was der Build wiegt und was sein erstes Paint blockiert: Gewicht pro Seite
gegen die Budgets aus `performance.md`, parser-blockierende Skripte,
`@font-face` ohne `font-display`, Preloads ins Leere und die fremden Origins,
die das Markup referenziert.

## Why this shape
Die Referenz war die einzige, deren Thema im Mission Statement steht und hinter
der keine einzige Regel lag (Issue #7). Die Arbeit war die Trennung, nicht der
Umfang: Die eine Hälfte — Gewicht, Blockade, Fonts, Preload-Ziele,
Dritthersteller — liegt im Build und ist messbar; die andere — LCP/INP/CLS
selbst, Caching-Header — braucht Labor oder Feld und bleibt Beratung, bis ein
Workspace eine vertrauenswürdige Quelle mitbringt.

Sie ist eine eigene Capability und keine Erweiterung von [Images](images.md).
`images` prüft *Auslieferung einzelner Dateien* (Formate, Dimensionen,
Existenz); Gewicht ist eine *Summe über Verweise*, Blockade eine *Eigenschaft
der Einbindung*. Beides dort hineinzulegen hieße, die Capability mit Regeln zu
beladen, die ihre eigene Definition ausschließt — dieselbe Begründung wie D51
bei [Links](links.md), eine Ebene tiefer.

**Statisch, und sie verweigert den Crawl.** Dateigrößen gibt es nur im Build.
Ein Crawl müsste jedes gemeinsame Stylesheet schätzen und jede Dateigröße
approximieren — D32 mit einer Waage dahinter. `run(live=True)` wirft deshalb,
statt Null zu melden.

## Shape
`scripts/wo/capabilities/performance/audit.py` — `_resolve` (löst eine URL
gegen die Seite auf, die sie nennt; relativ heißt relativ zum Seitenverzeichnis,
wie der Browser es sieht), `_font_files` (`url()` im Stylesheet ist relativ
zum Stylesheet, nicht zur Seite), `budget_findings`, `blocking_scripts`,
`font_display_files`, `preload_targets`, `third_party_origins`, `audit_pages`,
`to_report`, `CHECKS`. Dateischreibweisen und Host-Vergleich kommen aus
[URLs](urls.md) — `served()`, `key()`, `path_of()`, `bare_host()`; ein
URL-Satz, vier Verbraucher.

Regeln: `perf.budget_exceeded` (warning), `perf.render_blocking_script`
(warning), `perf.font_display_missing` (warning), `perf.preload_target_missing`
(critical), `perf.third_party_origin` (warning). Budgets: CSS 100 KB, JS
200 KB, größtes Bild 200 KB, Font 100 KB pro Datei — Bytes auf Platte, gegen
die Arbeitswerte aus `references/performance.md`.

**Gewicht ist pro Datei aggregiert, nicht pro Seite geflutet** (D52). Ein 150 KB
gemeinsames Stylesheet in 100 Seiten ist ein Befund mit Seitenzahl, nicht 100
Befunde. Nur wenn kein einzelnes File über dem Budget liegt, die Summe aber
schon, meldet die Seite ihre Komposition — dann fügt die Summe Information
hinzu, statt sie zu wiederholen. Das größte Bild pro Seite bleibt ein
Seitenbefund: Bilder sind selten Templates, und „größtes gegen
Hero-Budget" ist konservativ gelesen (darunter ist jedes Bild leicht, darüber
hat die Seite ein Gewichtsproblem, egal welches Bild heroisch ist).

**Was als fremd gilt, entscheidet `bare_host`.** Gleicher Host mit oder ohne
`www` ist eine Site (D38); eine Subdomain wird gemeldet, weil das Markup nicht
zeigt, ob sie eigenes CDN oder fremder CNAME ist. Die Meldung behauptet
deshalb keine fremde Infrastruktur, sondern verlangt Benennung und
Begründung — die Hälfte der Referenzforderung, die ein Werkzeug leisten kann.

**Fehlende Dateien wiegen nichts.** Ein deklarierter Pfad, den der Build nicht
enthält, ist der Befund von [Links](links.md) oder [Images](images.md). Diese
Regeln überspringen ihn: Eine 404 liest sich hier nie als leichtgewichtig, und
Gewicht wird nie negativ. Die 404-Seite selbst ist ausgenommen — sie ist keine
Ansicht.

- [scripts/wo/capabilities/performance/audit.py](../../../scripts/wo/capabilities/performance/audit.py)

## Connected to
Gehört zu [Page](page.md) (liefert `scripts[]`, `stylesheets[]`, `preloads[]`,
`iframes[]`), [URLs](urls.md) (Auflösung und Schreibweisen), [Audit-Report](audit-report.md).
Prozess: nur [Audit-Statisch](../processes/audit-static.md) —
[Audit-Live](../processes/audit-live.md) endet hier in einer Verweigerung, und
das ist die Absicht.
**Looks like but is not:** [Images](images.md) prüft, *ob* Dateien da sind und
welches Format sie haben; diese Karte prüft, *was sie wiegen* und *wann sie
laden*. Ein vorhandenes Bild kann hier zu schwer und ein leichtes dort
falsch formatiert sein — zwei Fragen, zwei Karten.

## If you change this
- **Hits:** [Page](page.md) — ein neues Lieferfeld wird dort extrahiert und berührt
  damit auch [On-Page](on-page.md) und [Quality](quality.md);
  `references/performance.md` (Abdeckung der Checkliste);
  `capabilities/performance/README.md`;
  [CLI](cli.md) (`REGISTRY`) und die Versionskopplung in [Audit-Report](audit-report.md)
  (`rules_run` ändert sich → `TOOL_VERSION`, D43).
- **Does not hit:** [Redirects](redirects.md); [Schema](schema.md);
  [Links](links.md); [Crawler-Files](crawler-files.md); [Receipt](receipt.md);
  [Crawl](crawl.md) — der Live-Pfad wird von hier aus verweigert, nicht verändert.

## Surfaces
Aufgerufen über `wo.py performance`. Liest ausschließlich das Build-Verzeichnis
(Dateigrößen via `stat`); kein Netzwerkzugriff. Findungen erscheinen im
Envelope und in `report.json`.

## See
[capabilities/performance/README.md](../../../scripts/wo/capabilities/performance/README.md).
Entscheidung D60 in [decision-log.md](../../../decision-log.md).
[Änderungsrouting](../effects/CONTEXT.md).
