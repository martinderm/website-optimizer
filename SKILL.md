---
name: website-optimizer
description: >-
  Audits and improves websites for search visibility and delivery quality: SEO
  metadata, indexing, structured data (schema.org / JSON-LD), Core Web Vitals,
  image and video optimization, accessibility, and AI/LLM visibility. Covers
  static generator output as well as dynamically rendered sites. Use when a task
  mentions SEO, Open Graph, Twitter Cards, canonical, sitemap, robots.txt,
  Search Console, JSON-LD, schema.org, Rich Results, PageSpeed, LCP/INP/CLS,
  WebP/AVIF, srcset, lazy loading, Core Web Vitals, WCAG, alt texts, llms.txt,
  or a website launch/relaunch audit.
---

# Website Optimizer

## Status

**Round 5 — six capabilities, static and live.**

`on-page`, `images` and `schema` audit build output or, with `--live`, pages
rendered in a real browser; `links` audits the internal link graph of a build;
`redirects` probes live rules; `compare` attributes what changed. All write
append-only evidence runs. The reference set is complete and `docs/system-map/`
maps the tool contracts.

Before changing anything in `scripts/`, read
[`docs/system-map/`](docs/system-map/README.md): it maps the tool contracts and
says what a given change hits and what it does not.

## Quick start

```
python scripts/wo.py init-site --site-url https://example.com
python scripts/wo.py on-page              # static output, one evidence run
python scripts/wo.py redirects             # live redirect rules
python scripts/wo.py compare               # attribute what changed since the last run
python scripts/wo.py images                # image delivery, dimensions, icons
python scripts/wo.py schema                # JSON-LD structure and completeness
python scripts/wo.py links                 # internal link graph (build output only)
python scripts/wo.py runs                 # list stored runs
python scripts/wo.py on-page --dry-run    # audit, write nothing

python scripts/wo.py on-page --live       # render pages in a browser instead
```

`--live` renders the site in `playwright-cli` and audits the result. It runs
because you asked, never from a hook: a crawl costs minutes, shares a browser
session with anything else using one, and depends on consent state. Raw HTML
lands in `data/crawl/<run-id>/`, which is regenerable — the run folder holds the
findings.

Configure with `site.optimizer.toml` (portable, commit it) and
`site.optimizer.local.toml` (machine paths, do not commit it).

## Router (planned)

The router is a dispatch table, never a copy of the content. One row per
question, pointing at one file. It is filled in as the references land.

| Question | File |
|---|---|
| Titles, descriptions, canonicals, snippet formula | `references/seo-core.md` |
| Open Graph, Twitter Cards, social previews | `references/seo-core.md` |
| Cornerstone content, anchor text, orphans, breadcrumbs, URL structure | `references/internal-linking.md` |
| `robots.txt`, sitemap, `noindex`, Search Console, Bing | `references/indexing.md` |
| 301 redirects, chains, wildcards, URL lifecycle, archives | `references/redirects.md` |
| JSON-LD, `@graph`, schema types, rich results | `references/structured-data.md` |
| Images: WebP/AVIF, `srcset`, dimensions, lazy loading, favicons, OG images | `references/images.md` |
| Video: codec, poster, preload, captions, `VideoObject` | `references/video.md` |
| LCP/INP/CLS, fonts, budgets, caching | `references/performance.md` |
| Semantics, keyboard, focus, contrast, forms, responsive layout | `references/accessibility.md` |
| `llms.txt`, AI overviews, AI crawlers, extractable content | `references/llm-visibility.md` |
| Static generator specifics (robots layout, sitemap config, build output) | `references/static-sites.md` |
| Dynamic CMS specifics (plugins, WP-CLI, cache, archives) | `references/dynamic-sites.md` |
| Where a rule came from, and how strong it is | `references/sources.md` |
| Run an audit, read a report | `scripts/README.md` |
| Which checks exist, and what each means | `scripts/wo/capabilities/*/README.md` |

## Not this skill

Do not load this skill for these tasks — they belong elsewhere:

- Building a site, templates, configuration, content structure → `hugo`
- Web server, reverse proxy, certificates → `caddy`
- Hosting, deployment, DNS, tunnels → `cloudflare-pages`, `cloudflared`,
  `cloudflare-api`
- Browser automation, screenshots, UI inspection → `playwright-cli`
- Writing and tone, copy editing → `writing-pro`

This skill measures and advises. It does not build, host, deploy, or deploy
content. If a finding implies a change to the site's generator, server, or
hosting, report it and hand off to the owning skill.

## Dependencies

Live page rendering uses `playwright-cli`, invoked as an external process and
resolved at runtime: a real executable if one is on `PATH`, otherwise the node
entry point behind npm's `.CMD` shim, so no shell is involved. On Windows the
CLI selects Edge rather than Chrome, because Edge is what the preflight reports
as installed. Its absence only blocks live crawling, never static auditing.

## Run state

Nothing is written inside this skill. Each audited site gets a folder in the
consuming workspace, following that workspace's conventions, holding the site
record, its config, and the run products. Findings go to the evidence zone;
raw rendered HTML goes to the workspace's data zone under `data/crawl/`, is
marked `crawl-ephemeral`, and may be deleted at any time.

## Source of truth

One home per fact. A link beats a copy.

| Question | Single source |
|---|---|
| What is correct? | `references/<topic>.md` — rules only, no flags |
| How is it checked? | `scripts/<capability>/README.md` — interface, exit codes, examples |
| What was found? | The report artifact — never copied into documentation |
| Why is it built this way? | [decision-log.md](decision-log.md) |

A rule and its check are never maintained in two places. If a rule changes,
the check that enforces it changes in the same commit.

## Changing this skill

Two steps, both cheap, both earned the hard way. The reasons are D53 and D54.

- **A new guard is shown to fail first.** Run the test against the unfixed
  behaviour — monkeypatch the fix away — and watch it go red before committing.
  A guard that cannot fail is decoration, and that sentence was written the same
  week a guard was written that could not fail, by someone who had just read it.
- **A rule or interface change is reviewed by a context that did not write it.**
  The shared `software-engineering-kit` skill `code-review` supplies the two axes,
  standards and specification, reported separately. It is bound as a method, not
  as a kernel: no kernel verdicts, no second report schema. A reworded message is
  not a rule change, and neither is a refactor.