---
type: object
cluster: governance
universe: live
status: verified
entity: SKILL.md
verified_at: 2026-10-15
revision: a2dda236b34e6222be84c6068d84203f340219a8
---

# Skill-Verhalten

Arbeitsregeln, Router, Ein-Homes-pro-Fakt, Phasenstatus.

## Why this shape
Der Skill misst und rät. Er baut nicht, hostet nicht, deployt nicht — und genau
das gehört in die Description, weil ein breit getriggerter Skill sonst die
Bau-, Hosting- und Browser-Skills überlagert. Die Negativliste in `SKILL.md` ist
deshalb Teil des Designs, nicht Dokumentations-Nice-to-have.

Der Skill speichert selbst keine Laufzustände. Der Workspace hält die Zone, der
Skill liefert das Werkzeug (D8). Und der Referenzsatz des Skills ist *nicht* die
`references`-Zone eines Workspace: portable Methode gegen verbindliche Tatsache
über eine Site.

## Shape
`SKILL.md`: Status, Quick Start, Router (eine Zeile pro Frage), **Not this
skill** (Negativliste gegen `hugo`, `caddy`, `cloudflare-pages`, `cloudflared`,
`playwright-cli`, `writing-pro`), Dependencies (`playwright-cli` als erklärte
Abhängigkeit des Live-Pfads), Run-State-Grenze, Ein-Homes-Tabelle.

`PLAN.md` trägt den Entwurf, `decision-log.md` die D1–D28 mit `support_level`
und Belegankern. Phasen: 1 Scaffold, 2 eine Capability, 3a References + Stubs, 3b Map,
4 Capabilities, 5 Live-Crawl, 6 Aufräumarbeiten.

Der Phasenstatus wird aus dem Plan in `SKILL.md` gespiegelt, damit ein Aufrufer
den Zustand nicht erst im Plan suchen muss.

- [SKILL.md](../../../SKILL.md) — Router, Negativliste, Status
- [PLAN.md](../../../PLAN.md) — §8 Phasen, §4 Skriptentwurf
- [decision-log.md](../../../decision-log.md) — D1–D28

## Connected to
Gehört zu [Referenzsatz](reference-set.md) (was der Router adressiert), [CLI](cli.md) (Quick Start), [Receipt](receipt.md) (Run-State-Grenze).
**Looks like but is not:** `PLAN.md` ist kein Regelwerk. Es ist der Entwurf, der die Regeln erklärt, und wird nicht als Anleitung zitiert.

## If you change this
- **Hits:** [CLI](cli.md) (Kommandonamen im Quick Start), [Referenzsatz](reference-set.md) (neue Datei braucht eine Router-Zeile), die Katalogenregistrierung in `skills-catalog.yaml`, die Stubs im konsumierenden Workspace.
- **Does not hit:** [On-Page](on-page.md), [Page](page.md), [Receipt](receipt.md), [Audit-Report](audit-report.md) — Arbeitsregeln ändern keine Messung.

## Surfaces
`SKILL.md` ist der Skill-Einstieg und wird vom Harness geladen. `PLAN.md` und
`decision-log.md` werden von Menschen und von späteren Agenten gelesen.

## See
[PLAN.md](../../../PLAN.md). [Änderungsrouting](../effects/CONTEXT.md).