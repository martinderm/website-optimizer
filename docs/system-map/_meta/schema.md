# Kartenschema

Geschlossene Typen: `object`, `process`. Geschlossene `universe`: `live`, `leftover`, `ghost`. Status: `stub`, `verified`, `stale`.

**Pflichtfelder:** `type`, `universe`, `status`, `entity` (Repository-Pfad), `verified_at` (ISO-Datum), `revision` (Git-Commit des geprüften Codebestands). `object` ergänzt `cluster`; `process` ergänzt `consumes` und `produces` (relative Links zu Objektkarten). `verified` setzt prüfbare Quellzitate voraus. Ungeprüfte Karten bleiben `stub`; erkannter Drift wird `stale`.

**Objektabschnitte:** Kurzdefinition, Why this shape, Shape mit Quellbelegen, Connected to, If you change this (Hits / Does not hit), Surfaces, See.
**Prozessabschnitte:** Input → Movement → Output, Why this shape, Steps mit Belegen, If you change this, Surfaces, See.

Quelllinks sind relativ; ergänzende `path:line`-Zitate sind repository-relativ. Laufzeitbehauptungen beziehen sich auf die angegebene Revision.

**Synchronität:** jede Änderung an Schemata, Verträgen, State-Maschinen, Konkurrenzregeln, Grenzen oder Workflows aktualisiert diese Map im selben Commit.

`README.md` ist der Kartenkatalog; `AGENTS.md` und `routing.md` sind aus `README.md` generierte, bytegleiche Zwillinge. Sie werden nie von Hand editiert.