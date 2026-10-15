---
type: process
cluster: flow
universe: live
status: verified
entity: scripts/wo/pages.py
verified_at: 2026-10-15
revision: 8450d5b
---

# Audit-Live

`wo.py <capability> --live` — dieselben Regeln, andere Quelle.

## When this runs
Nur auf ausdrückliche Anfrage. Es gibt keinen Config-Schalter, der es aktiviert,
und keinen Hook-Pfad, der es erreichen könnte (D26). Wer eine dynamische Site
prüfen will, tippt `--live`.

## Steps

1. **Preflight** — `_resolve_command()` findet den Browser-CLI als echtes
   Executable oder als Node-Eintrag hinter dem npm-Shim. Fehlt er, endet der Lauf
   mit einer Meldung, die den Installationsbefehl nennt.
2. **Session öffnen** — Name `wo-<domain>`, damit zwei Harnesses im selben
   Workspace nie dieselbe Browser-Session teilen. Auf Windows wird Edge gewählt,
   weil das Preflight Edge als installiert meldet.
3. **URLs bestimmen** — explizite `start_urls`, sonst die Sitemap, sonst die
   Root-URL als ausdrücklich geratene Annahme.
4. **Rendern** — `goto`, kurzes Settle, dann
   `eval "document.documentElement.outerHTML"` mit `--raw`. Ein Fehlschlag wird
   protokolliert, nicht geworfen: eine kaputte URL darf einen Crawl von vierhundert
   nicht verwerfen.
5. **Extraktion** — jede Seite wird über
   `extract_page_from_html` geschickt, also durch dieselbe Grenze wie eine Datei.
6. **Artefakt schreiben** — `data/crawl/<run-id>/` mit Provenienz-Kommentar. Erst
   nach erfolgreicher Extraktion, damit keine Datei eine Seite behauptet, die
   nie gesehen wurde.
7. **Wand-Prüfung** — sind die meisten Seiten bytegleich, wird **nicht**
   berichtet, sondern abgebrochen (D34).
8. **Regeln** — unverändert. `icon.file_missing` fällt aus `rules_run` heraus,
   weil ein Crawl kein Build-Verzeichnis hat, in dem die Datei liegen könnte.
9. **Report** — trägt `crawl_mode: live` und einen `crawl`-Block mit
   requested / fetched / failed / limit (D32).

## Compare also this
[Audit-Statisch](audit-static.md) — derselbe Ablauf, andere Quelle.

**Looks like but is not:** [Audit-Statisch](audit-static.md) ist *nicht* die
Vorbereitung dieses Laufs. Es ist derselbe Lauf mit `--static`, und die
statischen Befunde sind keine Teilmenge der live gefundenen — sie sind nur
derselbe Regeltext über andere Eingaben.

## If you change this
- **Hits:** [Crawl](../objects/crawl.md); [Page-Set](../objects/page-set.md); [CLI](../objects/cli.md); alle drei Capabilities, weil sie denselben Resolver benutzen.
- **Does not hit:** [Redirects](../objects/redirects.md) — eigene Klasse, kein `--live`; [Receipt](../objects/receipt.md); [Qualität](../objects/quality.md) — die Paritätstests laufen statisch.

## Surfaces
`data/crawl/<run-id>/` im konsumierenden Workspace.

## See
[scripts/wo/pages.py](../../../scripts/wo/pages.py), [scripts/wo/crawl.py](../../../scripts/wo/crawl.py). D26, D27, D32–D36 in [decision-log.md](../../../decision-log.md).