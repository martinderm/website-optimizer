# `crawler-files` capability

The documents a site publishes about itself: `robots.txt`, the XML sitemap, and
`llms.txt`. Three files nobody reads until something has been wrong for months.

## Interface

```
python scripts/wo.py crawler-files [--config FILE] [--strict] [--run ID] [--dry-run] [--json]
python scripts/wo.py crawler-files --live        # fetch the three from the site
```

Add `"crawler-files"` to `[audit] capabilities` in `site.optimizer.toml`.

## Rules

| rule_id | Severity | Fires when |
|---|---|---|
| `robots.missing` | warning | no `robots.txt` |
| `robots.blocks_site` | critical | `Disallow: /` under `User-agent: *` |
| `robots.blocks_asset` | warning | a `Disallow` rule cuts off CSS, JS, images, fonts or uploads |
| `robots.sitemap_missing` | warning | `robots.txt` names no sitemap |
| `sitemap.missing` | warning | no sitemap was found |
| `sitemap.unreadable` | critical | something answered, and it was not a sitemap |
| `sitemap.empty` | critical | a sitemap that parses and lists nothing |
| `sitemap.absent_page` | warning | **build only** — a built page appears in no sitemap |
| `sitemap.unsupported_url` | critical | **build only** — the sitemap lists a URL the build does not serve |
| `llms.missing` | warning | no `llms.txt` |
| `llms.empty` | warning | `llms.txt` contains no links |

## Two sources, one set of rules

In static mode the three are files in the build output; with `--live` they are
three URLs. Nothing above the resolver can tell the difference — the same
arrangement `pages` gives the page-reading capabilities (D33), applied to
documents instead of pages.

**Unlike `links`, this capability does not refuse a crawl.** A `Disallow: /` is
worth finding on any site, including one with no build output at all, so a live
run reports less rather than nothing: the two build-only rules leave `rules_run`,
which is how a reader can tell they were skipped instead of passing.

The live path fetches the three documents, following a sitemap index to its
children. It renders no pages and needs no browser.

## No coverage claim from a sitemap that could not be read *in full*

This is the one rule interaction worth knowing about. If the sitemap is missing,
unreadable, empty - **or an index whose children only partly loaded** - the two
coverage rules are skipped entirely, because the alternative is a sitemap that
fails to parse making every page on the site look absent from it: the loudest
wrong answer available here, arriving as a hundred warnings.

The partial case is the harder one, because the child that *did* load looks like a
complete sitemap. It was found by an independent review of this file rather than
by a test; the test was written with the fix, and it fails without it.

`checked_pages: 0` in the summary is therefore not "no pages" but "no coverage was
claimed" - and where coverage *was* claimed it counts the pages actually compared,
so the 404 page and any `noindex` page are not in it.

## What it does not check

- **Whether the sitemap is *complete* in intent.** A page can legitimately be
  absent: it may be `noindex`, or not meant to be indexed. The 404 page and any
  page carrying `noindex` are exempt from `sitemap.absent_page`; every other
  absence is raised as a question, not a verdict.
- **Whether the pages in the sitemap are the *right* pages.** `lastmod` accuracy,
  `changefreq` and `priority` are not read. Google ignores the last two, and the
  first is only as good as the generator.
- **Whether a crawler obeys `robots.txt`.** Nothing here fetches anything as a
  search engine would.
- **Anything about indexing itself.** `indexing.md` also covers Search Console,
  the URL-prefix rule and Bing Webmaster Tools; those need a console, not a
  fetch, and the reference says so next to the rules this capability does check.
- **Blocked *paths* that are content.** `robots.blocks_asset` knows the usual
  delivery prefixes. A site blocking `/werke/` is telling crawlers something, and
  only a person can say whether it meant to.
