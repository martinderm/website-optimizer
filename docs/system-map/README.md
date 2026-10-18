# website-optimizer — System-Map

ICM Form 6; Karte des Werkzeug-Subsystems. Einstieg für Änderungen, keine zweite Spezifikation. Die Regeln selbst stehen in `references/`, nicht hier.

| Frage | Karte |
| :--- | :--- |
| Arbeitsregeln, Router, Ein-Homes-pro-Fakt, Phasenstatus | [Skill-Verhalten](objects/skill-behavior.md) |
| Was jedes Kommando zurückgibt | [Envelope](objects/envelope.md) |
| Befund- und Report-Form | [Audit-Report](objects/audit-report.md) |
| Daten-Zonen-Receipt eines Laufs | [Receipt](objects/receipt.md) |
| TOML-Konfiguration, portable und lokale Ebene | [Site-Config](objects/site-config.md) |
| Was aus HTML extrahiert wird — und was nicht | [Page](objects/page.md) |
| Die zehn On-Page-Regeln | [On-Page](objects/on-page.md) |
| Live-Prüfung der Redirect-Regeln | [Redirects](objects/redirects.md) |
| Bildauslieferung, Dimensionen, Formate, Icons | [Images](objects/images.md) |
| JSON-LD-Struktur und Vollständigkeit | [Schema](objects/schema.md) |
| Interner Linkgraph: kaputte Ziele, unerreichbare Seiten, Tiefe | [Links](objects/links.md) |
| robots.txt, Sitemap, llms.txt — statisch oder live | [Crawler-Files](objects/crawler-files.md) |
| Gewicht, Render-Blocker, Fonts, Preloads, Dritthersteller — nur Build | [Performance](objects/performance.md) |
| Wie eine URL und ein Build-Dateiname einander benennen | [URLs](objects/urls.md) |
| Live-Rendering im Browser, Consent-Wall-Erkennung | [Crawl](objects/crawl.md) |
| Woher die Seiten eines Laufs kommen — statisch oder live | [Page-Set](objects/page-set.md) |
| Regelwerk, Quellen, Verbindlichkeit | [Referenzsatz](objects/reference-set.md) |
| Tests, Parität gegen das Vorgängerskript | [Qualität](objects/quality.md) |
| Tatsächliche Abläufe | [Prozesse](processes/CONTEXT.md) |
| Was trifft eine Änderung? | [Auswirkungen](effects/CONTEXT.md) |

**Namensfallen.** `references/` im Skill ist *nicht* die Data-Zone `memory/references/` im konsumierenden Workspace: die erste ist portable Methode, die zweite verbindliche Tatsache über eine Site. Ein *Run* ist ein Lauf mit eigenem Ordner, nicht ein Zeiger auf den letzten Lauf. `on-page` ist der Kommandoname, `on_page` der Modulname — ein Bindestrich ist kein gültiger Python-Bezeichner. `evidence`/`references`/`data` sind Zonen mit verschiedenen Trust-Stufen, `data/` ist überhaupt keine Zone. `subject` in einem Befund ist eine Seite bei `on-page` und eine Quell-URL bei `redirects` — und bei [Links](objects/links.md) je nach Regel beides: die fehlende URL bei `link.target_missing`, die Seite bei den beiden Graphregeln. Bei [Crawler-Files](objects/crawler-files.md) ebenso: die Sitemap-URL wie sie in der Datei steht bei `sitemap.unsupported_url`, die Seite bei `sitemap.absent_page`. Ein Sitemap-Eintrag hat genau eine Schreibweise, ein Link kann mehrere haben — daher dort die aufgelöste Form, hier die rohe. `links` kennt `--live` am Kommando und führt ihn nicht aus; `performance` kennt ihn und führt ihn nicht aus: Dateigrößen gibt es nur im Build; `crawler-files` führt ihn aus und lässt dafür zwei Regeln aus `rules_run` fallen. `live` bei `crawl_mode` heißt *nicht aus einem Build gelesen*. Bei `on-page --live`, [Images](objects/images.md) und [Schema](objects/schema.md) sind dafür Seiten gerendert; bei [Redirects](objects/redirects.md) ist eine Weiterleitung von Natur aus eine Netzbeobachtung; bei [Crawler-Files](objects/crawler-files.md) werden drei Dokumente geholt und keine Seite gerendert. Alle tragen `live`, weil keiner von ihnen dasselbe ist wie ein statischer Lauf.

Lade [CONTEXT.md](CONTEXT.md) und nur die zum Auftrag passende Karte. Metadatenregeln: [_meta/schema.md](_meta/schema.md).