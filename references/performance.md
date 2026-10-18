---
title: Performance and Core Web Vitals
description: LCP, INP, and CLS, and the asset decisions that move them.
evidence_level: normative
support_level: fully_supported
applies_to: [website-optimizer]
references:
  - https://web.dev/articles/vitals
  - https://web.dev/articles/optimize-lcp
  - https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Caching
last_verified: 2026-10-15
review_due: 2027-01-15
---

# Performance and Core Web Vitals

Performance is a ranking factor and, before that, it is the reason a visitor
leaves. Three metrics cover most of what matters.

| Metric | Measures | Good | Needs work | Poor |
|---|---|---|---|---|
| **LCP** | largest contentful paint | ≤ 2.5 s | ≤ 4.0 s | > 4.0 s |
| **INP** | interaction to next paint | ≤ 200 ms | ≤ 500 ms | > 500 ms |
| **CLS** | cumulative layout shift | ≤ 0.1 | ≤ 0.25 | > 0.25 |

## LCP — the largest thing appears

LCP is usually the hero image or the headline block. It is dominated by three
things: server response time, resource load time, and render delay.

- **Server response.** Cache HTML at the edge with a short TTL plus stale-while-
  revalidate. A static site should not wait on an origin.
- **The hero image.** Preload it, do not lazy-load it, and give it explicit
  dimensions (`images.md`). Preloading an image that is not the LCP element wastes
  bandwidth on something else.
- **Fonts.** A `font-display: swap` text keeps the page readable while a webfont
  loads. Self-host, subset to the used glyphs, and preload only the one or two
  faces needed for the first paint.
- **Render delay.** Long scripts before the first paint push LCP even when the
  resources are fast. Ship less JavaScript to the first paint.

## INP — the page responds

INP replaced First Input Delay as the responsiveness metric. Long tasks on the
main thread are the cause.

- Move work off the main thread; do it in a worker or at idle.
- Break long tasks into chunks with yields between them.
- Keep third-party scripts out of the critical path — this includes embedded
  video (`video.md`).
- Hydrate nothing that is not interactive. A static page needs no framework
  runtime to be responsive.

## CLS — the layout does not jump

Every shift scores. The causes are all fixable in the markup.

- **Images and video** need `width` and `height`.
- **Fonts** shift text when they swap in; size-adjust the fallback to match.
- **Ads and embeds** reserve space with a container of fixed dimensions.
- **Content injected above existing content** shifts everything below it. Never
  insert a banner above the fold after load.
- Anything animated with `top`, `left`, or `width` animates layout. Animate
  `transform` and `opacity` instead.

## Caching

| Resource | Recommendation |
|---|---|
| HTML | short TTL, `stale-while-revalidate`; must revalidate for correct canonicals |
| Fingerprinted CSS/JS/images | `Cache-Control: public, max-age=31536000, immutable` |
| `favicon.ico`, manifest | moderate TTL |
| HTML itself in a static build | hashed assets make a short HTML TTL safe |

Immutable caching requires content-addressed filenames. An image served with a
one-year immutable TTL under a stable name is uncacheable-by-design for
everyone after the first change.

## Asset budget

A budget is what stops performance from eroding one dependency at a time.

| Budget | Working value |
|---|---|
| CSS, compressed | ≤ 100 KB |
| JavaScript, compressed, first view | ≤ 200 KB |
| Third-party scripts | named and justified, individually |
| Hero image | ≤ 200 KB |
| Fonts | ≤ 100 KB per weight, 1–2 weights total |

Enforce the budget in CI rather than in review. A budget nobody measures is a
wish.

## Measurement

- Field data (CrUX, Search Console Core Web Vitals report) reflects real
  visitors and is what search uses. Lab tools (Lighthouse) are for diagnosis.
- Measure on a representative mobile connection, not on a workstation.
- Re-measure after deploys; a regression is invisible until someone looks.

## Checklist

- [ ] LCP element preloaded, not lazy-loaded, with explicit dimensions
- [ ] Fonts self-hosted, subsetted, `font-display: swap`, fallback size-adjusted
- [ ] No long tasks on the main thread during interaction
- [ ] No layout-affecting animations; ads and embeds reserve space
- [ ] Fingerprinted assets served immutable; HTML revalidating
- [ ] Asset budgets defined and measured in CI
- [ ] Field data checked in Search Console after launch

## Skill coverage

What the `performance` capability (v0.8.0) measures, and what stays advice:

- **Budgets — measured** (`perf.budget_exceeded`): CSS, JS, largest image and
  font files against the working values above, in bytes on disk.
- **Hero preloaded — half measured**: whether a preload *target exists* is
  measured (`perf.preload_target_missing`); whether the LCP element *is*
  preloaded is not, because hero detection from markup alone is a heuristic.
- **Fonts — one of four measured**: missing `font-display` is measured
  (`perf.font_display_missing`); self-hosting, subsetting and fallback
  size-adjustment are not.
- **Render delay — measured** (`perf.render_blocking_script`): classic scripts
  in `<head>` without `defer`/`async`. Long tasks, workers and hydration are
  runtime behavior, not markup.
- **Third parties — named, not judged** (`perf.third_party_origin`): one
  inventory line per origin with a page count. Justification stays human.
- **LCP/INP/CLS values, caching headers, field data — not measured.** They
  need lab or field observation (Lighthouse, PageSpeed Insights, CrUX), which
  is a network dependency and a separate decision, not a rule in this tool.