# Prozesse — Lesevertrag

Inputs: gewählte Prozesskarte und ihre Quellbelege. Nicht alle Karten laden.

Process: Bewegungsfluss anhand der Steps und Belege nachvollziehen;
`consumes`/`produces` gegen die Objektkarten prüfen. Läuft der Beleg nicht auf
Code, der die Bewegung tatsächlich ausführt, ist die Karte `stale`.

Outputs: begrenzter Änderungsscope und bei Drift aktualisierte Karte.

Human Check: Die Prozessbeschreibung landet am Code, der die Bewegung
tatsächlich ausführt.