---
type: object
cluster: subsystem
universe: live
status: verified
entity: scripts/wo/crawl.py
verified_at: 2026-10-15
revision: 8450d5b
---

# Crawl

Das Rendering von Seiten im echten Browser — und der einzige Ort im Skill, der
Netzwerk und Subprozesse benutzt.

## Why this shape
Eine statische Site hat Build-Output zum Lesen. Eine dynamische Site hat keinen,
und für WordPress ist der gerenderte DOM der einzige Weg an den Inhalt. D26 hat
vier Gründe zusammengetragen, warum das **auf Anfrage** passiert und nie aus
einem Hook: Minuten statt Sekunden, geteilte Browser-Session, Zustand-abhängige
Ergebnisse (Viewport, Consent) und — entscheidend — ein Crawl hinter einer
Consent-Wall findet auf *jeder* Seite die Wall und meldet sie als Inhalt.

Der letzte Grund ist der Grund für die Wächterlogik: er wird hier mechanisch
gemacht, nicht nur dokumentiert, weil der falsche Report überzeugender ist als
der Vorbehalt.

## Shape
`scripts/wo/crawl.py` — `crawl()` öffnet eine `BrowserSession` und rendert jede
URL; `_resolve_command()` bestimmt den Aufruf; `_looks_like_a_wall()` erkennt den
Wand-Fall; `resolve_start_urls()` entscheidet zwischen expliziter Liste,
Sitemap und Root-URL.

**Keine Shell, wo es geht.** npm installiert `playwright-cli` unter Windows als
`.CMD`-Shim, den `subprocess` ohne Shell nicht ausführen kann — und eine Shell
ist falsch, weil `cmd.exe` eine URL mit `&` zerstückelt, bevor der Browser sie
sieht. Der Shim wird deshalb geparst und die JS-Datei direkt mit `node`
aufgerufen (D36).

**Bytes rein, UTF-8 raus.** `text=True` dekodiert mit der Locale-Codepage — auf
deutschem Windows cp1252. Die erste gerenderte Seite mit einem Zeichen außerhalb
dieser Codepage ließ einen `UnicodeDecodeError` in einem Reader-Thread den
Prozess mit Traceback sterben. Ein Werkzeug, dessen Eingabe beliebige Webseiten
sind, darf die Kodierung des Terminals nicht erben (D35).

## Connected to
Gehört zu [Page-Set](page-set.md), das die Ergebnisse an die Capabilities reicht.
Prozess: [Audit-Live](../processes/audit-live.md).
**Looks like but is not:** `crawl.py` ist keine Evidence-Zone und kein
Workspace-Skill. Es schreibt Rohdaten in die Daten-Zone, nicht ins Repository
des Skills.

## If you change this
- **Hits:** [Page-Set](page-set.md) — die Rohdaten und der `crawl`-Block im Report; [Site-Config](site-config.md) — der `[crawl]`-Block; [Report-Basis](../objects/audit-report.md) — `crawl_mode` und `crawl`; alle drei Capabilities, denn sie nehmen denselben Resolver.
- **Does not hit:** [Redirects](redirects.md) — eigener Mechanismus, kein Browser; die Regeltexte in `references/*`; [Receipt](receipt.md) — er schreibt keine Findings.

## Surfaces
Schreibt `data/crawl/<run-id>/` im konsumierenden Workspace, jeweils mit
Provenienz-Kommentar (URL, Abrufzeit, Tool-Version). Retention-Klasse
`crawl-ephemeral`, git-ignoriert (D27).

**`[crawl] profile` öffnet den Browser mit `--profile=<dir>`** (D41). Der einzige
Weg an einer Consent-Wall vorbei: einmal `--headed` starten, zustimmen, und alle
späteren Crawls kommen bereits dahinter vorbei. Ein relativer Pfad löst gegen den
Workspace auf — damit sind „ein Profil pro Agent-Workspace" und „ein Profil pro
Maschine" beide formulierbar, ohne dass eine Variante erzwungen wird. Standard ist
aus: ein Profilverzeichnis trägt Session-Cookies und darf nicht ungefragt
entstehen. Das Werkzeug legt das Verzeichnis an und liest, schreibt oder meldet
seinen Inhalt nie.

Noch nie gegen eine echte Wall getestet: der Wächter ist getestet, der Ausweg
nicht.

## See
Quellmodul: [scripts/wo/crawl.py](../../../scripts/wo/crawl.py). D26, D27, D32, D34, D35, D36 in [decision-log.md](../../../decision-log.md). Browser-Handhabung: `../playwright-cli/SKILL.md`.