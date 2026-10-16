---
title: Source log
description: Every source behind a rule in this skill, with what it taught and which file cites it.
evidence_level: normative
applies_to: [website-optimizer]
last_verified: 2026-10-15
review_due: 2027-01-15
---

# Source log

The rule set exists so that an agent can tell whether a rule is a specification,
a strong recommendation, or an observation. This file is where that comes from.

## How to read the provenance column

| Value | Meaning |
|---|---|
| `consulted` | the source was opened directly and read |
| `inherited` | the source was cited by an existing workspace document and has **not** been re-opened while writing this file |

Anything marked `inherited` is a claim about a source nobody in this skill has
recently read. Before building on such a rule, open the source. That is the
point of recording which is which: an `inherited` anchor is a lead, not a
verification.

## Sources

| Source | Provenance | Consulted | Taught | Cited by |
|---|---|---|---|---|
| [Open Graph protocol](https://ogp.me/) | `inherited` via `hugo-wizard/memory/references/chores/seo-opengraph-schema-accessibility-checkliste.md` | 2026-05-11 (by that document) | The `og:` property set: `og:title`, `og:description`, `og:image`, `og:image:alt`, `og:url`, `og:type`, `og:locale`, `og:site_name` | `seo-core.md`, `images.md` |
| [Twitter Cards](https://developer.x.com/en/docs/twitter-for-websites/cards/overview/abouts-cards) | `inherited` via the same chore | 2026-05-11 | `twitter:card`, `twitter:title`, `twitter:description`, `twitter:image`, `twitter:image:alt` | `seo-core.md` |
| [schema.org](https://schema.org/) | general knowledge | — | The vocabulary of `@type`; that JSON-LD is the serialisation format | `structured-data.md` |
| [MDN: `<img>` alt](https://developer.mozilla.org/docs/Web/HTML/Reference/Elements/img#alt) | general knowledge | — | `alt` is required unless the image is purely decorative, in which case `alt=""` is correct | `images.md`, `accessibility.md` |
| [W3C WCAG](https://www.w3.org/TR/WCAG22/) | general knowledge | — | Conformance levels A/AA; the four principles | `accessibility.md` |
| [web.dev Core Web Vitals](https://web.dev/articles/vitals) | general knowledge | — | LCP, INP, CLS and their thresholds | `performance.md` |
| [llmstxt.org](https://llmstxt.org/) | `inherited` via `hugo-wizard/memory/references/chores/add-llms-txt.md` | 2026-08-25 (by that document) | The `/llms.txt` structure: H1, blockquote summary, free notes, H2 link sections; the `## Optional` block may be dropped under a tight context budget | `llm-visibility.md` |
| [favicon.io HTML guide](https://favicon.io/html-favicon/) | `inherited` via `hugo-wizard/memory/references/chores/add_favicon.md` | 2026 (by that document) | The icon set a modern site ships and the head tags that reference it | `images.md` |
| [Yoast: SEO for a new website](https://yoast.com/seo-for-a-new-website-the-very-first-things-to-do/) | `inherited` via `hugo-wizard/memory/references/chores/seo-launch-und-content-leitfaden.md` | 2026-08-25 (by that document) | The first-external-link principle, the three-part snippet formula, cornerstone content, AI-search preparation | `seo-core.md`, `indexing.md` |
| [Yoast: optimising content for LLM comprehension](https://yoast.com/how-to-optimize-content-for-llms/) (Carolyn Shelby) | `inherited` via `hugo-wizard/memory/references/chores/llm-lesbare-inhalte.md` | 2026-09-15 (by that document) | Page structure for extractability: answer first, one idea per paragraph, lists for steps, question-shaped headings | `llm-visibility.md` |
| [Hugo sitemap and robots output](https://gohugo.io/configuration/sitemap/) | general knowledge | — | That `enableRobotsTXT` alone emits no `Sitemap:` directive, so a `layouts/robots.txt` template is required | `static-sites.md` |
| [Google: localized versions of your page](https://developers.google.com/search/docs/specialty/international/localized-versions) | `consulted` | 2026-10-16 | The three annotation methods and that they are equivalent; the reciprocal rule, and that an incomplete set is tolerated *pairwise* while completeness is the guideline; `x-default` takes no language code; codes come from ISO 639-1 + ISO 3166-1 alpha-2 only, so `es-419` is unsupported; alternate URLs must be fully qualified; **Google uses neither `hreflang` nor the `lang` attribute to detect a page's language**. Three claims in this file's first draft were wrong until the page was opened. | `i18n.md` |
| [ISO 639-1 language codes](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes), [ISO 3166-1 alpha-2 region codes](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2), [ISO 15924 scripts](https://unicode.org/iso15924/iso15924-codes.html) | `consulted` via the Google page | 2026-10-16 | The three lists a valid `hreflang` value may draw from | `i18n.md` |
| [Google: managing crawling of faceted navigation URLs](https://developers.google.com/crawling/docs/faceted-navigation) | `consulted` | 2026-10-16 | The per-parameter table (`page`/`item-id`: every URL; sort/track: one representative; narrowing: not all); that `rel=canonical` may reduce crawl volume *over time* rather than removing URLs; that `rel=nofollow` limits discovery but not crawling, and only a `robots.txt` disallow prevents crawling; the `/filtering/` directory pattern | `pagination.md` |
| [Google: pagination with rel=next and rel=prev](https://developers.google.com/search/blog/2011/09/pagination-with-relnext-and-relprev) | `inherited` | — | The original markup guidance, still linked from the faceted-navigation page above — which is why that page contradicts current practice | `pagination.md` |
| [Yoast: Google says it doesn't use rel=prev/next](https://yoast.com/google-doesnt-use-rel-prev-next-for-pagination/) | `inherited` | — | Secondary confirmation that rel=next/prev stopped being an indexing signal in 2019. The announcement itself was not opened; the 2011 page above is what Google still links. | `pagination.md` |

## Unverified notes

Claims with no source behind them. They are recorded so they are not silently
promoted into rules later. Nothing below may appear in a reference file as an
assertion.

| Claim | Status | Note |
|---|---|---|
| Google indexes a new site faster after one external link from an indexed domain | `partially_supported` | Widely repeated in practitioner sources; Google states no such guarantee. Treated as a low-risk, high-cost-to-ignore practice. |
| Search Console shows "sitemap could not be read" for 24–72 h after submission | `observed` | Seen repeatedly in `hugo-wizard` runs across several domains. Mechanism is Google's asynchronous crawl scheduler, which is documented in general terms but not as this behaviour. |
| A single `<h1>` is required | `contested` | The HTML specification and accessibility practice favour one `<h1>`; Google has stated the number of `h1`s does not matter for ranking. Recorded because a rule here is a judgement, not a ranking fact. |
| A language page should name itself as its own canonical | `partially_supported` | Consistent with what `hreflang` and `rel=canonical` each mean, and the practitioner consensus, but not stated by Google's localized-versions page. Recorded as practice in `i18n.md` rather than as a rule. |

## Re-verification

When a `references/` file is revised, its `last_verified` moves only when the
sources behind it were actually re-read. Re-stamping the date without opening
the source is the failure this log exists to prevent.