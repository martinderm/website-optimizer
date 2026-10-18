# `links` capability

The internal link graph of a built site: which links point at URLs the build does
not serve, which pages nothing reaches, and how deep the site runs.

Read over the whole build directory rather than one page, because a link is a
relation between two pages and no single-page view can see one.

## Interface

```
python scripts/wo.py links [--config FILE] [--strict] [--run ID] [--dry-run] [--json]
```

Add `"links"` to `[audit] capabilities` in `site.optimizer.toml` to switch it on.

## Static only, and it refuses rather than pretending

`--live` is accepted and raises. A graph needs to know every page the site
serves; a crawl sees the pages inside its limit and nothing else, so every page
beyond the limit would read as unreachable and every link to it as broken. That
report would describe the crawl and call it the site — D32's failure with a graph
attached. The error says so and names the way back:

```
python scripts/wo.py links          # built output, no --live
```

## Rules

| rule_id | Severity | Fires when |
|---|---|---|
| `link.target_missing` | critical | an internal link points at a URL the build does not serve |
| `link.unreachable` | warning | no internal link reaches a built page from the home page |
| `link.depth` | warning | a page sits `DEPTH_LIMIT` (4) or more clicks from the home page |

Findings are graph findings, so `subject` is not always a page: for
`link.target_missing` it is the **URL that is missing**, for the other two it is
the page.

## One missing target, one finding

A broken link in a site-wide template is one defect on one URL. Reporting it once
per linking page turns a single fixable line into a screenful of identical
criticals — the failure D38 named, where a reader who sees the same thing twelve
times stops reading the rule. So the finding is keyed on the target, and names
the pages that link it:

```
1 page(s) link to /por-baixo-da-pele-outra-pele, which the build does not serve:
projects/underneath-the-skin-another-skin/index.html.
```

On the reference site this is what made the difference between one finding and
one finding, and it is also what makes `compare` useful here: a broken URL
appearing is one regression, not one per page that happens to link it.

## Reachability is transitive

`link.unreachable` is a breadth-first walk from `/`. A page linked only from
another unreachable page is unreachable too, which is what "reachable only from
the sitemap" actually means. Consequences worth knowing:

- `404.html` is exempt. Nothing is meant to link to it.
- Two pages that link only each other are both unreachable.
- A build with no `index.html` has no root to measure from, so the two graph
  rules are skipped rather than reporting every page as an orphan.

## What the graph does not see

- **Anchor text.** `Page.links` carries the target, not the words: an anchor's
  text is authored prose and D13 keeps prose out of the extractor. So the
  anchor-text guidance in `references/internal-linking.md` — "read more" in body
  content, ten identical links to one target — is a rule this tool **cannot**
  measure. That is stated there rather than left to be discovered.
- **Redirects.** A link to a redirect *source* is answered, not missing: the
  build's `_redirects` and `.htaccess` are read, and their sources count as
  served. `_redirects` paths match exactly, `*` splats by prefix; `Redirect`
  directives match exactly; R-flag `RewriteRule` patterns match as regexes,
  the way the server matches them (verbatim anchors, search semantics, `NC`
  honored). Such a link draws no graph edge — where the redirect leads is
  unknowable statically, so reachability and depth never see it.
- **What redirect acceptance does not do.** Whole-site rules (HTTPS/www
  canonical), bare `.*` catch-alls and `/*` splats never accept: they answer
  everything and route nothing, and blanket-acceptance would silence the
  whole rule. Non-redirect rewrites are not redirects. `RewriteCond` lines
  are not evaluated, so conditional rules may accept more than the server
  would. `:placeholder` segments in `_redirects` and `RedirectMatch`
  directives are not read. Whether a redirect leads somewhere useful stays
  `redirects`' live question.
- **Pages excluded by `ignore_path`.** They are not audited, so their links are
  not followed: a page reachable only from `admin/` reads as unreachable.
- **Links added by JavaScript.** Only what the markup contains is in the graph.
- **Whether a target is *right*, only whether it exists.** A link to the wrong
  page that happens to exist is invisible here, deliberately: that is a content
  decision, not a measurement.
- **Fragment targets.** `/a/#section` resolves to `/a/`; whether `#section`
  exists in that document is not checked.
- **One URL with two pages.** A build holding both `a.html` and `a/index.html`
  serves `/a` twice; the graph follows whichever it reads first and does not
  report the collision. Hugo and WordPress do not emit that pair.
- **A relative link whose first segment contains a colon** (`foo:bar/baz`) is read
  as a URL scheme and skipped, because that is what a browser would do.
