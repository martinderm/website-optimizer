# `performance` capability

What the build weighs and what blocks its first paint: per-page weight against
the budgets `references/performance.md` names, parser-blocking scripts,
`@font-face` blocks without `font-display`, preloads pointing at nothing, and
the foreign origins the markup references.

Weight is per page — every page loads what it declares. Everything else is
keyed on its target (D52): one blocking script, one font file, one missing
preload target, one foreign origin, each naming the pages involved.

## Interface

```
python scripts/wo.py performance [--config FILE] [--strict] [--run ID] [--dry-run] [--json]
```

Add `"performance"` to `[audit] capabilities` in `site.optimizer.toml` to switch it on.

## Static only, and it refuses rather than pretending

`--live` is accepted and raises. File sizes exist only in a build; a crawl
would force every shared stylesheet to be guessed at and every file size
approximated. That report would describe the crawl and call it the site — the
D32 failure with a scale attached. The error says so and names the way back:

```
python scripts/wo.py performance          # built output, no --live
```

## Rules

| rule_id | Severity | Fires when |
|---|---|---|
| `perf.budget_exceeded` | warning | a page's stylesheets or scripts, its largest image, or a font file it loads weigh more than the reference budgets (CSS 100 KB, JS 200 KB, hero image 200 KB, font 100 KB per file) |
| `perf.render_blocking_script` | warning | a classic `<script src>` in `<head>` has neither `defer` nor `async` |
| `perf.font_display_missing` | warning | an `@font-face` block in a served stylesheet declares no `font-display` |
| `perf.preload_target_missing` | critical | a `<link rel="preload">` points at a URL the build does not serve |
| `perf.third_party_origin` | warning | markup references a foreign origin (one finding per origin, with a page count) |

Bytes are bytes on disk. Compression shrinks text in transit, so a file over
budget on disk is over budget served; one under it may still be close. The
finding reports the measured number, not the wire.

## What this capability does not see

- **Which image is the hero.** Hero detection from markup alone is a heuristic,
  and a heuristic finding is a false positive with a schedule. The rule reads
  conservatively instead: the *largest* image on the page is weighed against
  the hero budget. Under it, every image is; over it, the page has an
  image-weight problem whatever the hero is.
- **Whether a third party is justified.** A tag manager the team chose and a
  tracker someone pasted in 2019 look identical in markup. The rule names each
  origin once with a page count; justification stays human, as the reference
  asks ("named and justified, individually").
- **Subdomains as first-party.** `static.example.com` is reported even when the
  site owns it: the markup cannot show whether a subdomain is the site's own
  CDN or a CNAME to someone else's infrastructure. Same bare host with or
  without `www` is one site (D38); anything else is inventory.
- **Missing files.** A declared path the build does not contain is `links`' or
  `images`' finding. These rules skip it: a 404 never reads as lightweight
  here, and weight can never go negative.
- **The 404 page.** It is not a view, so it is neither weighed nor scanned.
- **Inline `<style>` and `<script>` bodies.** They are authored code, and
  `Page` retains no authored code (D13). A `@font-face` in an inline `<style>`
  block is therefore not read — only served stylesheets are.
- **Lab and field numbers.** LCP, INP, CLS themselves and caching headers need
  measurement this tool does not do. That half of `references/performance.md`
  stays advice until a workspace brings a trusted lab or field source.
- **Relative stylesheet/script/image paths** resolve against the page's
  directory, the way a browser resolves them — there is no unresolvable case
  here, only external ones, which belong to the third-party rule.
