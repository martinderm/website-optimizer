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
| Regelwerk, Quellen, Verbindlichkeit | [Referenzsatz](objects/reference-set.md) |
| Tests, Parität gegen das Vorgängerskript | [Qualität](objects/quality.md) |
| Tatsächliche Abläufe | [Prozesse](processes/CONTEXT.md) |
| Was trifft eine Änderung? | [Auswirkungen](effects/CONTEXT.md) |

**Namensfallen.** `references/` im Skill ist *nicht* die Data-Zone `memory/references/` im konsumierenden Workspace: die erste ist portable Methode, die zweite verbindliche Tatsache über eine Site. Ein *Run* ist ein Lauf mit eigenem Ordner, nicht ein Zeiger auf den letzten Lauf. `on-page` ist der Kommandoname, `on_page` der Modulname — ein Bindestrich ist kein gültiger Python-Bezeichner. `evidence`/`references`/`data` sind Zonen mit verschiedenen Trust-Stufen, `data/` ist überhaupt keine Zone. `subject` in einem Befund ist eine Seite bei `on-page` und eine Quell-URL bei `redirects`.

Lade [CONTEXT.md](CONTEXT.md) und nur die zum Auftrag passende Karte. Metadatenregeln: [_meta/schema.md](_meta/schema.md).