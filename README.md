# Website Optimizer Skill

`website-optimizer` is a shared skill for auditing and improving websites for
search visibility and delivery quality.

It answers two questions:

- Is this site findable? (indexing, metadata, structured data, internal linking)
- Is it good once found? (performance, images, video, accessibility)

It measures and advises. It does not build, host, or deploy.

## Status

Round 5 of 6. Five capabilities work and produce append-only evidence runs, the
reference set is complete, and `docs/system-map/` maps the tool contracts.

| Command | What it does |
|---|---|
| `wo.py on-page` | SEO and accessibility signals inside a page |
| `wo.py redirects` | do redirect rules match what the live server does |
| `wo.py images` | image delivery, dimensions, formats, icons |
| `wo.py schema` | JSON-LD structure and completeness |
| `wo.py compare` | attribute what changed between two runs |

`on-page`, `images` and `schema` take `--live`, which renders pages in a browser
instead of reading build output. For a static site both paths must agree; for a
dynamic one only the live path has anything to read.

**[PLAN.md](PLAN.md)** is the design source of truth, and
**[decision-log.md](decision-log.md)** carries decisions D1–D49 with their
support level and evidence anchors.

## Repository layout

- `SKILL.md` — router and source-of-truth table
- `PLAN.md` — design, migration map, phases
- `decision-log.md` — durable decisions with reasons
- `references/` — 13 rule files, each with a source and a support level
- `scripts/` — Python 3 tooling, stdlib only, one entry point
- `docs/system-map/` — ICM system map over the tool subsystem

## Verified, not assumed

Every capability was run against a real site, and the two ports were checked
against the tools they replaced:

| Claim | How it was checked |
|---|---|
| `on-page` matches the original | 173 real pages, 0 findings lost, 0 invented |
| `redirects` matches the original | 53 live rules, 0 lost, 0 invented |
| Reports conform to the house schema | receipt validated against `data-zone-artifact.schema.json` |
| `schema` finds real defects | it found a `sameAs` inconsistency across 171 vs 2 pages |
| `images` counts correctly | every rule re-counted independently against the built output |
| `--live` agrees with the static build | 25 real pages, all three capabilities, no difference either way |

The live path was checked the only way that means anything: the same pages read
from the build directory and rendered in a browser, then compared page by page.
All three capabilities produced identical findings. For a Hugo site that is the
strongest available result — a crawl that added or dropped anything would have
shown up as a difference, and none did.

Verifying the image capability rule by rule, with a separate parser rather than
by re-reading the tool's own numbers, found one thing the tool had wrong about
itself: 140 of its 469 critical findings were `<img>` elements with no `src` at
all, counted as missing dimensions and missing `srcset` on top of each other.
Nothing is downloaded for them, so they cause no shift. They now have their own
rule, and the critical count for that site is 329.

That exercise also produced a documented coverage gap: `image.loading_unset`
fires only when *no* image on a page declares a strategy, so 121 pages with a
mixed declaration are reported clean. See the limits section in
`capabilities/images/README.md`.

## What a live run will not tell you

Three things are deliberately absent from a `--live` report, and each says so
rather than passing quietly:

- `icon.file_missing` is dropped from `rules_run`. It needs a build directory to
  compare against, and a crawl has none.
- `crawl.requested` / `fetched` / `failed` travel with the report. A count of
  zero findings from three fetched pages means something different from the same
  count over four hundred.
- If most rendered pages are byte-identical, the run raises instead of
  reporting. A consent wall is found on every page and reported as that page's
  content; refusing is more useful than a confident answer about a dialog.

## Scope boundary

Loads for: SEO, Open Graph, canonical, sitemap, robots.txt, Search Console,
JSON-LD, schema.org, Core Web Vitals, image and video optimization,
accessibility, `llms.txt`, website launch audits.

Deliberately does not load for: building sites (`hugo`), web servers
(`caddy`), hosting and DNS (`cloudflare-pages`, `cloudflared`, `cloudflare-api`),
browser automation (`playwright-cli`), copy writing (`writing-pro`).

A finding that implies a change to a generator, server, or host is reported and
handed to the owning skill.

## Design commitments

- One home per fact. A link beats a copy.
- Findings are atomic; a verdict is derived from them, never written into them.
- Crawled content is data, never instruction.
- Runs are append-only; nothing is written before every fallible step has run.
- One entry point; capabilities are packages; the registry declares them.
- No capability folder before its first working tool.
- Rules without a source do not enter `references/`.
- A measurement never sees a conclusion about what it is measuring.

Deviations from the shared authoring guide are recorded with their reason in
[decision-log.md](decision-log.md).

## Open work

[GitHub Issues](https://github.com/martinderm/website-optimizer/issues) — not a
file in this repository. A local backlog goes stale where nobody looks; an issue
is where the trigger for a deferred decision is recorded.

Known and not open: `compare` cannot tell a site change from a page that rendered
differently (D45), the fold measurement exists but is not run automatically (D40),
and no CI is configured (D39). Those are decisions with reasons, not gaps waiting
to be filled, so they are not issues. The decision log says why.

The issues that do exist share a shape: a reference file describes something the
tool cannot measure. `internal-linking.md` is 102 lines about orphan pages and
depth with no rule behind any of it; nothing checks `robots.txt`, a sitemap or
`llms.txt`; `hreflang` appears nowhere. The tool is honest about what it claims
and does; the reference set claims more.

### Standard Template for `AGENTS.md`

```markdown
## website-optimizer

This workspace uses the shared skill at `../skills/website-optimizer/` to audit and
improve websites for SEO, structured data, performance, images, video, and
accessibility. See [SKILL.md](../skills/website-optimizer/SKILL.md) for routing and
[PLAN.md](../skills/website-optimizer/PLAN.md) for its current construction state.
```