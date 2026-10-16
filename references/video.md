---
title: Video
description: Codec and container choices, posters, loading strategy, transcripts, and VideoObject markup.
evidence_level: normative
support_level: partially_supported
applies_to: [website-optimizer]
references:
  - https://developer.mozilla.org/docs/Web/Media/Guides/Formats/video_codecs
  - https://schema.org/VideoObject
  - https://developer.mozilla.org/docs/Web/HTML/Element/video
last_verified: 2026-10-15
review_due: 2027-01-15
---

# Video

Video is the largest asset on most sites and the least often optimised. Two
rules dominate: do not make the browser download what the visitor has not asked
for, and make the content usable without sound or sight.

**Support note:** the codec guidance below rests on general knowledge of browser
support rather than a source re-read for this file (`see sources.md`). Verify
before relying on a specific format claim.

## Container and codec

| Container | Codec | Use |
|---|---|---|
| MP4 | H.264 | universal fallback |
| WebM | VP9, AV1 | better compression where supported |
| HLS | — | adaptive streaming for long or audience-critical video |

Serve a WebM source and an MP4 source; browsers pick what they can play. The
`<source>` order should put the more capable format first only if you trust
every browser's fallback behaviour — otherwise put the safe format first.

Keep audio in AAC in MP4 and Opus in WebM. A container with a codec the browser
cannot decode plays nothing, and the failure looks like a network error.

## Poster image

A video downloads no pixels before it starts. Without a poster, the player area
is blank until the first frame arrives.

```html
<video controls preload="metadata" poster="/media/talk-poster.jpg"
       width="1280" height="720">
  <source src="/media/talk.webm" type="video/webm">
  <source src="/media/talk.mp4" type="video/mp4">
  <track kind="captions" src="/media/talk.de.vtt" srclang="de" label="Deutsch">
  <p>Your browser cannot play this video.
     <a href="/media/talk.mp4">Download it instead</a>.</p>
</video>
```

- `width` and `height` here too, for the same layout-stability reason as images.
- The poster should match the first frame's framing so playback does not jump.

**Measured by** `images`: `video.poster_missing` counts the `<video>` elements on
a page without a poster; `video.poster_file_missing` reports a poster the build
never emitted, which is `icon.file_missing` one element type over. A remote poster
is not checked, because it is not in the build to check.

## Loading strategy

| Attribute | Effect | Use when |
|---|---|---|
| `preload="none"` | nothing loads until the user presses play | default for long or below-the-fold video |
| `preload="metadata"` | duration and dimensions only | reasonable default for short video |
| `preload="auto"` | the browser may fetch the whole file | **not** for video, and never combined with `autoplay` on a page with other media |

A poster plus `preload="none"` costs a visitor nothing until they choose to watch.
That is almost always right.

**Measured by** `images`: `video.preload_unset` fires once per page when no
`<video>` on it declares any strategy, exactly as `image.loading_unset` does for
images and for the same reason — one decision was left unmade, not four. It does
not report a *partially* declared page: unlike the image case, the reference above
gives one right answer for video, so a page that declares something has answered.

For video embedded in a page that also contains other media, prefer
`preload="none"` plus a facade: a poster image that loads the real player on
click. Third-party players otherwise pull megabytes of script and telemetry
before the visitor expresses any intent.

Autoplay with sound is blocked by every current browser. Autoplay muted is
permitted and is an accessibility decision, not a default.

## Captions and transcripts

**Not measured, and the reason is worth keeping.** A `<track kind="captions">`
presence check is markup and would be easy to write. It is not written, because
presence is not the thing that matters: a track that is empty, mistimed, or in the
wrong language passes it, and a page reported clean reads as a page whose captions
were checked. That is a clearance this tool would not have earned, which is worse
than the silence it would replace.
- **Captions** are timed text for people who cannot hear. `kind="captions"`.
- **Transcripts** are prose for people who cannot watch, for search, and for
  anyone who prefers to read. `kind="descriptions"` is a different thing —
  audio description.
- `srclang` is required; `label` should match it.
- The transcript belongs on the page as text, not only in a caption file. It is
  the only version a crawler can quote.

A video without captions is a video some visitors cannot use.

## VideoObject structured data

```json
{
  "@type": "VideoObject",
  "name": "Title",
  "description": "One or two sentences.",
  "thumbnailUrl": ["https://example.com/media/talk-poster.jpg"],
  "uploadDate": "2026-03-01T10:00:00+01:00",
  "duration": "PT12M30S",
  "contentUrl": "https://example.com/media/talk.mp4",
  "embedUrl": "https://example.com/media/talk/"
}
```

Duration uses ISO 8601 (`PT12M30S`). `uploadDate` is required. The marked-up
video must be the one at that URL and visibly present on the page — markup for a
video the page does not show is a violation, not an optimisation.

Include `VideoObject` in the page's `@graph` alongside `WebPage` and `WebSite`
(`structured-data.md`).

## Embedded third-party video

- A YouTube or Vimeo embed loads the provider's script, cookies, and player
  before play. Treat it as third-party script, budget for it in
  `performance.md`, and gate it behind a consent decision.
- A facade (poster image, click to load) removes that cost for visitors who never
  play.
- Embeds must not silently set cookies before consent.

## Checklist

- [ ] WebM plus MP4 sources, both with audio in a supported codec
- [ ] `poster` present, matching the first frame
- [ ] `width` and `height` set
- [ ] `preload="none"` or `"metadata"`, never `"auto"` for long video
- [ ] Captions with `srclang` and matching `label`
- [ ] Transcript present as text on the page
- [ ] `VideoObject` in the page's `@graph`, with `uploadDate` and `duration`
- [ ] Third-party embeds behind a facade and gated by consent