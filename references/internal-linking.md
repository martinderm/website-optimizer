---
title: Internal linking and architecture
description: Cornerstone content, anchor text, orphan pages, and the site structure crawlers follow.
evidence_level: normative
support_level: fully_supported
applies_to: [website-optimizer]
references:
  - https://developers.google.com/search/docs/fundamentals/seo-starter-guide
  - https://yoast.com/seo-for-a-new-website-the-very-first-things-to-do/
last_verified: 2026-10-15
review_due: 2027-01-15
---

# Internal linking and site architecture

Internal linking is the cheapest ranking lever available and the most neglected.
It tells a crawler what a site is *about*, not just what is on it.

## Cornerstone content

Pick the two or three pages that represent the main offer — the pages a
prospect should land on. These are the cornerstones, or pillars.

- Every article and every subpage links **up** to the relevant cornerstone.
- Cornerstones link **down** to their supporting content.
- The resulting graph makes the topic hierarchy explicit, which is what a
  crawler infers relevance from.

A cornerstone that nothing links to is a page the site has not decided matters.

## Anchor text

The words in a link describe its target to a reader and to a crawler.

- Descriptive: "how to test soil pH before planting".
- Useless: "read more", "click here", "here", a bare URL.
- Useless in a list of ten identical links to the same target: "this article".

Context matters — the surrounding sentence can supply meaning the anchor alone
does not. Links inside a sentence with descriptive anchors are better than links
in a navigation list, even if the navigation exists too.

## Orphan pages

A page reachable only from the sitemap, or from no internal link at all, is an
orphan. Orphans are crawled rarely and rank poorly.

Every indexable page must be reachable from at least one of:

- the main navigation,
- a category or listing page,
- an internal link in content,
- a breadcrumb (and then a `BreadcrumbList` in structured data).

## Breadcrumbs

```html
<nav aria-label="Brotkrumen">
  <ol>
    <li><a href="/">Start</a></li>
    <li><a href="/works/">Werke</a></li>
    <li aria-current="page">Detail</li>
  </ol>
</nav>
```

- An ordered list, not a pile of separators.
- The last item is the current page and is not a link.
- `aria-current="page"` on it.
- `aria-label` on the `<nav>` distinguishes it from other navigation regions.

Breadcrumbs show a crawler the path from the homepage, which is how depth is
discovered for deep URLs.

## URL structure

- Short, readable, stable, lowercase, hyphen-separated.
- Reflect the hierarchy: `/category/subcategory/page/`.
- **Never change a URL without a permanent redirect** (`redirects.md`).
- Parameters belong on listing pages, not on content pages. Two URLs for one
  page means one of them should be canonicalised or blocked.

## Depth and crawl budget

Pages four or more clicks from the homepage are crawled less often. Flatten
where the content allows it: a category page that lists its items is more
valuable than a hierarchy of subcategories.

## Page purposes

One page, one purpose. A page that targets three unrelated intents will have a
title, a description, and a heading that satisfy none of them well.

## Checklist

- [ ] Two or three cornerstones defined and linked from adjacent content
- [ ] Anchor texts describe their target; no "read more" in body content
- [ ] Every indexable page reachable from navigation, listing, or a link
- [ ] Breadcrumbs as an ordered list with `aria-current="page"`
- [ ] URLs short, lowercase, hierarchical, and unchanged since launch
- [ ] No orphan pages in the sitemap that nothing links to
- [ ] No duplicate content reachable under multiple URLs