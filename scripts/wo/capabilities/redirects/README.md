# `redirects` capability

Probes the live site with the redirect rules its configuration file declares, and
records what the server actually did.

## Interface

```
python scripts/wo.py redirects [--config FILE] [--strict] [--dry-run] [--json]
```

Configuration lives in `site.optimizer.toml`:

```toml
[audit]
capabilities = ["on-page", "redirects"]

[redirects]
file = "static/.htaccess"   # .htaccess, _redirects, .json, .csv, .tsv
check_target = true         # also require the destination to answer 200
timeout = 10
```

This capability performs **live network requests**. `on-page` does not.

## What it does

1. Reads rules from the configured file. Apache `.htaccess`, Cloudflare Pages /
   Netlify `_redirects`, and JSON or CSV mapping files are understood; the type is
   detected from the filename, then from the content.
2. Turns each rule into a URL it can actually request. A wildcard rule is probed
   with a sample slug and marked as a wildcard.
3. Requests the source URL with a handler that surfaces redirects instead of
   following them, and compares the `Location` header against the configured
   target.
4. Unless the rule is a wildcard, requests the destination and requires `200`.
5. Writes one `checks` row per rule, and a finding for each failure.

Wildcard rules are exempt from step 4 on purpose: the destination was a sample
slug that does not exist, and a 404 there would be a false failure.

**Response bodies are never read.** Only the status line and the `Location`
header are consumed. A redirect target is arbitrary content, and this capability
deliberately has no path by which a server's HTML could reach the report (D13).

## Findings

| rule_id | Severity | Fires when |
|---|---|---|
| `redirect.location_mismatch` | critical | a redirect happened, but points somewhere else than configured |
| `redirect.status_unexpected` | critical | the source URL answers without a redirect status |
| `redirect.unreachable` | critical | the source URL could not be reached at all |
| `redirect.target_unreachable` | critical | the redirect is correct, but the destination does not answer 200 |
| `redirect.failed` | warning | the rule failed for a reason not covered above |

A passing rule produces a row in `checks`, never a finding. The verdict is
derived from the rows.

## When the rules are not in a file

This capability reads rules from a **file**. On a platform that keeps them
elsewhere — WordPress on nginx stores them in the database — there is nothing to
point it at, and the honest move is to switch it off for that site rather than
let it report "no rules found" about a site that has redirects. Switching it off
means removing it from `[audit] capabilities`, with the reason written in the
config next to the omission.

The trade-offs between the possible sources — reading the database, reading the
server config, checking a URL list against the live server — are weighed in
`references/redirects.md` under *When the rules are not in a file*. That file is
the right home for it: it is a per-site decision, and the decision belongs to the
site, not to this capability.

**Whatever a future source turns out to be, it has to name itself.** The report
already carries `source.kind`; a new source is a new value there, and a run that
cannot say where it read from is indistinguishable from a run that found nothing.

## Adding a file type

Add a parser in `parse.py` returning `list[tuple[source, target, wildcard]]`, a
branch in `load_mappings`, and a case in `tests/test_redirects.py`. Keep the
tuple shape — `dedupe` and `probe` both depend on it.

## Provenance

Ported from `hugo-wizard/scripts/verify-redirects.py`. Rule loading, status
handling, retry behaviour, wildcard exemption and finding derivation are
unchanged. Parity was verified against the original over the 53 live rules of a
real site: 0 findings lost, 0 invented.