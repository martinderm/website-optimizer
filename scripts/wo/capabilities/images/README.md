# `images` capability

Image delivery, dimensions, formats, and icons — read from the built output
directory rather than a single page, because half of what matters is only visible
across the site.

## Interface

```
python scripts/wo.py images [--config FILE] [--strict] [--dry-run] [--json]
```

## Scope boundary

**The `alt` check belongs to `on-page` and is not repeated here.** Duplicating it
would give one defect two rule ids, two severities and two homes — exactly what
this skill exists to remove. What is read from `alt` here is presence and length
only; the value itself is authored prose and a report has no use for it.

## Rules

| rule_id | Severity | Fires when |
|---|---|---|
| `image.src_missing` | warning | `<img>` with no `src`, or an empty one — nothing can load |
| `image.dimensions_missing` | critical | `<img>` without `width` or `height` — the browser cannot reserve space, so CLS |
| `image.srcset_missing` | warning | no candidate set; the image cannot adapt to the viewport |
| `image.sizes_missing` | warning | width-descriptor `srcset` without `sizes` — the browser picks the wrong candidate |
| `image.format_legacy` | warning | no AVIF or WebP candidate anywhere in the set |
| `image.loading_unset` | warning | no image on the page declares a loading strategy (once per page) |
| `image.loading_partial` | warning | some images declare a strategy, some do not (once per page) |
| `image.og_relative` | warning | `og:image` is not an absolute URL — scrapers do not resolve it |
| `icon.none_declared` | warning | no favicon or app icon declared |
| `icon.file_missing` | critical | an icon is declared but the file is not in the build output |

`width="100%"` does not count as a dimension: the check requires a number,
because that is what reserves space.

An `<img>` with no `src` is reported by `image.src_missing` **instead of**
`image.dimensions_missing` and `image.srcset_missing`, not in addition to them.
An element that downloads nothing reserves no space and adapts to nothing, so
counting it as a missing dimension inflated the critical count by counting
JavaScript placeholders as delivery faults. On the reference site that was 140
of 469 — thirty percent of the headline number.

The bare-attribute case is the one to fix first. `<img src alt>` parses as
`src=""`, which resolves against the document, so the browser issues a genuine
request for the page itself as an image. It is a real network cost and a real
symptom of a template that emits an attribute it has not filled yet.

`image.loading_unset` reports once per page rather than once per image. A site
that lazy-loads nothing has one problem, not two hundred.

`icon.file_missing` is the one that needs the directory: an icon declared in the
head of every page but never emitted by the build is the classic silent fault,
and no single-page view can see it.

## Known limits

- `loading` strategy cannot be judged statically: whether an image is above the
  fold needs a layout, so only a wholly undeclared strategy is reported.
- **A partially declared strategy raises a question, not a verdict.** The fold
  cannot be measured statically: whether an image sits above it needs a layout.
  So `image.loading_partial` says the question is open, how many images it
  concerns, and what would close it — it does not say those images are wrong.

  Before this rule existed, 121 pages on the reference site and 26 of 29 on a
  real WordPress site reported nothing at all despite carrying images with no
  strategy — among them one page with 42 OpenStreetMap tiles, every one of which
  the browser fetches immediately. Silence read as clean.

  What would close the question is a live run that measures each image's
  position against the viewport. That path is not taken automatically: a crawl
  per page is the most expensive thing this tool does. Until it is taken, read
  `loading_partial` as a prompt to investigate, not as a defect list.
- Image *weight* is not measured. That needs real network or file inspection and
  belongs to `performance.md`.
- `<picture>` elements are not walked; their `<source>` children are invisible
  here. `srcset` on the `<img>` is what gets read.
- `_extension()` takes the last extension only. A file named
  `photo.webp.jpg` is classified `.jpg`, which is right, but a name like
  `photo.jpg.webp` that does not exist in its real format would silently pass.