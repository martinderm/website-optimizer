---
title: Images
description: Formats, responsive delivery, dimensions, lazy loading, favicons, and social images.
evidence_level: normative
support_level: fully_supported
applies_to: [website-optimizer]
references:
  - https://developer.mozilla.org/docs/Web/HTML/Reference/Elements/img
  - https://web.dev/articles/responsive-images
  - https://ogp.me/docs/image-metadata/
  - https://favicon.io/html-favicon/
last_verified: 2026-10-15
review_due: 2027-01-15
---

# Images

Images are usually the largest thing on a page and the easiest to improve.
They also determine whether a link looks right when it is shared.

## Format

| Format | Use |
|---|---|
| AVIF | best compression; decoder support is good in current browsers |
| WebP | the safe default; universal in current browsers |
| JPEG / PNG | source material and fallbacks |

Serve modern formats with the original as fallback. In a generator, this means
multiple widths **and** multiple formats from one source image — resize at build
time, not at request time.

## Responsive delivery

An image must declare its rendered sizes, or the browser downloads a
desktop-sized file for a phone.

```html
<img
  src="/img/hero-1400.webp"
  srcset="/img/hero-800.webp 800w,
          /img/hero-1400.webp 1400w,
          /img/hero-2200.webp 2200w"
  sizes="(max-width: 820px) 100vw, 60vw"
  width="1400" height="700"
  alt="A furnished living room with a large window">
```

- **Three widths are the working set** for most sites: roughly 800, 1400, 2200
  pixels. More is possible; beyond three the benefit is small and the build cost
  is real.
- `sizes` must describe the *layout* width at each breakpoint, not the viewport.
  A wrong `sizes` is worse than no `sizes`: the browser picks the wrong candidate
  with full confidence.
- **The above-fold image must not be lazy-loaded.** Lazy loading the LCP element
  defers the largest contentful paint until after layout settles, which is the
  single most common self-inflicted performance regression.

## Dimensions and layout stability

Always set `width` and `height`. Without them the browser cannot reserve space
before the file arrives, and the content jumps — a direct contributor to
cumulative layout shift. In CSS, `height: auto` alongside the attributes keeps
the ratio when the width is constrained.

## Lazy loading

```html
<img loading="lazy" decoding="async" ...>
```

Use it for everything below the fold. Leave the first meaningful image eager.
Lazy loading an element that is initially above the fold is a bug, not a
caution.

## Alt text

- `alt` describes what the image conveys, for someone who cannot see it.
- Decorative images take `alt=""` — **present and empty**. This is correct and
  is not the same as omitting the attribute. Omitting `alt` is the defect the
  `on-page` capability reports.
- Never start with "image of" or "picture of"; the reader already knows it is an
  image.
- For content images, a short description of the subject beats a keyword list.

## Favicons and app icons

A modern set, referenced from the head:

```html
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png">
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
```

Files: `favicon.ico` (16/32/48), `favicon-16x16.png`, `favicon-32x32.png`,
`apple-touch-icon.png` (180×180), `android-chrome-192x192.png`,
`android-chrome-512x512.png`, `site.webmanifest`. Keep `favicon.ico` at the site
root for automatic fallback.

**Design at the smallest size.** Detail that reads at 512px disappears at 16px.
A complex logo makes a poor favicon; reduce it to an icon, a mark, or a letter.

Keep the links in one head partial and make sure the build actually copies the
files to the site root — an icon that exists in the repository but not in the
build output is the usual cause of "works locally, missing in production".

An SVG favicon is optional:

```html
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
```

## Social preview images

- 1200×630 pixels is the reliable baseline for `og:image`.
- **Absolute URL.** Scrapers do not resolve relative paths.
- A single global image is the minimum viable setup; a site with covers can
  resolve per page with a global fallback.
- `og:image:alt` is part of the Open Graph spec and is set alongside.
- The image should still make sense cropped — some clients crop to a square.

## Checklist

- [ ] AVIF or WebP with an original fallback
- [ ] `srcset` with ~3 widths and a correct `sizes`
- [ ] `width` and `height` on every image
- [ ] `loading="lazy"` below the fold, **not** on the LCP image
- [ ] `alt` present on every image; decorative images `alt=""`
- [ ] Favicon set complete and present in the build output
- [ ] `og:image` absolute, 1200×630, with `og:image:alt`