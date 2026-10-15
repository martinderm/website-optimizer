---
type: process
universe: live
status: verified
entity: scripts/wo.py
verified_at: 2026-10-15
revision: a2dda236b34e6222be84c6068d84203f340219a8
consumes:
  - ../objects/site-config.md
  - ../objects/page.md
produces:
  - ../objects/audit-report.md
  - ../objects/receipt.md
  - ../objects/envelope.md
---

# Audit-Statisch

## Input → Movement → Output

**Input:** `site.optimizer.toml` plus `site.optimizer.local.toml`; das
generierte Ausgabeverzeichnis.

**Movement:** `wo.py on-page` löst die Config auf, prüft die Capability-Liste,
iteriert `*.html` unterhalb von `static_dir`, filtert über `ignore_path`,
extrahiert je Seite ein [Page](../objects/page.md), wendet die Regeln aus
[On-Page](../objects/on-page.md) an, validiert das Ergebnis gegen das Report-Schema
und schreibt Report und Beleg in die Evidence-Zone des Workspace.

**Output:** Envelope auf stdout; `report.json` und `receipt.json` unter
`<workspace>/memory/evidence/websites/<domain>/runs/<run-id>/`.

## Why this shape
Die Reihenfolge ist nicht verhandelbar, weil drei Prüfungen dazwischenliegen:
erst wird extrahiert, dann gemessen, dann gegen das Schema geprüft, und **erst
danach** geschrieben. Ein Report, der das Schema verletzt, erreicht die Platte
nicht — lieber kein Report als einer, der wie ein gültiger aussieht.

## Steps

1. `_load_config` lädt portabel, dann lokal, und meldet `ConfigError` mit
   konkreter nächster Aktion.
   — [scripts/wo.py:64](../../../scripts/wo.py), [scripts/wo/config.py:87](../../../scripts/wo/config.py)
2. Fehlt die Capability in `[audit] capabilities`, endet der Lauf mit einem
   Fehler, der die Zeile nennt, die zu ergänzen ist.
   — [scripts/wo.py](../../../scripts/wo.py) (`_run_capability`)
3. `find_static_dir` erkennt `public/`, ein reines HTML-Verzeichnis oder den
   angegebenen Pfad. Die Funktion liegt jetzt in
   [Page-Set](../objects/page-set.md), weil drei Capabilities sie brauchen und
   nur eine Kopie eine Regel bleibt; `on_page.audit` re-exportiert sie, damit der
   Paritätstest nicht wegen einer Verschiebung bricht.
   — [scripts/wo/pages.py](../../../scripts/wo/pages.py)
4. `iter_html_files` liefert eine **sortierte** Liste; `ignore_path` wird als
   Regex auf den workspace-relativen Pfad angewandt. Die Extraktion läuft über
   `extract_page` — dieselbe Funktion, die auch gerendertes Markup verarbeitet.
   — [scripts/wo/page.py](../../../scripts/wo/page.py), [scripts/wo/pages.py](../../../scripts/wo/pages.py)
5. `audit_page` erzeugt atomare Befunde in fester Regelreihenfolge.
   — [scripts/wo/capabilities/on_page/audit.py:181](../../../scripts/wo/capabilities/on_page/audit.py)
6. `jsonschema.validate` prüft den Report; bei Verstoß wird nichts geschrieben.
   — [scripts/wo.py](../../../scripts/wo.py) (`_run_capability`), [scripts/wo/jsonschema.py:52](../../../scripts/wo/jsonschema.py)
7. `write_run` legt den Laufordner an, schreibt atomar und prüft den Beleg gegen
   die Teilmenge des Daten-Zonen-Schemas.
   — [scripts/wo/report.py:140](../../../scripts/wo/report.py)

## Compare also this
[Audit-Live](audit-live.md) — derselbe Ablauf über eine andere Quelle.

**Looks like but is not:** [Audit-Live](audit-live.md) ist keine Variante, die
man anstelle dieses Ablaufs wählt, weil sie gründlicher wäre. Sie ist nötig, wo
es kein Build-Verzeichnis gibt, und die statischen Befunde sind keine Teilmenge
der live gefundenen.

## If you change this
- **Hits:** [Site-Config](../objects/site-config.md), [Page](../objects/page.md), [Page-Set](../objects/page-set.md), [On-Page](../objects/on-page.md), [Audit-Report](../objects/audit-report.md), [Receipt](../objects/receipt.md), [Envelope](../objects/envelope.md), [Qualität](../objects/quality.md).
- **Does not hit:** [Referenzsatz](../objects/reference-set.md) — der Ablauf ändert nicht, was inhaltlich korrekt ist; [Crawl](../objects/crawl.md), solange kein Browser beteiligt ist.

## Surfaces
Kommandozeile. Schreibt ausschließlich in den Laufordner; `--dry-run` schreibt
gar nichts.

## See
[scripts/README.md](../../../scripts/README.md).