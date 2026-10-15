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

**Round 2 of 4 — one capability working. References still pending.**

`scripts/` is live: `on-page` audits a static output directory and writes an
append-only evidence run. `references/` and `docs/system-map/` do not exist yet.

**Nothing in this skill may be cited as a rule until the corresponding reference
file exists.** Until round 3a lands, `hugo-wizard`'s own chore documents remain
where SEO rules live, and they stay there until their replacement exists.
Full design and migration map: [PLAN.md](PLAN.md).

## Quick start

```
python scripts/wo.py init-site --site-url https://example.com
python scripts/wo.py on-page              # audit, write one evidence run
python scripts/wo.py runs                 # list stored runs
python scripts/wo.py on-page --dry-run    # audit, write nothing
```

Configure with `site.optimizer.toml` (portable, commit it) and
`site.optimizer.local.toml` (machine paths, do not commit it).

## Router (planned)

The router is a dispatch table, never a copy of the content. One row per
question, pointing at one file. It is filled in as the references land.

| Question | Planned file |
|---|---|
| Titles, descriptions, canonicals, snippet formula | `references/seo-core.md` |
| Internal linking, cornerstone content, anchor text | `references/seo-core.md` |
| `robots.txt`, sitemap, `noindex`, crawl budget | `references/indexing.md` |
| Search Console, Bing Webmaster, indexing request | `references/indexing.md` |
| 301 redirects, URL lifecycle, legacy URLs | `references/redirects.md` |
| JSON-LD, `@graph`, schema types, rich results | `references/structured-data.md` |
| Images: WebP/AVIF, `srcset`, dimensions, lazy loading, favicons, OG images | `references/images.md` |
| Video: codec, poster, preload, transcript, `VideoObject` | `references/video.md` |
| LCP/INP/CLS, fonts, CSS/JS budget, caching | `references/performance.md` |
| Semantics, keyboard, focus, contrast, skip link | `references/accessibility.md` |
| `llms.txt`, AI overviews, AI crawlers, extractable content | `references/llm-visibility.md` |
| Static generator specifics (Hugo robots layout, build output) | `references/static-sites.md` |
| Dynamic CMS specifics (plugin SEO, WP-CLI, cache invalidation) | `references/dynamic-sites.md` |
| Run an audit, read a report | `scripts/README.md` |

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

Live page rendering uses `playwright-cli`, invoked as an external CLI and
probed for version at runtime. It is presumed available on this system; its
absence only blocks live crawling, never static auditing.

## Run state

Nothing is written inside this skill. Each audited site gets a folder in the
consuming workspace, following that workspace's conventions, holding the site
record, its config, and the run products (crawl, reports, baseline).

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