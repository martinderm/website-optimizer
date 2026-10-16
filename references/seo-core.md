---
title: SEO core — titles, descriptions, canonicals, internal linking
description: The on-page signals every page carries, and the platform-neutral rules for setting them.
evidence_level: normative
support_level: fully_supported
applies_to: [website-optimizer]
references:
  - https://ogp.me/
  - https://developer.x.com/en/docs/twitter-for-websites/cards/overview/abouts-cards
  - https://yoast.com/seo-for-a-new-website-the-very-first-things-to-do/
  - https://developer.mozilla.org/docs/Web/HTML/Element/title
last_verified: 2026-10-15
review_due: 2027-01-15
---

# SEO core

Platform-neutral. Static and dynamic sites follow the same rules here; only the
*place* to set them differs.

## Title

Every page has a `<title>`, and it is the single strongest on-page signal.

- **Present and non-empty.** An empty `<title>` is the defect, not a short one.
- **Unique per page.** Two pages sharing a title means the second page is
  discarded or ranked as a duplicate of the first. On a generated site this
  usually means a missing `title` front-matter value.
- **Leading element first.** Match the order of the audience's intent, not the
  order of the brand name.
- Length has no specification threshold. A title that is truncated in the result
  is a title whose first ~60 characters fail to identify the page.

## Meta description

The description is not a ranking factor in itself. It is the advertisement for
your ranking, and it is generated from the page's own content unless you write
it.

**The three-part formula** — keyword, concrete benefit, call to action:

```
Meta description = focus keyword + concrete benefit + call to action
```

- Weak: "Gardening is fun. We'll show you how."
- Strong: "Want to grow your own vegetables? Ten beginner-friendly tips for a
  productive garden in a few weeks — start now."

Rules:

- Unique per page, written for the searcher rather than the brand.
- 30 to 300 characters is the working band this skill's auditor enforces. Under
  30 wastes space; over 300 is truncated in most result layouts.
- Never leave it to the generator if the page's own text would make a poor
  snippet. The generator picks the first plausible sentence, which is often the
  navigation sentence.

## Canonical URL

- **Absolute, self-referencing, one per page.** A relative canonical is legal but
  fragile across environments.
- The canonical must match the domain that is actually canonical for the site,
  and the non-canonical host must redirect there permanently (see `caddy`).
- When auditing, `[site] url` must be **that** domain — the one the site
  canonicalises to, not the one that redirects to it. The audit compares against
  what the config says. `www` against apex is the commonest WordPress
  misconfiguration there is, and configuring it the wrong way produces the same
  finding on every page, which is worse than no finding at all.
- A canonical pointing at another domain that does not redirect hands ranking
  authority away and usually indicates a staging URL that escaped into
  production.
- Paginated and filtered views: canonical to the first page, or leave unfiltered
  variants out of the index — but never canonicalise a filter combination to a
  page that does not exist.

## Open Graph and Twitter Cards

These control how a shared link renders. They are `critical` in the auditor for
`og:title` and `og:image`, `warning` for the rest, because a missing tag does
not harm search — it only makes shares look broken.

| Tag | Notes |
|---|---|
| `og:title` | defaults to the page title if absent; set it explicitly to control the wording |
| `og:description` | same relationship to `og:title` |
| `og:image` | absolute URL; a relative path is not resolved by most scrapers |
| `og:image:alt` | alt text for the preview image — set it, it is part of the spec |
| `og:url` | the canonical URL, not the shared URL's tracking parameters |
| `og:type` | `website` for a normal page, `article` for a dated post |
| `og:locale` | `de_AT`, not `de-AT` |
| `og:site_name` | constant per site, useful when the page title is long |
| `twitter:card` | `summary_large_image` when a good image exists |
| `twitter:image` | without it, X falls back to Open Graph images |

One global 1200×630 image is the minimum viable setup. A site with covers can
resolve per page with a global fallback.

## Internal linking and cornerstone content

- **Define two or three pillar pages** that represent the main offer. Everything
  adjacent links up to them.
- Link with descriptive anchor text. "Read more", "here", and bare URLs tell a
  crawler nothing about the target.
- Every page should be reachable from the navigation, a category page, or an
  internal link. An orphan page is a page no crawler prioritises.
- Breadcrumbs help users and machines alike; add `BreadcrumbList` structured
  data alongside them (`structured-data.md`).

## Heading structure

- Exactly one `<h1>` per page is the accessibility and authoring convention.
  Its ranking effect is contested — see `sources.md`.
- Headings must not skip levels, because screen readers navigate by heading
  level.
- **Headings with action verbs** (`## Step 1: test the soil pH before planting`)
  extract better in AI answer surfaces than nominal headings (`## Preparation`),
  because they state what the section delivers.

## Checklist

- [ ] Title present, unique, intent-led
- [ ] Description unique, within the band, keyword + benefit + action
- [ ] Canonical absolute, self-referencing, matching the canonical host
- [ ] `og:title`, `og:image`, `og:url`, `og:type` set
- [ ] `og:image:alt`, `twitter:card` set
- [ ] Exactly one `<h1>`, no skipped levels
- [ ] Pillar pages defined and linked from adjacent content
- [ ] Anchor texts describe their target

Verify mechanically with `python scripts/wo.py on-page`; the rules are listed in
`scripts/wo/capabilities/on_page/README.md`. Structured data is checked by
`wo.py schema`, image delivery by `wo.py images`.