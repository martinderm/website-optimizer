---
title: Accessibility
description: Semantic structure, keyboard operation, focus, contrast, and responsive layout as an accessibility obligation.
evidence_level: normative
support_level: fully_supported
applies_to: [website-optimizer]
references:
  - https://www.w3.org/TR/WCAG22/
  - https://developer.mozilla.org/docs/Web/Accessibility/ARIA
  - https://www.w3.org/WAI/WCAG22/Understanding/link-purpose-in-context.html
last_verified: 2026-10-15
review_due: 2027-01-15
---

# Accessibility

Accessibility is a requirement in Austrian and EU law for commercial sites, not
a quality nicety. The checks below are WCAG 2.2 level A/AA basics — the floor,
not the goal.

## Semantic structure

Structure is what assistive technology navigates by.

- One `<h1>` per page; headings descend without skipping levels (`seo-core.md`).
- `<main>` for the primary content — one per page. It is the landmark that lets
  a keyboard user or screen reader skip navigation.
- `<nav>` for navigation regions, `<header>` and `<footer>` for page furniture.
- Contact information belongs in `<address>`.
- Lists are `<ul>`/`<ol>`, not a sequence of `<div>`s.
- Buttons do things, links navigate. A `<div onclick>` is invisible to a keyboard
  and announces nothing.

## ARIA

**The first rule of ARIA is not to use ARIA.** Native elements carry semantics
and keyboard behaviour for free; ARIA has to reimplement both.

- Prefer native elements over `role`.
- If ARIA is used, it must be complete: a `role="button"` also needs `tabindex`
  and key handlers.
- `aria-label` on a link without visible text is fine; on a link *with* visible
  text it overrides the visible name, and if they disagree the site has failed
  link purpose in context.
- Never hide content from assistive technology without a reason.
- `alt`, `label`, and `<caption>` carry meaning; `aria-hidden` on a decorative
  element is its counterpart.

## Keyboard operation

Everything reachable by mouse is reachable by keyboard.

- A visible skip link is the first focusable element:
  `<a href="#main-content" class="skip-link">Zum Inhalt springen</a>`, visually
  hidden until focused, then visible.
- All content reachable by pointer must be reachable by <kbd>Tab</kbd>.
- `Tab` moves forward, `Shift+Tab` back; focus must never become trapped.
- No keyboard handler that intercepts keys the browser uses for navigation.
- A `<details>`-based menu works without JavaScript and is keyboard operable for
  free — prefer it over a scripted hamburger.

## Focus visibility

- A focused control must be visibly distinguishable. Removing the outline
  without providing a replacement makes a site unusable by keyboard.
- Style `:focus-visible` rather than `:focus` so pointer users do not see rings
  on click, and never `outline: none` without a replacement.
- Focus order follows the DOM. If a visual layout reorders content, fix the DOM
  or correct the order explicitly.

## Contrast and colour

- Text contrast ≥ 4.5:1, large text ≥ 3:1. Interface components and focus
  indicators ≥ 3:1.
- Do not encode meaning in colour alone; add a shape, icon, or text.
- Check the actual rendered result — gradients, transparency, and layered
  surfaces make computed values lie.

## Forms

- Every field has a `<label>` bound by `for`/`id`.
- Errors are identified in text, not only in colour, and state which field failed
  and how to fix it.
- Do not disable the submit button as validation feedback; let the submission
  happen and report the problems.

## Images and media

- `alt` on every image; `alt=""` for purely decorative ones (`images.md`).
- Captions and transcripts for video (`video.md`).
- Nothing auto-plays with sound.

## Responsive layout is an accessibility obligation

Zoom and reflow are accessibility criteria, not design preferences.

- Content must survive 200 % zoom and a 320 CSS-pixel-wide viewport without
  horizontal scrolling or loss of content.
- The viewport must not be locked with `user-scalable=no` or
  `maximum-scale=1`.
- Text must remain resizable; do not size in `px` alone where rem is available.
- Touch targets need enough size and spacing to be operable.

### Breakpoint discipline

Breakpoints belong to the layout, not to device names.

- Work mobile-first: base styles describe the small viewport, media queries
  contain only genuine overrides.
- **Never re-declare a base value inside a query.** The most common CSS defect
  is a query resetting `align-items`, `width`, `flex`, `margin` or `padding` to
  a value the base already had — which then silently overrides a later fix.
- One breakpoint per region; consolidate rather than scattering several queries
  at the same boundary.
- Choose the breakpoint when the content actually needs it, not at
  320/768/1024 by convention. Around 820 px is a common point for switching a
  header to a mobile menu, but it is a per-site decision.

### Navigation

- Keep desktop and mobile navigation structurally separate rather than bending
  one construct to fit every width.
- The mobile toggle must not resize its container when opened. An open menu that
  widens the header pushes the brand and the toggle out of alignment — the most
  frequent bug in this area.
- Brand and toggle stay on one line; the toggle stays right-aligned in both
  states.
- Submenus on mobile belong in the overlay as collapsible lists, not as free
  floating dropdowns.
- Opening the menu must not shift content. Reserve the space or overlay it.

## Checklist

- [ ] `lang` on `<html>`, one `<h1>`, no skipped heading levels
- [ ] `<main>`, `<nav>`, `<header>`, `<footer>` present and unique where required
- [ ] Skip link is the first focusable element and visible on focus
- [ ] Everything pointer-operable is keyboard-operable; no focus traps
- [ ] `:focus-visible` styling, never `outline: none` without a replacement
- [ ] Contrast verified on the rendered page
- [ ] Every form control labelled; errors in text
- [ ] `alt` on all images, decorative ones empty
- [ ] Survives 200 % zoom at 320 px width
- [ ] Mobile menu does not resize the header when opened
- [ ] No media query re-declaring an unchanged base value