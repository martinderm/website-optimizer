# `on-page` capability

Audits the signals that live inside a single page: title, description,
canonical, language, heading structure, Open Graph, Twitter Cards, landmarks,
image alt attributes, and the `noindex` state.

## Interface

```
python scripts/wo.py on-page [--config FILE] [--strict] [--ignore-noindex] [--run ID] [--dry-run] [--json]
```

| Flag | Effect |
|---|---|
| `--config` | path to `site.optimizer.toml`; otherwise discovered upwards from the workspace root |
| `--strict` | exit code 1 when any finding has severity `critical` |
| `--ignore-noindex` | do not report pages carrying `<meta name="robots" content="noindex">` |
| `--run ID` | explicit run identifier; default is a UTC timestamp without colons |
| `--dry-run` | audit and report, write nothing |
| `--json` | emit the structured envelope |

Without `--dry-run` the run is written to
`<workspace>/memory/evidence/websites/<domain>/runs/<run-id>/` as `report.json`
and `receipt.json`. Evidence is append-only, so an existing run folder is never
overwritten.

## Rules

Ten rules, each a pure function of the extracted page fields. A rule never sees a
verdict about the page — that is what keeps a measurement from confirming a
conclusion it was handed.

| rule_id | Severity | Fires when |
|---|---|---|
| `title.missing` | critical | no `<title>`, or it is empty |
| `description.missing` | critical | no `meta[name=description]` (not on a 404 page) |
| `description.short` | warning | description shorter than 30 characters |
| `description.long` | warning | description longer than 300 characters |
| `canonical.missing` | critical | no `link[rel=canonical]` (not on a 404 page) |
| `canonical.mismatch` | critical | canonical does not start with the configured site base URL |
| `lang.missing` | critical | no `lang` on `<html>` |
| `h1.missing` | critical | no `<h1>` |
| `h1.multiple` | warning | more than one `<h1>` |
| `og.title.missing` | critical | no `meta[property=og:title]` |
| `og.image.missing` | critical | no `meta[property=og:image]` |
| `og.description.missing` | warning | no `meta[property=og:description]` |
| `twitter.card.missing` | warning | no `meta[name=twitter:card]` |
| `main.missing` | warning | no `<main>` landmark |
| `skiplink.missing` | warning | no link to `#main-content` and no `.skip-link` |
| `img.alt.missing` | critical | one or more `<img>` without an `alt` attribute |
| `robots.noindex` | warning | page marked `noindex`, unless suppressed |

## Finding shape

Each finding is atomic:

```json
{
  "rule_id": "img.alt.missing",
  "severity": "critical",
  "message": "1/2 <img> missing alt attribute",
  "observed": 1,
  "expected": 0,
  "page": "index.html",
  "location": "body > img"
}
```

`observed` is the extracted value, `location` is a structural pointer. Neither
carries page prose beyond the value itself.

## Adding a rule

1. Add a function to `audit.py` taking `(page, ...) -> list[finding]`.
2. Register it in `RULES` — position fixes the report order.
3. Add a case to `tests/test_on_page.py`.
4. Re-run the parity test. If the rule changes what a human would be told, that
   is a deliberate behaviour change, not a refactor: say so in the commit and
   update `post-migration-seo-checklist.md` if it is documented there.

## Provenance

Ported from `hugo-wizard/scripts/audit-site-seo.py`. Rule conditions, severities
and message texts are unchanged, so `tests/test_parity.py` compares the two
implementations' output and fails on any divergence. That test skips itself once
the original is deleted.