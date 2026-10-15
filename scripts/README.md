# `website-optimizer` scripts

Python 3.11+ tools. Standard library only, no pip dependencies.

## One entry point

```
python scripts/wo.py <command> [options]
```

`wo.py` is the only executable. Capability modules are packages, not standalone
scripts: two entry points drift apart, and running `wo.py` puts this directory on
`sys.path` so the packages import without path manipulation.

## Commands

| Command | Purpose |
|---|---|
| `init-site` | write a `site.optimizer.toml` for a site |
| `on-page` | audit on-page signals, write one evidence run |
| `run-all` | run every enabled capability in order |
| `runs` | list stored runs for the configured site |
| `validate-report` | validate a report against `schemas/audit-report.schema.json` |

Common flags: `--config`, `--workspace`, `--json`. Audit commands add `--strict`,
`--ignore-noindex`, `--run`, `--dry-run`.

## Configuration

Two files, by design:

| File | Contains | Committed |
|---|---|---|
| `site.optimizer.toml` | portable values: site URL, domain, static dir, crawl limits | yes |
| `site.optimizer.local.toml` | machine-specific paths | no |

TOML, not YAML: `tomllib` ships in the Python standard library from 3.11 and YAML
does not. The authoring guide requires stdlib-only, so a YAML config would either
break that rule or depend on a package that happens to be installed.

## Layout

```
wo.py                     entry point
wo/
  envelope.py             the standard --json envelope
  config.py               TOML loading and validation
  page.py                 field extraction from HTML
  report.py               run folders, atomic writes, data-zone receipts
  jsonschema.py           dependency-free validator for the schema subset used
  capabilities/
    on_page/              one capability, one folder
schemas/
  audit-report.schema.json
tests/                    stdlib unittest, including parity against the original
```

`capabilities/on_page/` carries an underscore while the command is `on-page`: a
hyphen is a fine command name and an invalid Python identifier.

## Where output goes

Runs are Evidence, per the Workspace Data Zones standard — append-only, one
folder per execution, never a file that gets overwritten:

```
<workspace>/memory/evidence/websites/<domain>/runs/<run-id>/
    report.json
    receipt.json
```

`receipt.json` conforms to `data-zone-artifact.schema.json` using the house field
names, so the workspace linter can read it. `owner` is the workspace slug.
Raw crawl output is not knowledge and stays outside the zones.

## Safety properties

- **Crawled pages are untrusted input.** `page.py` extracts fields only and keeps
  no body text, so page content cannot reach a report or an agent context.
- **Findings are atomic.** A rule sees extracted fields, never a verdict about the
  page; the verdict is derived from the findings.
- **Writes are atomic.** `tempfile` plus `os.replace`, so a reader never sees a
  partial report.
- **Nothing is destroyed.** Evidence folders accumulate; `--dry-run` writes
  nothing at all.

## Tests

```
python -m unittest discover -s tests -p "test_*.py"
```

Standard library `unittest`, no runner dependency. The parity test compares this
implementation against `hugo-wizard/scripts/audit-site-seo.py` and skips itself
once that file is gone.