# Objekte — Lesevertrag

Inputs: Kartenindex und die zum Auftrag passende Objektkarte samt Quellzitaten.
Nicht alle Karten laden; der Katalog existiert genau dafür, dass man es nicht muss.

Process: `universe` prüfen. `live` = aktiv verdrahtet, gegen die Quelle
implementieren und zitieren. `leftover` = noch vorhanden, nicht mehr Hauptpfad,
nur anfassen wenn dieser Pfad im Auftrag liegt. `ghost` = benannt, nicht
implementiert; **nicht** gegen diese Karten implementieren.

Outputs: Änderungsscope. Bei Drift Karte mit Quelle, Datum und Revision
aktualisieren — und die Map im selben Commit, wenn sich ein Vertrag geändert hat.

Human Check: Die Aussagen der Karte stehen am Code, nicht in einer Absicht. Die
`Does not hit`-Zeile benennt die naheliegende falsche Nachbarkarte.