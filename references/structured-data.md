---
title: Structured data
description: JSON-LD, the @graph pattern, choosing a type, and validating the result.
evidence_level: normative
support_level: fully_supported
applies_to: [website-optimizer]
references:
  - https://schema.org/docs/full.html
  - https://json-ld.org/
  - https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data
last_verified: 2026-10-15
review_due: 2027-01-15
---

# Structured data

JSON-LD is the serialisation to use. Microdata and RDFa still work; JSON-LD is
scriptable, separable from the markup, and survives template changes.

## Minimum viable set

```json
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "WebSite",
      "@id": "https://example.com/#website",
      "name": "Example",
      "url": "https://example.com/"
    },
    {
      "@type": "Organization",
      "@id": "https://example.com/#organization",
      "name": "Example GmbH",
      "url": "https://example.com/"
    }
  ]
}
```

Two nodes are enough for most sites: the site and the organisation or person
behind it. Everything else is earned by a feature the site actually has.

## The @graph pattern

A single `@graph` with stable `@id` values lets the nodes reference each other
instead of duplicating data:

```json
{ "@type": "WebPage", "@id": "https://example.com/about/#webpage",
  "isPartOf": { "@id": "https://example.com/#website" },
  "about":   { "@id": "https://example.com/#organization" } }
```

Why it matters: duplication is where structured data goes wrong. Two `Person`
nodes with different spellings of the same person is a data-quality signal that
weakens everything attached to them.

## Choosing types

| Situation | Type |
|---|---|
| Business with a physical presence or services | `Organization`, `ProfessionalService` |
| Individual practitioner | `Person` |
| Local business | `LocalBusiness` + `address`, `geo`, `openingHours` |
| Article or dated post | `Article` with `headline`, `datePublished`, `author` |
| Product with a price | `Product` with `offers` |
| Question and answer blocks | `FAQPage` |
| Step-by-step instructions | `HowTo` |
| Recipe | `Recipe` |
| Portfolio piece | `VisualArtwork` with `artMedium`, `dateCreated` |
| Breadcrumb trail | `BreadcrumbList` |
| Video | `VideoObject` — see `video.md` |

**Do not add a type because it could apply.** A `FAQPage` on a page with no
questions is a structured-data lie, and search engines treat it as one.

## Authoring rules

- **Complete or absent.** Half-populated fields are worse than no markup: they
  assert facts about a page that do not exist.
- **Identifiers must be stable.** An `@id` that changes between renders makes
  the graph unresolvable.
- **Absolute URLs.** Schema URLs do not resolve relative paths.
- **Match the visible page.** Structured data describing content a visitor
  cannot see is a manual-action risk.
- Generate it from typed data, not by writing literals in templates. Build the
  graph in a template from front matter so it cannot drift from the page.

In a generator, serialise with the platform's JSON encoder and mark it safe
rather than string-concatenating, which is where escaping bugs come from.

## For AI answer surfaces

`FAQPage` and `HowTo` are the two that most often get cited in AI overviews,
because they map directly onto a question and a resolution. They are only useful
when the page really contains that structure:

- `FAQPage` requires the question and answer to be visible on the page.
- `HowTo` requires every step, including supplies and the final state.
- Action-oriented headings (`## Step 1: …`) extract better than nominal ones —
  see `seo-core.md`.

## Validation

1. Parse the JSON-LD blocks out of the built HTML — a syntax error is silent in
   the browser.
2. Validate against the schema at
   `https://validator.schema.org/` (vocabulary) and Google's Rich Results
   Test (what actually produces a rich result).
3. Run the `schema` capability once it lands; until then, a malformed block
   inside a valid one is not detected by anything here.

The `on-page` capability extracts and lists the `@type` values it found, which
catches a missing or empty block but not a broken one inside it.

## Checklist

- [ ] Valid JSON-LD parses out of the built HTML
- [ ] One `@graph`, stable `@id`s, absolute URLs
- [ ] `WebSite` plus exactly one organisation or person node
- [ ] Every additional type corresponds to visible page content
- [ ] Validated in the Rich Results Test
- [ ] No placeholders, no empty required fields