---
type: object
cluster: logic
universe: live
status: verified
entity: scripts/wo/capabilities/redirects/audit.py
verified_at: 2026-10-15
revision: a2dda236b34e6222be84c6068d84203f340219a8
---

# Redirects

Prüft live, ob die Site das tut, was ihre Redirect-Regeln behaupten.

## Why this shape
Regeln sind eine Behauptung; HTTP-Antworten sind die Messung. Die Capability
vergleicht beides, statt die Konfiguration für gültig zu erklären, weil eine
korrekt gelesene Datei regelmäßig falsche Regeln enthält.

Zwei Grenzen sind bewusst gezogen. **Antwortkörper werden nie gelesen** — nur
Statuszeile und `Location`-Header. Ein Redirect-Ziel ist beliebiger Inhalt, und
diese Capability hat absichtlich keinen Weg, über den fremdes HTML in den Report
gelangt (D13). Und **Wildcard-Regeln werden nicht auf ihr Ziel geprüft**: das
Ziel war ein Beispiel-Slug, ein 404 dort wäre ein Fehlalarm.

## Shape
`scripts/wo/capabilities/redirects/parse.py` — Parser für `.htaccess`
(`RewriteRule`, `Redirect`), `_redirects` (Splat-Syntax) sowie JSON- und
CSV-Mappings; `clean_regex_to_path` macht aus einem Regex einen anfragbaren Pfad
und meldet, ob es eine Wildcard ist.

`scripts/wo/capabilities/redirects/audit.py` — `probe` stellt die Quelle mit
einem Handler, der Weiterleitungen offenlegt statt ihnen zu folgen, und
vergleicht `Location` mit dem konfigurierten Ziel. `_findings_from_row` leitet
atomare Befunde ab; `run` schreibt eine `checks`-Zeile **pro Regel** und einen
Befund **nur für Fehlschläge**.

Regeln: `redirect.location_mismatch`, `redirect.status_unexpected`,
`redirect.unreachable`, `redirect.target_unreachable` (alle `critical`),
`redirect.failed` (`warning`).

`crawl_mode` ist hier `live` — eine Weiterleitung *ist* eine Netzbeobachtung, und
ein Vergleich gegen einen statischen Lauf wäre bedeutungslos.

- [scripts/wo/capabilities/redirects/audit.py](../../../scripts/wo/capabilities/redirects/audit.py)
- [scripts/wo/capabilities/redirects/parse.py](../../../scripts/wo/capabilities/redirects/parse.py)

## Connected to
Gehört zu [Audit-Report](../objects/audit-report.md) (eigener `checks`-Abschnitt), [Site-Config](../objects/site-config.md) (`[redirects]`-Block), [Envelope](../objects/envelope.md). Prozess: [Audit-Statisch](../processes/audit-static.md) für den Ablauf, `crawl_mode: live`.
**Looks like but is not:** [On-Page](../objects/on-page.md) arbeitet ohne Netz; diese Capability ohne Build-Verzeichnis. Beide teilen nur den Findings-Vertrag.

## If you change this
- **Hits:** [Audit-Report](../objects/audit-report.md) (`redirects-report.schema.json`), [Site-Config](../objects/site-config.md) (`[redirects]`-Optionen), [Envelope](../objects/envelope.md) (Exit-Code-Zählung), [Qualität](../objects/quality.md) (16 neue Tests), [CLI](../objects/cli.md) (REGISTRY), `references/redirects.md` (Regeltext), `capabilities/redirects/README.md`.
- **Does not hit:** [Page](../objects/page.md) — hier wird keine Seite extrahiert; [Referenzsatz](../objects/reference-set.md) jenseits der Regeltexte in `redirects.md`; der Paritätstest in [Qualität](../objects/quality.md) hängt am Vorgängerskript, das live prüft.

## Surfaces
Netzwerkzugriff auf die konfigurierte Site. Aufgerufen über `wo.py redirects`.
Schreibt einen Lauf in die Evidence-Zone des Workspace.

## See
[capabilities/redirects/README.md](../../../scripts/wo/capabilities/redirects/README.md). [Änderungsrouting](../effects/CONTEXT.md).