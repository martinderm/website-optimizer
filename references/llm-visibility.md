---
title: AI and LLM visibility
description: llms.txt, AI search crawlers, and writing content that can be extracted and cited.
evidence_level: normative
support_level: partially_supported
applies_to: [website-optimizer]
references:
  - https://llmstxt.org/
  - https://developer.mozilla.org/en-US/docs/Web/HTML/Element/link#rel
last_verified: 2026-10-15
review_due: 2027-01-15
---

# AI and LLM visibility

**Support note:** `llms.txt` is a proposal, not an adopted standard, and no
major engine has confirmed it as a ranking input. Nothing here is a ranking
factor. The value of this page is in making content easier to extract correctly
— that part does not depend on the proposal.

## llms.txt

A Markdown file at `/llms.txt` giving a model a curated entry point instead of
a page full of navigation and script.

```md
# Example GmbH

> Example GmbH builds and repairs industrial control systems in Lower Austria,
> with service across the EU since 1994.

- German-language site
- Primary content: products, service, contact
- Prices on request

## Main pages

- [Startseite](https://example.com/): Entry point
- [Leistungen](https://example.com/leistungen/): What we do
- [Kontakt](https://example.com/kontakt/): Request an offer

## Legal

- [Impressum](https://example.com/impressum/): Provider identification
- [Datenschutz](https://example.com/datenschutz/): Privacy information

## Optional

- [History](https://example.com/geschichte/): Background, not usually needed
```

**Measured by** `crawler-files`: `llms.missing` when there is none, `llms.empty`
when there is one with no links in it. Presence and shape only — the file is
Markdown and *reading* it is the job of whatever consumes it, not of an audit.

The structure the specification describes:

1. `#` H1 with the project or site name.
2. `>` blockquote with a short summary — the most important context in the file.
3. Optional free notes, **without further headings**.
4. Zero or more `##` sections containing link lists, each entry
   `[Name](URL): note`.

**`## Optional` is a semantic block.** Resources listed there may be dropped
under a tight context budget, so it holds only secondary material. Using it as a
miscellaneous bucket defeats its purpose.

Include: the home page, primary service or product pages, content indexes,
contact, and legal pages. Exclude: every remaining subpage, redundant
navigation, search/filter/login URLs, and assets.

Errors to avoid: turning it into a second sitemap, marketing language without
information value, linking staging URLs, and not maintaining it after a
relaunch.

**Markdown versions of pages.** The proposal also suggests serving clean Markdown
at the same URL with `.md` appended (`/docs/intro/` →
`/docs/intro/index.html.md`). Optional; a good `llms.txt` comes first.

In a static generator, put the file in `static/` so it is served unchanged at
`/llms.txt`, and keep it per-domain — never merge content from several sites into
one file.

## Crawlers

- `robots.txt` applies to AI crawlers like it does to any other bot. Blocking
  `GPTBot`, `ClaudeBot`, or `PerplexityBot` is a legal and commercial decision
  about whether to allow training, and it is separate from whether the site may
  be cited.
- A crawler blocked in `robots.txt` cannot be cited as a source either, because
  it cannot read the page.
- Decide per site, record the decision in the site's reference file, and do not
  set and forget it.

## Writing content that extracts well

This is the durable part, and it holds regardless of any AI surface.

### Page structure

1. **Answer or define immediately.** One to three clear sentences at the top that
   answer the main question or name the central benefit. Do not bury the answer
   under a long introduction.
2. **Question-shaped headings.** Each H2/H3 handles exactly one question or one
   bounded aspect. Avoid vague headings like "Good to know" — they carry no
   extractable meaning.
3. **One idea per paragraph.** Keep paragraphs short and do not mix independent
   claims into one block of text.
4. **Lists for steps, criteria, and options.** Numbered lists for sequences,
   bullets for equal items. Do not hide a list inside running text.
5. **Use the audience's terms.** Search and question phrases belong in the text
   naturally and concretely — without keyword repetition that adds no
   information.
6. **Close with the conclusion or the next step.** Compress the main point and
   point to the relevant next page, contact route, or action.

### Writing rules

- Prefer short, active, unambiguous sentences.
- Explain a technical term at first use unless the audience can be assumed to
  know it.
- In long articles, break the text roughly every 300 words — and make sure the
  intermediate heading carries real navigational value rather than existing only
  to break the block.
- Write more plainly for FAQ, introductory, and explanatory content.
- Avoid digressions, heavy introductory passages, pop-ups, overlays, and
  off-topic interruptions on informational pages.

### What each rule buys

- **Answer early.** Extraction favours the passage that answers the question
  without preamble.
- **Action verbs in headings.** `## Step 1: test the pH` states what the section
  delivers; `## Preparation` does not.
- **Self-contained passages.** A paragraph that depends on the two before it
  cannot be quoted alone, and will not be.
- **Facts, not adjectives.** "Supports up to 16 bar" extracts. "High quality,
  robust solution" does not.
- **The audience's vocabulary.** Match terms, not phrases.

### Review before publishing

- [ ] Do the first sentences answer the most important question directly?
- [ ] Does each H2/H3 carry exactly one understandable idea?
- [ ] Is each paragraph limited to one core statement?
- [ ] Are steps, selection criteria, and options set as real lists?
- [ ] Does the page name its terms, questions, and services concretely?
- [ ] Is the conclusion or next action unambiguous?
- [ ] Does the structured markup carry an existing statement rather than
      simulate one?

## Technique supports, it does not replace

Structured data (`Article`, `FAQPage`, `HowTo`) supplies context and helps
entity assignment. It does not make unclear content clear. `llms.txt` is a
curated orientation; it replaces neither clear page content nor `robots.txt` nor
`sitemap.xml`. The technical checks that verify these things live in
`indexing.md` and `structured-data.md`, and the mechanical ones in
`scripts/wo/capabilities/on_page/` and `scripts/wo/capabilities/schema/`.

## Structured data for AI surfaces

`FAQPage` and `HowTo` map most directly onto a question and a resolution, which
makes them the two most frequently eligible for citation — and only when the page
genuinely contains that structure (`structured-data.md`). Markup that describes
content the page does not show is a violation.

## Checklist

- [ ] `/llms.txt` reachable, per domain, structure per specification
- [ ] Blockquote summary answers who and what within two sentences
- [ ] `## Optional` holds only genuinely secondary resources
- [ ] Links match the current live domain; no staging URLs
- [ ] AI crawler policy decided and recorded for the site
- [ ] Key answers in the first paragraph after their heading
- [ ] Headings state questions or actions
- [ ] Passages self-contained and quotable