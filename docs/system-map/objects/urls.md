---
type: object
cluster: interface
universe: live
status: verified
entity: scripts/wo/urls.py
verified_at: 2026-10-16
revision: d54632c434fd18da884ed4b491c5c50141cb01a0
---

# URLs

Wie eine URL und ein Build-Dateiname einander benennen — an einer Stelle, weil
zwei Capabilities die Frage stellen.

## Why this shape
Ein statischer Server beantwortet eine Datei unter mehreren Schreibweisen:
`/about`, `/about/` und `/about/index.html` sind dieselbe Seite. `links` löst ein
Linkziel dagegen auf, `crawler-files` eine Sitemap-URL — dieselbe Frage, zweimal
gestellt.

**Sie wurde zur Kopie und ging sofort schief.** Innerhalb von `links` akzeptierte
`served()` die Schreibweise `/index.html` für die Startseite, `page_urls()` tat es
nicht: eine URL, die existiert und im Graphen nirgends hinführt. Gefunden nur, weil
beide Funktionen nebeneinander gelesen wurden. Als `crawler-files` denselben Satz
Schreibweisen brauchte, wäre die Kopie die dritte Stelle geworden — und die dritte
Stelle ist die, an der eine Abweichung dauerhaft wird (D57).

## Shape
`scripts/wo/urls.py` — `key()` (Query, Fragment und Prozentkodierung fallen weg,
das Ergebnis wird normalisiert), `served()` (jede URL, die das Verzeichnis
beantwortet, in allen Schreibweisen, Dateien eingeschlossen), `page_urls()` (die
Schreibweisen, die *eine gebaute Seite* benennen), `path_of()` (die Site-relative
Form einer absoluten URL, `None` bei fremdem Host), `bare_host()`.

`served()` liest das Verzeichnis, nicht die geprüfte Seitenmenge: eine Seite, die
`ignore_path` aus dem Audit ausschließt, ist ungeprüft und nicht abwesend.

- [scripts/wo/urls.py](../../../scripts/wo/urls.py)

## Connected to
Gehört zu [Links](links.md) und [Crawler-Files](crawler-files.md) — die beiden
Aufrufer. Benutzt [Page](page.md) nur über `page.source`.
**Looks like but is not:** keine eigene Capability und kein Kommando. Es gibt
keinen `wo.py urls`; das Modul hat keine Regeln, nur Schreibweisen.

## If you change this
- **Hits:** [Links](links.md) und [Crawler-Files](crawler-files.md) gleichzeitig —
  beide verlassen sich auf dieselben Schreibweisen; `tests/test_links.py` prüft
  die Übereinstimmung gegen eine Tabelle, nicht gegen eine Ableitung.
- **Does not hit:** jede andere Capability; die Regel*texte* in `references/*`.

## Surfaces
Kein Kommando. Interner Import von `links` und `crawler_files`.

## See
[scripts/wo/urls.py](../../../scripts/wo/urls.py). Entscheidung D57 in
[decision-log.md](../../../decision-log.md). [Änderungsrouting](../effects/CONTEXT.md).
