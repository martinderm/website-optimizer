# Website Optimizer Skill

`website-optimizer` is a shared skill for auditing and improving websites for
search visibility and delivery quality.

It answers two questions:

- Is this site findable? (indexing, metadata, structured data, internal linking)
- Is it good once found? (performance, images, video, accessibility)

It measures and advises. It does not build, host, or deploy.

## Status

Round 2 of 4. The `on-page` capability works and produces append-only evidence
runs; the reference set and the system map are still pending.

**[PLAN.md](PLAN.md) is the design source of truth.** Do not cite this skill as
a rule yet: `references/` does not exist, so the SEO rules still live in the
consuming workspace's chore documents until their replacements land.

## Repository layout

- `SKILL.md` — router and source-of-truth table
- `PLAN.md` — design, migration map, phases
- `decision-log.md` — durable decisions with reasons
- `references/` — rules, one file per topic (planned, round 3)
- `scripts/` — Python 3 audit tools, stdlib only (planned, round 2)
- `docs/system-map/` — ICM system map over the tool subsystem (planned, round 3)

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
- The report shape is a schema file, not prose.
- One entry point; capabilities are packages.
- No capability folder before its first working tool.
- Rules without a source do not enter `references/`.

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