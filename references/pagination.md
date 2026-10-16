---
title: Pagination and faceted navigation
description: Series pages, filter combinations, and the four levers that decide what crawls.
evidence_level: normative
support_level: partially_supported
applies_to: [website-optimizer]
references:
  - https://developers.google.com/crawling/docs/faceted-navigation
  - https://developers.google.com/search/blog/2011/09/pagination-with-relnext-and-relprev
  - https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls
  - https://yoast.com/google-doesnt-use-rel-prev-next-for-pagination/
last_verified: 2026-10-16
review_due: 2027-04-16
---

# Pagination and faceted navigation

**Support note.** The guidance here has moved more than once, and it contradicts
itself in places — including inside Google's own documentation, which is noted
below rather than smoothed over. Treat the mechanics as `partially_supported` and
re-read the sources before relying on a specific one.

## Two different problems that get one name

- **Pagination** is a series: `/news/`, `/news/page/2/`, `/news/page/3/`. Finite,
  knowable, the same pages for every visitor.
- **Faceted navigation** is a product: filters multiplied by each other. The URL
  space is unbounded, and which of it exists depends on what a filter combination
  would return.

They are conflated constantly, and the fixes are not the same. Pagination is a
decision about *which pages in a series should rank*. Facets are a decision about
*how much of an infinite space should exist at all*.

## Pagination

A series of listing pages has two defensible shapes. Pick one and apply it
everywhere:

| Choice | Effect |
|---|---|
| **Self-referencing canonical** on every page of the series | every page can rank, each with its own title; link signals are spread across the series |
| **Canonical from each page to a view-all page** | signals consolidate on one URL; the individual pages are not meant to rank |

Google's faceted-navigation page recommends the second, and it is the one that
needs a real "view all" URL to exist. The first is the commoner practice on
editorial sites. They optimise different things, and mixing them across a site is
the mistake: a series where page 2 canonicalises to page 1 *and* page 3 does not
tells a crawler two stories about the same series.

**Do not block `page` in `robots.txt`.** Google's own parameter table lists `page`
as a parameter where *every* URL should be crawled. Paginated pages are how a
crawler reaches the older items.

**Do not `noindex` page 1** to "fix" duplication. Page 1 is the series.

## The `rel="next"` / `rel="prev"` contradiction

Worth knowing, because guides disagree and both are quoting Google.

- Google announced in 2019 that `rel="next"` and `rel="prev"` are **no longer an
  indexing signal**. Their systems infer pagination from links themselves.
- Google's **own faceted-navigation page still lists them** as an option for
  consolidating paginated content, because that page descends from material
  written in 2014.

Neither is a reason to remove pagination from a site, and neither is a reason to
add the markup hoping for a ranking effect. Link the pages to each other — a
series that is not reachable in order is the actual defect.

## Faceted navigation and the crawl space

The failure is a URL space that grows without anyone deciding it should:

```
/category/?color=red
/category/?color=red&size=large
/category/?color=red&size=large&sort=price
/category/?session-id=abc123&color=red
```

Each is its own URL, and a crawler that finds them will spend its budget on
combinations nobody searches for.

**Rule one: only create a URL when it has results.** A filter combination that
returns nothing should not be a link at all — grey out the option, or 404 the
page. That is where most of the waste goes, and it is a template decision.

**Rule two: decide per parameter, not per site.** Google's own table:

| Parameter kind | Example | What should be crawled |
|---|---|---|
| specifies content | `item-id`, `category-id` | every URL |
| paginates | `page` | every URL |
| sorts | `sort`, `SortOrder` | one representative value |
| tracks | `session-id`, `trackingId` | one representative URL |
| narrows | `color`, `size`, `price` | not all of them |

## The four levers, and what each actually does

- **`rel="canonical"`** — points at the version that should rank. It is a hint,
  and Google's page notes it may *decrease crawl volume* of the non-canonical
  versions **over time**. It does not stop crawling, and it does not remove a URL
  from the index.
- **`robots.txt`** — stops **crawling**, not indexing. A disallowed URL that is
  linked from elsewhere can still appear as a bare link. This is the trap: a
  disallowed page's `noindex` is never seen, because the page is never fetched.
  Blocking and `noindex` cannot both work on the same URL.
- **`rel="nofollow"`** on filter links — a hint since 2019, not a directive.
  Google's page says it "minimizes the crawler's discovery" of unnecessary URLs
  but "doesn't prevent the unnecessary URLs from being crawled (only a
  `robots.txt` disallow prevents crawling)".
- **A separate directory per unnecessary parameter** (`/filtering/...`) — the
  pattern Google's page recommends for combining option one with a single
  `Disallow` rule, because it makes the blockable set enumerable.

**Use one lever per URL.** `canonical` plus a `Disallow` on the same URL means the
canonical is never read.

## What a build audit can and cannot see

**Can be seen**, because it is in the built output:
- whether a listing series links to the next page at all, and whether the series
  is reachable in order
- whether every page of a series carries a canonical, and whether the series is
  internally consistent (all self-referencing, or all pointing at one view-all)
- whether a parameterised URL is linked with `rel="nofollow"`
- whether a sitemap lists parameterised URLs, which the guidance says it should
  not

**Cannot be seen:**
- whether a filter combination *returns results*, which needs the query behind it
- how large the URL space actually is, since most of it is generated at request
  time and never appears in a crawl
- whether the choice of which parameters matter is right — that is a business
  decision

The second item is the reason this is not a capability. A build shows the pages
that exist; the problem is the pages that would exist if asked. That is the same
boundary `redirects` runs into, and D47's answer applies: build it when a real
site needs it and supplies the input.

## Checklist

- [ ] One pagination strategy, applied to every series
- [ ] Canonical present on every page of a series, self-consistent across it
- [ ] `page` not blocked in `robots.txt`
- [ ] Page 1 of every series indexable
- [ ] No URL created for a filter combination with no results
- [ ] Parameters sorted and encoded consistently (`key=value&`, no brackets)
- [ ] `canonical` and `Disallow` never used on the same URL
- [ ] `rel="nofollow"` on links to unnecessary filter parameters
- [ ] Sitemaps contain canonical URLs only, no parameter combinations
- [ ] The series is reachable in order by following links, not only by URL guess
