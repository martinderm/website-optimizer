---
type: object
cluster: quality
universe: live
status: verified
entity: scripts/tests/
verified_at: 2026-10-15
revision: a2dda236b34e6222be84c6068d84203f340219a8
---

# Qualität

104 Tests, Standardbibliothek `unittest`, kein Runner nötig.

## Why this shape
Der Authoring Guide verbietet pip-Abhängigkeiten; ein Test-Runner wie pytest wäre
eine. `unittest` ist im Standard und läuft überall dort, wo Python läuft.

Die bemerkenswerteste Eigenschaft dieser Karte ist nicht ein Test, sondern deren
Lebenszyklus: `test_parity.py` vergleicht beide Implementierungen und **schaltet
sich selbst ab**, sobald der Vorgänger gelöscht ist. Ein Paritätstest, der eine
gelöschte Datei braucht, wäre nach der Migration ein dauerhaft roter Test — also
kein Wegweiser, sondern Lärm.

## Shape
`scripts/tests/test_page.py` — Extraktion, JSON-LD-`@graph`, und die
Negativprobe: dass die `Page` keinen Fließtext enthält (D13 als Test, nicht als
Kommentar).
`test_on_page.py` — jede Regel feuert und schweigt im richtigen Fall.
`test_parity.py` — führt Original und Port über dasselbe Fixture-Verzeichnis
und vergleicht `(page, severity, message)`-Tripel; überspringbar.
`test_contracts.py` — Envelope, Schema-Validator (`if`/`then`, Union-Typen,
`additionalProperties`), Receipt, atomare Schreibvorgänge, Evidence-Append-only.
`test_config.py` — TOML-Ebenen, Fehlermeldungen, Klassifikationseskalation.
`test_redirects.py` — Parser für alle vier Dateitypen und die Ableitung der
Befunde, ohne Netz.
`test_images_schema.py` — Bildregeln und JSON-LD, plus zwei Grenztests: `alt`
gehört `on-page`, und `schema` prüft Struktur statt Vokabular.

Fixture: `scripts/tests/fixtures/site/public/` — drei Seiten, eine mit genau
vier erwarteten Befunden, eine makellose, eine 404.

Parität wurde zusätzlich auf einer echten Site mit 173 Seiten geprüft: 0 Befunde
verloren, 0 erfunden.

**Zwei Bugs fand kein Test, sondern der Lauf gegen die echten Daten.** Der
JSON-LD-Block-Regex verlangte Anführungszeichen um den `type`-Attribut; der
minifizierte Generator-Output liefert keine, also meldete eine vollständig
markierte Site 173 Warnungen statt null. Und die `@id`-Regel meldete denselben
Knoten auf jeder Seite als Fehler, obwohl genau das der richtige `@graph` ist.
Ein Test mit realistischem, minifiziertem Markup deckt den ersten Fall jetzt ab;
der zweite wird durch zwei Fixtures getragen, weil sich „kein Icon" und „fehlendes
Icon" nicht in einem Fixture ausschließen.

- [scripts/tests/test_parity.py](../../../scripts/tests/test_parity.py)
- [scripts/tests/fixtures/site/public/index.html](../../../scripts/tests/fixtures/site/public/index.html)

## Connected to
Gehört zu [On-Page](on-page.md), [Page](page.md), [Site-Config](site-config.md), [Receipt](receipt.md), [Envelope](envelope.md) — praktisch zu jeder Karte.

## If you change this
- **Hits:** jede Vertragsänderung; [On-Page](on-page.md) (Regeltests), [Site-Config](site-config.md) (Merge-Verhalten), [Receipt](receipt.md), [Envelope](envelope.md), [Audit-Report](audit-report.md) (Fixtures brechen bei Schemaänderung).
- **Does not hit:** [Referenzsatz](reference-set.md) und [Skill-Verhalten](skill-behavior.md) — die Regeln und Arbeitsregeln werden nicht durch Tests abgesichert, sondern durch Quellenangabe und Disziplin.

## Surfaces
`python -m unittest discover -s tests -p "test_*.py"` aus `scripts/`.
Lokal ausgeführt; kein CI-Anschluss eingerichtet — das ist eine offene Lücke.

## See
[scripts/README.md](../../../scripts/README.md). [Änderungsrouting](../effects/CONTEXT.md).