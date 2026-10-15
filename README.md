# Website Optimizer Skill

`website-optimizer` is a shared skill for auditing and improving websites for
search visibility and delivery quality.

It answers two questions:

- Is this site findable? (indexing, metadata, structured data, internal linking)
- Is it good once found? (performance, images, video, accessibility)

It measures and advises. It does not build, host, or deploy.

## Status

Round 4 of 6. Four capabilities work and produce append-only evidence runs, the
reference set is complete, and `docs/system-map/` maps the tool contracts.

| Command | What it does |
|---|---|
| `wo.py on-page` | SEO and accessibility signals inside a page |
| `wo.py redirects` | do redirect rules match what the live server does |
| `wo.py images` | image delivery, dimensions, formats, icons |
| `wo.py schema` | JSON-LD structure and completeness |
| `wo.py compare` | attribute what changed between two runs |

Not started: live page rendering via `playwright-cli` (round 5) and housekeeping
— refreshing the workspace pins and the catalog entry (round 6).

**[PLAN.md](PLAN.md)** is the design source of truth, and
**[decision-log.md](decision-log.md)** carries decisions D1–D30 with their
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
| `images` counts correctly | every rule re-counted independently; 469/469 exact |

The image counts were re-derived from the built output with a separate parser,
rule by rule, rather than by re-reading the tool's own numbers. Two apparent
disagreements both resolved in the tool's favour — `photo.webp.jpg` is `.jpg`,
and HEIC is not a modern format — so the tool was right and the check was
weaker in both cases.

That exercise also produced a known coverage gap: `image.loading_unset` fires
only when *no* image on a page declares a strategy, so 121 pages with a mixed
declaration are reported clean. See the limits section in
`capabilities/images/README.md`.

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

### Standard Template for `AGENTS.md`

```markdown
## website-optimizer

This workspace uses the shared skill at `../skills/website-optimizer/` to audit and
improve websites for SEO, structured data, performance, images, video, and
accessibility. See [SKILL.md](../skills/website-optimizer/SKILL.md) for routing and
[PLAN.md](../skills/website-optimizer/PLAN.md) for its current construction state.
```