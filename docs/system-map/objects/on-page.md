---
type: object
cluster: logic
universe: live
status: verified
entity: scripts/wo/capabilities/on_page/audit.py
verified_at: 2026-10-15
revision: a2dda236b34e6222be84c6068d84203f340219a8
---

# On-Page

Die zehn Regeln der ersten Capability. Jede eine reine Funktion der extrahierten
Felder.

## Why this shape
Eine Regel sieht Felder, nie ein Urteil. Würde eine Regel eine Zusammenfassung
über die Seite mitlesen, bestätigte sie diese Zusammenfassung, statt sie
unabhängig neu herzuleiten — dieselbe Verzerrung, aus der ein Modell seinen
eigenen Entwurf wiederholt (D15). Deshalb ist jede Regel eine Funktion
`Page -> list[finding]` ohne Seitenzugriff.

Die Reihenfolge in `RULES` ist fixiert und bestimmt die Report-Reihenfolge. Eine
neue Regel wird dort registriert, nicht an einer Aufrufstelle versteckt.

## Shape
`scripts/wo/capabilities/on_page/audit.py:167` `RULES` — `title_missing`,
`description`, `canonical`, `lang_missing`, `headings`, `open_graph`,
`twitter_card`, `landmarks`, `image_alt`, `robots_noindex`.
`:181` `audit_page` verteilt die Argumente an die zwei Regeln, die welche
brauchen (`canonical` braucht `site_url`, `robots_noindex` das
Suppress-Flag). `:206` `run` über ein Ausgabeverzeichnis.

Schweregrade: `critical` für Title, Description, `canonical.missing`,
`canonical.mismatch`, `lang`, `h1`, `og:title`, `og:image`, `img:alt`.
`warning` für kurze/lange Description, mehrfaches `h1`, `og:description`,
`twitter:card`, `main`, Skip-Link, `noindex`, und **`canonical.host_differs`**.

**Zwei Canonical-Befunde, weil zwei verschiedene Dinge dahinterstehen** (D38).
Ein Canonical auf einem *anderen Host* als `[site] url` ist ein
Konfigurationshinweis: die Seiten sind untereinander konsistent, sie widersprechen
nur dem konfigurierten Wert. `www` gegen Apex ist die häufigste
WordPress-Fehlkonfiguration überhaupt, und sie erzeugte einmal zwölf identische
kritische Befunde auf zwölf Seiten — wer zwölfmal dasselbe sieht, hört auf, die
Regel zu lesen, und die eine tatsächlich falsche Zeile verschwindet darin.
Ein Canonical *außerhalb* eines pfadpräfigierten Base-URLs bleibt kritisch und
blieb es. Nichts wird unterdrückt: die Host-Abweichung wird weiterhin auf jeder
Seite gemeldet, nur nicht als kaputte Seite.

Nebenbefund beim Schreiben des Tests: `canonical.mismatch` ist bei einem nackten
Host als Base **unerreichbar**, weil jeder Canonical auf diesem Host mit ihm
beginnt. Die Regel braucht einen Base mit Pfad-Präfix. Das galt schon vorher —
sie war für die meisten Single-Host-Installationen tot.

Eine absichtliche Abweichung vom Vorgänger: `--ignore-noindex` unterdrückt jetzt
tatsächlich. Im portierten Skript existierte der Parameter, wurde aber nie
durchgereicht (D22).

- [scripts/wo/capabilities/on_page/audit.py](../../../scripts/wo/capabilities/on_page/audit.py) — `:167`, `:181`, `:206`

## Connected to
Gehört zu [Page](page.md) (Eingang), [Audit-Report](audit-report.md) (Ausgang), [Site-Config](site-config.md). Prozess: [Audit-Statisch](../processes/audit-static.md).
**Looks like but is not:** die Regel*beschreibungen* in `references/seo-core.md` sind nicht diese Regeln. Die Reference sagt, was korrekt ist; hier steht, wie geprüft wird. Beide müssen synchron gehalten werden.

## If you change this
- **Hits:** [Page](page.md) (Feldnamen), [Audit-Report](audit-report.md) (Finding-Struktur), [Qualität](quality.md) (die Regeltests und — solange der Vorgänger existiert — der Paritätstest), `capabilities/on_page/README.md` (Regeltabelle), `references/seo-core.md` und `references/accessibility.md` (Regeltext).
- **Does not hit:** [Receipt](receipt.md); [Site-Config](site-config.md), sofern keine Konfigurationsoption hinzukommt; die anderen References, die andere Themen behandeln.

## Surfaces
Aufgerufen über `wo.py on-page`. Findungen erscheinen im Envelope und in
`report.json`.

## See
[capabilities/on_page/README.md](../../../scripts/wo/capabilities/on_page/README.md). [Änderungsrouting](../effects/CONTEXT.md).