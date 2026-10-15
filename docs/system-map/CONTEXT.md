# System-Map — Lesevertrag

## Inputs
Reference: [Katalog](README.md), [_meta/schema.md](_meta/schema.md), die in der gewählten Karte verlinkten Quellmodule. Working: konkreter Änderungsauftrag oder GitHub Issue.

## Do NOT load
Nicht alle Karten und nicht `references/` laden. `references/` ist kuratierte Regel-Dokumentation und wird nur thematisch passend geöffnet, niemals vollständig — das ist der Lesevertrag dieser Map: eine Karte plus ein Quellmodul müssen reichen.

## Process
1. Katalog nach Objekt oder Prozess wählen; für Änderungen zuerst `effects/CONTEXT.md` lesen.
2. Quellzitate und Grenzen der gewählten Karte prüfen. Code hat bei Ist-Zustandsfragen Vorrang; `SKILL.md` trägt die Arbeitsregeln, `references/` die Regeln.
3. Live = aktiv verdrahtet; leftover = historisch oder ersetzt; ghost = benannt, aber nicht implementiert.
4. Bei Drift Karte mit Quelle, Datum und Revision synchron aktualisieren. `README.md` ändern und `AGENTS.md`/`routing.md` daraus bytegleich generieren.

## Outputs
Begründeter Änderungsscope und synchron aktualisierte Objekt-/Prozesskarten. Offene Arbeit als GitHub Issue, keine lokale Backlog-Datei.

## Human Check
Eine fremde Person findet vom Skill-Einstieg aus eine Karte, deren Quellbelege sie öffnen und deren direkte Änderungsauswirkungen sie erklären kann. Der Kartierungsstand behauptet keinen aktuellen Testlauf — die Tests laufen getrennt.