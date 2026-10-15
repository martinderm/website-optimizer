---
type: object
cluster: input
universe: live
status: verified
entity: scripts/wo/config.py
verified_at: 2026-10-15
revision: a2dda236b34e6222be84c6068d84203f340219a8
---

# Site-Config

Wer auditet wird, wo die Ausgabe liegt, und welche Capability läuft.

## Why this shape
Zwei Gründe, jeder für sich ausreichend.

**Format.** Python 3.11 liefert `tomllib` mit, YAML nicht. Der Authoring Guide
verlangt Standardbibliothek ohne pip. Eine YAML-Konfiguration würde entweder die
Regel brechen oder sich auf ein Paket verlassen, das auf *einem* Rechner
zufällig installiert ist (D20).

**Zwei Ebenen.** `site.optimizer.toml` ist portabel und wird committet,
`site.optimizer.local.toml` trägt maschinenlokale Pfade und wird nicht committet.
Ein gemischtes File lässt sich nicht committen, ohne das Verzeichnislayout eines
Rechners in jeden Fork zu tragen. Der Deep-Merge in `_merge` ist genau das, was
diese Trennung braucht: lokale Werte überschreiben, nicht ersetzen.

## Shape
`scripts/wo/config.py:24` `CONFIG_NAMES`, `:76` `_merge` (Sektionstabellen werden
schlüsselweise gemischt), `:87` `load` (portabel zuerst, dann lokal).

`SiteConfig`: `site_url`, `domain`, `static_dir`, `workspace_root`, `ignore_path`,
`strict`, `crawl_mode`, `data_classification`, `contacted_private_surface`,
`owner`, `retention_class`, `capabilities`. `classification` eskaliert einmalig
auf `confidential`, wenn `contacted_private_surface` gesetzt ist (D19).

`find_workspace_root` läuft nach oben, bis `.agents/` oder `AGENTS.md`
auftaucht. Fehlermeldungen benennen den konkreten nächsten Schritt.

- [scripts/wo/config.py](../../../scripts/wo/config.py) — `:24`, `:76`, `:87`

## Connected to
Gehört zu [CLI](cli.md), [Receipt](receipt.md) (liefert `owner` und Klassifikation), [On-Page](on-page.md) (liest `static_dir`, `site_url`, `ignore_path`, `capabilities`).

## If you change this
- **Hits:** [CLI](cli.md) (`init-site`, Template), [On-Page](on-page.md) (nimmt `SiteConfig`), [Receipt](receipt.md) (`owner`, `data_classification`), `SKILL.md` und `scripts/README.md` (Dateinamen), die Config-Tests in [Qualität](quality.md), sowie die `.gitignore` des konsumierenden Workspace.
- **Does not hit:** [Page](page.md); [Audit-Report](audit-report.md) (nimmt Werte entgegen, keine Felder hinzu); die Regel*inhalte* in `references/*`.

## Surfaces
`site.optimizer.toml` und `site.optimizer.local.toml` im konsumierenden
Workspace. Gelesen von jedem Kommando außer `init-site` und `validate-report`.

## See
[scripts/README.md](../../../scripts/README.md). [Änderungsrouting](../effects/CONTEXT.md).