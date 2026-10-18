---
type: object
cluster: logic
universe: live
status: verified
entity: scripts/wo/capabilities/links/audit.py
verified_at: 2026-10-18
revision: 48adff4e0cb25e4eab644ac31a40d3d638a3ce75
---

# Links

Der interne Linkgraph einer gebauten Site: Links auf URLs, die der Build nicht
ausliefert, Seiten, die von der Startseite aus nichts erreicht, und die Tiefe der
Site.

## Why this shape
Ein Link ist eine *Relation zwischen zwei Seiten*. Keine Einzelansicht kann sie
sehen, deshalb liest diese Capability das Build-Verzeichnis — dieselbe Begründung
wie bei [Images](images.md), nur eine Ebene höher: dort ging es um Dateien, die
es geben muss, hier um Seiten, die erreichbar sein müssen.

Sie ist eine eigene Capability und keine Erweiterung von [On-Page](on-page.md).
`on-page` ist als *die Signale innerhalb einer einzelnen Seite* definiert; jede
seiner Regeln ist eine Funktion einer Seite. Eine Graphregel dort hineinzulegen
hieße, die Capability mit Regeln zu beladen, die ihre eigene Definition
ausschließt (D51).

**Statisch, und sie verweigert den Crawl.** Ein Graph braucht jede URL, die die
Site ausliefert. Ein Crawl sieht nur die Seiten innerhalb seines Limits; alles
darüber läse sich als unerreichbar und jeder Link dorthin als kaputt. Das
Ergebnis wäre selbstsicher und falsch — die Form, die D32 benennt. `run(live=True)`
wirft deshalb, statt Null zu melden.

## Shape
`scripts/wo/capabilities/links/audit.py` — `target_of` (löst ein `href` gegen die
Seite auf, die es hält), `audit_pages`, `_page_alias_map`, `_distances` (BFS ab
`/`), `CHECKS`. Die URL-Schreibweisen selbst liegen in
[URLs](urls.md) — `served()` und `page_urls()` werden von `crawler-files`
mitbenutzt, und genau deshalb stehen sie an einer Stelle.

Regeln: `link.target_missing` (critical), `link.unreachable` und `link.depth`
(je warning). `DEPTH_LIMIT` ist 4 — die Distanz, ab der
[internal-linking.md](../../../references/internal-linking.md) von dünnerem Crawl
spricht.

**Ein fehlendes Ziel ist ein Befund, nicht einer pro verlinkender Seite** (D52).
`subject` ist dort die **URL**, die fehlt, und die Meldung nennt die Seiten, die
auf sie zeigen. In einem siteweiten Template wäre ein kaputter `href` sonst 173
identische kritische Befunde für eine Zeile, die man einmal repariert — D38 mit
einer Vorlage dahinter. Bei den beiden Graphregeln bleibt `subject` die Seite,
denn dort *ist* die Seite der Gegenstand.

**Erreichbarkeit ist transitiv.** `link.unreachable` ist ein Breitendurchlauf ab
`/`, keine Zählung eingehender Links: eine Seite, die nur von einer anderen
unerreichbaren Seite verlinkt wird, ist unerreichbar. Genau das heißt „nur über
die Sitemap erreichbar". `404.html` ist ausgenommen, und ein Build ohne
`index.html` hat keine Wurzel, von der aus gemessen werden könnte — dann
unterbleiben die beiden Graphregeln, statt jede Seite zum Waisen zu erklären.

**Gelesen wird nur das Ziel, nie der Ankertext** (D50). Beide Hälften von
`<a href>…</a>` sind ein Element; die Entscheidung ist bewusst asymmetrisch: eine
URL ist ein Wert, die Wörter sind redaktionelle Prosa und haben in
[Page](page.md) keinen Ort. Die Konsequenz steht in der Referenz und nicht nur
hier — die Ankertext-Regeln sind der eine Teil von `internal-linking.md`, den
dieses Werkzeug nicht prüfen kann.

**Eine Auflösungsentscheidung ist von D38 geerbt:** ein absoluter Link auf `www`
und einer auf den Apex sind dieselbe Site. Sie als verschiedene zu behandeln
ließe den Graphen eine ganze Klasse interner Links still übersehen.

**Weiterleitungs-Quellen gelten als ausgeliefert** (D61). `_redirects` und
`.htaccess` aus dem Build werden gelesen — exakte Pfade und Splats dort,
`Redirect`-Direktiven und R-Flag-`RewriteRule`-Muster hier, letztere als Regex
wie der Server sie matcht. Ein Link dorthin ist beantwortet, nicht fehlend;
Kanten zeichnet er keine, denn wohin die Weiterleitung führt, ist statisch
nicht wissbar. Catch-alls (`/*`, `.*`, Canonical-Regeln) akzeptieren nie,
sonst würde eine Zeile die ganze Regel stummschalten.

- [scripts/wo/capabilities/links/audit.py](../../../scripts/wo/capabilities/links/audit.py)

## Connected to
Gehört zu [Page](page.md) (liefert `links[]`), [Page-Set](page-set.md) (die
Seiten), [Audit-Report](audit-report.md). Prozess: nur
[Audit-Statisch](../processes/audit-static.md) — [Audit-Live](../processes/audit-live.md)
endet hier in einer Verweigerung, und das ist die Absicht.
**Looks like but is not:** [Redirects](redirects.md) prüft, wohin die Site
*leitet*; diese Karte prüft, wohin sie *zeigt*. Die Quellen der
Weiterleitungen liest sie dabei mit — ein Link auf eine Quelle ist
beantwortet. Ob das Ziel dahinter nützlich ist, bleibt die Live-Frage von
[Redirects](redirects.md).

## If you change this
- **Hits:** [Page](page.md) — ein neues Linkfeld wird dort extrahiert und berührt
  damit auch [On-Page](on-page.md) und [Quality](quality.md);
  `references/internal-linking.md`; `capabilities/links/README.md`;
  `scripts/wo/redirect_rules.py` — die geteilte Redirect-Syntax (D57), mitbenutzt
  von [Redirects](redirects.md);
  [CLI](cli.md) (`REGISTRY`) und die Versionskopplung in [Audit-Report](audit-report.md)
  (`rules_run` ändert sich → `TOOL_VERSION`, D43).
- **Does not hit:** [Redirects](redirects.md); [Schema](schema.md);
  [Images](images.md); [Receipt](receipt.md); [Crawl](crawl.md) — der Live-Pfad
  wird von hier aus verweigert, nicht verändert.

## Surfaces
Aufgerufen über `wo.py links`. Liest ausschließlich das Build-Verzeichnis; kein
Netzwerkzugriff. Findungen erscheinen im Envelope und in `report.json`.

## See
[capabilities/links/README.md](../../../scripts/wo/capabilities/links/README.md).
Entscheidungen D50–D52 in [decision-log.md](../../../decision-log.md).
[Änderungsrouting](../effects/CONTEXT.md).
