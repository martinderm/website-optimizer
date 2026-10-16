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
| `on-page` | audit on-page signals in a static output directory |
| `links` | audit the internal link graph of built output |
| `crawler-files` | audit robots.txt, the sitemap and llms.txt, from a build or the live site |
| `redirects` | probe live redirect rules against the running site |
| `runs` | list stored runs for the configured site |
| `validate-report` | validate a report; the matching capability schema is autodetected |

Common flags: `--config`, `--workspace`, `--json`. Capability commands add
`--strict`, `--run`, `--dry-run`, and `--ignore-noindex` (`on-page`).

Capability subparsers are generated from `REGISTRY`, so registering a capability
is the only step needed to expose it on the command line.

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
  urls.py                 how a URL and a build file name each other
  sitemaps.py             sitemap syntax: <loc>, index roots, known names
  report.py               run folders, atomic writes, data-zone receipts
  jsonschema.py           dependency-free validator for the schema subset used
  capabilities/
    on_page/              static output analysis
    redirects/            live rule verification
    images/              image delivery and icons
    schema/              JSON-LD structure
    links/               the internal link graph (build output only)
    crawler_files/       robots.txt, sitemap, llms.txt
    compare/             difference attribution between runs
schemas/
  report-base.schema.json     fields every report carries
  on-page-report.schema.json  extends the base
  redirects-report.schema.json extends the base
  images-report.schema.json     extends the base
  schema-report.schema.json     extends the base
  links-report.schema.json      extends the base
  crawler-files-report.schema.json extends the base
  compare-report.schema.json   extends the base
tests/                    stdlib unittest, including parity against the originals
```

`capabilities/on_page/` carries an underscore while the command is `on-page`: a
hyphen is a fine command name and an invalid Python identifier.

## Network

`redirects` performs live HTTP requests, and `crawler-files` does so with
`--live`; `on-page`, `images`, `schema` and `links` do not. A capability that
reaches the network is marked `crawl_mode: live` in its report, because a live
result and a static one are not comparable.

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