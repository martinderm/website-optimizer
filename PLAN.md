---
document_type: plan
title: "Plan — website-optimizer"
status: draft
owner: "dagobert-ai / website-optimizer"
version: "0.3"
date: 2026-10-15
last_verified: 2026-10-15
review_due: 2026-11-15
evidence_level: normative
applies_to:
  - website-optimizer
references:
  - agent-architecture/governance/decisions/0002-dual-evidence-framework-and-factored-verification.md
  - agent-architecture/standards/evidence/evidence-based-decision-architecture.md
  - agent-architecture/standards/workspace/workspace-memory-tiers-standard.md
  - agent-architecture/governance/decisions/0005-workspace-data-zones-and-icm-migration.md
  - agent-architecture/schemas/data-zone-artifact.schema.json
---

# Plan — `website-optimizer`

Design and migration plan. Written 2026-10-15, before implementation.
Structure: [ICM System Map form](../icm-architect/references/system-map.md) principles, housekeeping: [Authoring Guide](../authoring-guide.md).

This file is the only source of truth until the referenced files exist.

---

## 1. Purpose

One skill that answers: *is this website good enough to be found, and is it good
enough once found?* It measures and advises. It does not build, host, or deploy.

The material used to exist as nine scattered chore documents in
`hugo-wizard/memory/references/chores/`, with the same three facts restated in
two or three places each:

| Duplicated fact | Occurrences |
|---|---|
| `layouts/robots.txt` with `Sitemap:` directive is mandatory | 3 |
| Search Console URL-prefix rule (submit `sitemap.xml`, not the full URL) | 2 |
| First External Link principle | 3 |
| `python scripts/audit-site-seo.py` invocation | 3, in three different forms |

That was the problem this skill solves: not missing knowledge, but knowledge in
three places with no owner. Six of the nine documents are now stubs pointing
here; `post-migration-seo-checklist.md` deliberately stays as a migration
runbook, and `mobile-optimierung-und-menue.md` stays with the `hugo` skill (D6).

---

## 2. Target structure

Annotated with the state as of 2026-10-15. Everything listed exists unless a
line says otherwise.

```
website-optimizer/
├── SKILL.md                  router + source-of-truth table
├── PLAN.md                   this file
├── decision-log.md           durable decisions D1–D52
├── README.md
├── LICENSE                   MIT
├── references/               13 files
│   ├── seo-core.md           titles, descriptions, canonicals, snippets, Open Graph
│   ├── internal-linking.md   cornerstone content, anchor text, orphans, breadcrumbs
│   ├── indexing.md           robots.txt, sitemap, noindex, GSC, Bing
│   ├── redirects.md          301 chains, wildcards, URL lifecycle, archives
│   ├── structured-data.md    JSON-LD, @graph, schema types, rich results
│   ├── images.md             formats, srcset, dimensions, lazy, favicons, OG images
│   ├── video.md              codec, poster, preload, captions, VideoObject
│   ├── performance.md        LCP/INP/CLS, fonts, budgets, caching
│   ├── accessibility.md      semantics, keyboard, focus, contrast, responsive
│   ├── llm-visibility.md     llms.txt, AI overviews, AI crawlers, extractable content
│   ├── static-sites.md       Hugo robots layout, [sitemap], build-output audits
│   ├── dynamic-sites.md      plugin SEO, WP-CLI, cache invalidation, archives
│   └── sources.md            external provenance, consulted vs inherited
├── scripts/
│   ├── README.md
│   ├── wo.py                 single entry point; subparsers generated from REGISTRY
│   ├── wo/
│   │   ├── envelope.py       standard --json envelope
│   │   ├── config.py         TOML loader, portable + local layers
│   │   ├── errors.py         CapabilityError base (Config/Mapping/Compare/Crawl)
│   │   ├── jsonschema.py     stdlib validator, $ref resolution
│   │   ├── page.py           field extraction from markup or a file
│   │   ├── report.py         run folders, atomic writes, data-zone receipts
│   │   ├── crawl.py          playwright-cli binding, sitemap discovery, wall guard
│   │   ├── pages.py          resolves either source into Page objects (D33)
│   │   └── capabilities/
│   │       ├── on_page/      ← SEO + A11y on-page signals, static or live
│   │       ├── redirects/    ← live: do redirect rules match reality
│   │       ├── images/       ← delivery, dimensions, icons, static or live
│   │       ├── schema/       ← JSON-LD structure and completeness
│   │       ├── links/        ← the internal link graph, build output only
│   │       └── compare/      ← meta: attribute differences between two runs
│   ├── schemas/
│   │   ├── report-base.schema.json        shared by every report
│   │   ├── on-page-report.schema.json
│   │   ├── redirects-report.schema.json
│   │   ├── images-report.schema.json
│   │   ├── schema-report.schema.json
│   │   ├── links-report.schema.json
│   │   └── compare-report.schema.json
│   └── tests/                191 stdlib unittest cases
└── docs/system-map/          ICM Form 6
    ├── README.md  + byte-identical AGENTS.md + routing.md
    ├── CONTEXT.md
    ├── _meta/schema.md
    ├── _templates/{object,process}.md
    ├── objects/              16 cards + CONTEXT.md + _index.md
    ├── processes/            audit-static, audit-live, compare-baseline
    └── effects/CONTEXT.md
```

The parity tests are gone with both reference implementations. `test_crawl.py` and
`test_config.py` replaced them: 169 cases that need no network and no browser.

Rationale for the phase order is in section 8.

---

## 3. Router

In `SKILL.md`, 15 rows. One row per question, one target file. The router never
carries content — if a rule has to be read in the router to be applied, the rule
is in the wrong file.

Negative routing matters as much as positive routing. `SKILL.md` names the
skills this one must not shadow: `hugo` (building), `caddy` (server),
`cloudflare-pages` / `cloudflared` (hosting), `playwright-cli` (browser),
`writing-pro` (copy).

---

## 4. Scripts design

### 4.1 Entry point

```
python scripts/wo.py init-site --site-url https://example.com
python scripts/wo.py on-page                 # static output
python scripts/wo.py redirects                # live redirect rules
python scripts/wo.py images                   # image delivery and icons
python scripts/wo.py schema                   # JSON-LD structure
python scripts/wo.py links                    # internal link graph
python scripts/wo.py compare                  # attribute changes between runs
python scripts/wo.py runs                     # list stored runs
python scripts/wo.py validate-report FILE    # validate against a capability schema
```

One entry point only. Capability modules are packages, not directly executable
scripts. Running `wo.py` puts `scripts/` on `sys.path`, so imports work without
path manipulation (D2). Subparsers are generated from `REGISTRY`, so registering
a capability is the only step needed to expose it (D23).

### 4.2 Pipeline as code

Folder numbering is a weak proxy for execution order, so the order is expressed
by the registry and the entry point rather than by folder names. Each capability
is invoked on its own and writes its own run; `compare` reads those runs.

```
discover  → crawl inputs (static_dir or rendered site) → page set
audit     → one capability per module → findings against schemas/
compare   → current report vs. stored baseline → attributed differences
```

Static and dynamic sites differ only in the first step: a static crawl reads
generated output, a live crawl would render the same page interface. Every
downstream capability is written against the page interface, not against a build
directory.

**Built today:** `on-page`, `images`, `schema` and `links` all take the static
path; `redirects` is live by nature and returns `crawl_mode: live`, and `links`
refuses a live run because a partial graph would describe the crawl rather than
the site. `compare` reads any two runs that share a capability.

### 4.3 The site workspace owns the run, in its declared data zones

There is exactly one baseline per website, and it lives in the consuming
workspace — not in the skill. The workspace holds the store, the skill supplies
the tools.

**Reason:** a baseline is dated evidence of what a site looked like. Evidence
belongs where the site's other evidence lives, versionable and append-only. A
baseline inside the skill repo cannot be reviewed, diffed, or attributed to a
commit.

**Conformance target:** the Workspace Data Zones standard
(`agent-architecture/standards/workspace/workspace-memory-tiers-standard.md`,
normative, v1.3) together with ADR-0002 for the two-pillar model. A workspace
declares its zones via `.agents/workspace-architecture.json` →
`capabilities.data_zones: true`; the linter enforces `WS-D01`/`WS-D02`.

**Three distinct stores, not two.** This distinction is easy to get wrong:

| Store | Zone | Holds |
|---|---|---|
| `website-optimizer/references/` | *none — not a workspace zone* | portable method, shared by every consumer |
| `memory/references/` | References (Säule 1, de jure) | the authoritative record of this site, versioned, review-bound |
| `memory/evidence/` | Evidence (Säule 2, de facto) | audit runs, reports, baselines, receipts — append-only |
| `data/` | *none — bulk storage* | bulky raw crawl output, regenerable, not knowledge |

The skill's own `references/` is the skill's factory, not a workspace zone, and
it is no substitute for a workspace's `memory/references/`: the first is
portable method, the second is authoritative fact about one site. Conflating them
is how a rule learned from four sites silently turns into a fact about the fifth.

**Run-scoped, append-only.** Evidence is logically append-only; corrections
arrive as new entries or superseding records, never by overwriting. A baseline is
therefore not one mutable file:

```
memory/evidence/websites/<domain>/runs/2026-10-15T09-20Z/
    report.json      the findings
    receipt.json     zone metadata, hashes, provenance
memory/evidence/websites/<domain>/runs/2026-10-08T14-05Z/
    ...
```

`compare` takes an explicit earlier run, or the latest run preceding the current
one. Status is derivable by scanning the tree — invariant 9 of ICM, the
filesystem is the state machine. No pointer file exists to drift.

**Writing standard-shaped data before the workspace migrates.** A consumer may
not have declared its zones yet. That is not a reason to invent a fallback
layout: runs are written to the standard zones from the first run, with two
conditions.

1. **The receipt is written from run one**, even though nothing enforces it yet.
   That makes every artifact self-describing, so a later migration is a file
   move (`prepare_destination` returns `move`) rather than a reconstruction from
   memory. An artifact without zone metadata is the thing that gets lost.
2. **The missing declaration stays a tracked chore** in the consuming workspace.
   Otherwise undeclared zone data accumulates silently while the linter error
   sits untouched in the corner.

Writing into the zones introduces no new lint finding on the way there:
`WS-D02` only fires once `capabilities.data_zones` is declared, and `WS-M01`
already passes in a workspace that has both `memory/references/` and
`memory/evidence/`. Early conformance is strictly closer to the standard, never
further from it.

**Config versioning.** `site.optimizer.toml` is committed and carries only
portable values: site URL, crawl limits, which capabilities run.
Machine-specific paths live in untracked `site.optimizer.local.toml`. A config
that mixes both cannot be committed without leaking one workstation's layout
into every fork of the workspace. (Format is TOML, not YAML — D20.)

### 4.4 Reports conform to the data-zone artifact schema

`schemas/report-base.schema.json` carries what every report needs; each capability
adds its own schema via `allOf` (D23). The envelope is generated in
`wo/envelope.py`, never built per tool.

Each run additionally writes a `receipt.json` conforming to
`agent-architecture/schemas/data-zone-artifact.schema.json`. Its field names are
the house vocabulary and are not to be reinvented:

| Field | Carries |
|---|---|
| `zone`, `trust_level`, `status` | `evidence`, `observed`, `active` |
| `source_uri`, `source_version` | the site URL, the tool version |
| `artifact_sha256` | hash of the report |
| `synced_at`, `converter` | run timestamp, tool identity |
| `data_classification`, `retention_class`, `owner` | required before promotion |
| `promotion_policy` | whether this run may be promoted at all |

**Why the standard's field names rather than our own:** a receipt shaped like
`provenance: {tool_version: …}` cannot be validated by the workspace linter or
read by any tool that speaks the house schema. One vocabulary, checked by
machinery that already exists, beats a private one that nothing checks.

**Why it matters for `compare`:** a live crawl is not deterministic, so
provenance must be recorded to tell a real change from rendering noise. It is
reported as a qualifier on the comparison, never used as a filter (D25).

Every report also carries `capability` and `rules_run` — every rule id the
capability could emit, fired or not. Without `rules_run`, "the page is clean"
and "this check did not run" are the same observation, and `compare` cannot tell
a new rule from a broken page.

### 4.5 External tools are declared dependencies, not silent assumptions

Live crawling renders pages, which needs a browser. `playwright-cli` exists as a
skill on this system and is **presumed available** for the parts that need it.
It is invoked as an external CLI through a subprocess, never imported as a
Python dependency — the skill stays stdlib-only either way.

| Consequence | Detail |
|---|---|
| Declared, not assumed | `SKILL.md` names `playwright-cli` as a dependency of the live path; the catalog entry references it |
| Probed at runtime | version and availability are checked before a crawl and recorded in `provenance` |
| Self-correcting failure | if the tool is missing, the error states what is missing and how to obtain it, instead of a stack trace |
| Graceful degradation | every static-side capability runs without it; only live mode requires it |
| Rendering ≠ analysis | capabilities receive the rendered page interface, never the browser API |

Live mode is therefore not optional-future: it is designed for, and the
`dynamic-sites.md` reference is verifiable rather than merely procedural.

### 4.6 Crawled pages are untrusted external content

This skill ingests content it does not control: arbitrary websites, their HTML,
their metadata, their text. That is the trust class the standard assigns to the
Cloud zone — `trust_level: untrusted_external` with
`instructions_are_data: true`.

Rules that follow, none of them optional:

- Page content is **data, never instruction**. Text on a crawled page can never
  alter which checks run, which thresholds apply, or how a report is written.
- The crawler extracts fields — tags, attributes, dimensions, status codes — and
  never carries page prose into a report or into an agent's context.
- A finding quotes the extracted value and its source location, never a passage
  of page text.
- The report names which pages were crawled and treats each as untrusted input.

**Reason:** OWASP LLM09 and the Cloud-zone rule exist because external content in
an agent context is an injection surface. A tool that renders arbitrary sites is
a deliberate ingestion path, so the treatment is declared rather than assumed.

### 4.7 House rules

- Python 3, standard library only, no pip dependencies.
- `pathlib.Path`, forward slashes, LF line endings, `#!/usr/bin/env python3`.
- `--json` with the standard envelope on every command.
- Self-correcting error messages; atomic writes via `tempfile` + `os.replace`.
- Dry-run where a command could write anything outside its own output directory.

---

## 5. System map design

Form 6 over the script subsystem. It maps tools, contracts, and artifacts. It
does **not** map the SEO rules — those belong to `references/`, and duplicating
them in cards would create the second copy this skill exists to remove.

Objects (nouns): `envelope`, `audit-report`, `provenance`, `site-config`,
`site-workspace`, `page`, `audit-run`, `finding`, `baseline`, `redirect-rule`,
`capability-contract`.

Processes (verbs, only movements that actually run): `audit-static`,
`audit-live`, `compare-baseline`.

The card that pays for itself:

```
If you change this — envelope schema
  Hits:        every capability module, scripts/README.md,
               objects/envelope.md (sync required)
  Does not hit: references/* (rules are envelope-independent),
               any rule file
```

`Does not hit` names the obvious wrong neighbour. That is the information the
current three-chores-and-no-owner situation cannot produce.

**Synchronicity:** any change to schemas, contracts, state machines, or
interfaces updates this map in the same commit (per repo AGENTS.md).

---

## 6. Migration out of `hugo-wizard`

Reference integrity rule: copy, verify parity, then remove. Nothing is deleted
before its consumers are updated.

| Source (hugo-wizard) | Destination | Fate | State |
|---|---|---|---|
| `chores/seo-opengraph-schema-accessibility-checkliste.md` | `seo-core` + `structured-data` + `images` + `accessibility` | stub with `delegated_to:` | done |
| `chores/seo-launch-und-content-leitfaden.md` | `seo-core` + `indexing` | stub; Yoast provenance → `sources.md` | done |
| `chores/post-migration-seo-checklist.md` §3–§4 | distributed across references | §1–§2 and §5 **stay** as the WordPress→Hugo runbook | done |
| `chores/add_favicon.md` | `images.md` | stub | done |
| `chores/llm-lesbare-inhalte.md` | `llm-visibility.md` | stub; content enriched before stubbing | done |
| `chores/add-llms-txt.md` | `llm-visibility.md` | stub | done |
| `chores/mobile-optimierung-und-menue.md` | **stays** in `hugo` (D6) | no stub; only generalized parts mirrored | done |
| `scripts/audit-site-seo.py` | `capabilities/on_page/` | ported, parity verified on 173 pages, removed | done |
| `scripts/verify-redirects.py` | `capabilities/redirects/` | ported, parity verified on 53 live rules | removed 2026-10-16 after the capability was re-verified standalone |

Remains in hugo-wizard by design: `memory/references/websites/<domain>.md` (site
decisions) and `memory/evidence/` (execution records). Those are the evidence
architecture's job, not the skill's.

### 6.1 Referrer status

- `hugo-wizard/scripts/README.md` — updated to point at `wo.py on-page`; the
  file also carries an unrelated pre-existing edit to the live-stack logging
  line, which was committed alongside it.
- `memory/references/websites/*.md` — no remaining references to either script.
- `memory/evidence/websites/<domain>/*.md` — historical record, links adjusted
  where they existed, content never rewritten.
- `.agents/upstream.lock.json` and `AGENTS.md` — skill registered and pinned;
  **the pinned commit is stale** and needs a pointer refresh.

---

## 7. Explicit non-goals

- Not a CMS, not a builder, not a hosting or deployment skill.
- Not a crawler framework: one crawl implementation, one page interface.
- Not an analytics dashboard: it consumes Search Console exports, it does not
  reproduce them.
- No rule enters `references/` without a source, whether an official
  specification, vendor documentation, or a dated external article.

---

## 8. Phases

### Round 1 — scaffold — **done**

`SKILL.md`, `PLAN.md`, `decision-log.md`, `README.md`, `LICENSE`, `.gitignore`.
No catalog entry, no git repository, no submodule (D7).

### Round 2 — one capability end to end — **done**

`wo.py`, envelope, config loader, report writer, schemas, tests, and the
`on-page` capability rebuilt from `audit-site-seo.py` with `--json` added.
Parity verified against the original on a real 173-page site: 0 findings lost,
0 invented. First evidence run written into `hugo-wizard`'s Evidence zone, with a
receipt validated against the real `data-zone-artifact.schema.json`.

Met: schema-valid reports, parity on real data, baselines in the workspace,
catalog entry plus `validate-skills-catalog.py` passing, private GitHub repo and
submodule set up.

**The `hugo-wizard` chore stubs moved to round 3a, not round 2.** An earlier
version of this plan put them here; that was wrong. A stub replaces content with
a pointer to a reference file, and the reference files did not exist yet. Writing
the stubs first would have left six pointers at files that cannot be opened —
named but not wired, the ghost case — and deleted working knowledge from
`hugo-wizard` with nothing taking its place. Reference integrity is
copy-verify-remove: a home is never removed before the new home exists.

### Round 3a — references, then the chore stubs — **done**

Thirteen reference files, each with `evidence_level`, `support_level`, source
anchors and a review date. As each topic file landed, the matching chore was
verified against it and only then reduced to a stub. `llm-visibility.md` was
enriched with the page-structure rules from `llm-lesbare-inhalte.md` *before*
that chore was stubbed, so the stub could not drop content that had no home yet.

### Round 3b — the system map — **done**

`docs/system-map/` built slice by slice, with a human gate per slice. Thirteen
object cards and two process cards, each citing `path:line` at the revision it
describes and carrying first-order waterfalls. `AGENTS.md` and `routing.md` are
byte-identical twins of `README.md` and are generated, never hand-edited.

**Catalog blast radius is `workspace_scoped`, not `read_only`.** The skill writes
reports and baselines into the consuming workspace by design.

### Round 4 — capabilities — **done**

| Capability | State | Verified by |
|---|---|---|
| `on-page` | done | parity vs. the original, 173 pages; then against a real WordPress site |
| `redirects` | done | parity vs. the original, 53 live rules |
| `images` | done | 173 pages; every rule re-counted independently, one false-positive class found and removed; re-derived exactly from live crawl artifacts |
| `schema` | done | 173 blocks, 4 types; found a real `#artist` `sameAs` inconsistency |
| `compare` | done | regression, improvement, check-change, site-change |

Kept separate so a failing capability never blocked the map or the references.
Live rendering is round 5, not a sixth capability.

### Round 5 — live page rendering — **done**

`page.extract_page_from_html` as the single new extraction entry point;
`wo/crawl.py` binding `playwright-cli`; `wo/pages.py` resolving either source
into `Page` objects so no capability grows a `--live` branch. On request only,
never from a hook (D26). Crawl artifacts beside the run in the data zone (D27).

Verified against the reference site: 25 pages read from the build directory and
rendered in a browser, compared page by page per capability. All three identical.
The consent wall of D26(d) is now detected rather than merely documented — most
identical pages raise instead of reporting.

Then driven by a real WordPress requirement, which found two more:
sitemaps are indexes and must be followed (D37), and a canonical on another host
is a configuration hint rather than a page defect (D38).

New decisions: D32 (a crawl reports its reach), D33 (one code path), D34 (the
wall guard), D35 (UTF-8, not the terminal's encoding), D36 (no shell).

### Round 6 — housekeeping — **partly done**

- ~~Refresh `.agents/upstream.lock.json` and `AGENTS.md` in `hugo-wizard`~~ done.
- ~~Rewrite the `skills-catalog.yaml` entry~~ done.
- ~~Delete `verify-redirects.py` once its remaining referrers are checked~~ done
  2026-10-16. The capability was re-verified standalone first — 53 live rules,
  53 passed, 0 failed, the same figure the parity check produced — then the
  script was removed. Seven referrers were rewritten; the three that remain are
  the ones dating the migration, which are correct as they stand.

  One capability of the original has no successor: `--test-route`, the inline
  single-route check. For that case there is `curl -I`. Named in both the
  workspace README and the runbook, because a migration that quietly drops a
  feature reads as equivalence.
- ~~Decide on CI~~ decided 2026-10-16: no CI, run manually at launch or on
  demand. D39. The 169 tests run in under three seconds and need no network. The
  cost is that a rule regression now reaches a site audit before anyone notices;
  revisit if the skill is bound in more than two workspaces.

### Round 7 — open findings from verification

Verifying the image capability against the built output (round 6) produced items
that were not on any list:

- Fixed: `--config` silently dropped the local overlay, so the documented
  invocation could not see a configured site at all. D29.
- Fixed: `<img>` without a `src` was counted three times over, including as a
  critical missing dimension. 140 of 469 critical findings on the reference site
  described elements that download nothing. Now `image.src_missing`. D31.
- ~~`image.loading_unset` misses every page with a mixed `loading`
  declaration~~ partially closed 2026-10-16. `image.loading_partial` now raises
  the question per page instead of leaving it unasked; the fold measurement that
  would answer it exists but is not run automatically. D40. The reference site's
  run went from 1209 to 1330 findings, the 121 added being exactly the pages
  that had been silent.

### Round 8 — open per platform

Found by asking whether the skill could be bound into `wordpress-wizard`, which
it could not until the sitemap fix existed.

- `redirects` has no source where the rules are not a file. **Not open work — a
  trigger.** Build it when a specific site has redirects that are not in a file
  and someone asks for the audit; that site then supplies the input and the test
  fixtures at the same time. D47. Until then, switching the capability off per
  site with the reason in the config is the whole answer, and doing so is safe
  because the wrong way in raises loudly with the trap and the way out (D46).
- Consent handling is answered, not deferred. `[crawl] profile` lets a site name
  a browser profile that has already accepted its cookie banner; a relative path
  resolves against the workspace, so the profile can live per agent workspace or
  per machine at the user's choice. Off unless configured, because a persistent
  profile directory holds session cookies and must not be created unasked. D41.
  Never yet exercised against a real consent wall - the guard is tested, the
  escape hatch is not.

**The lesson worth keeping:** all four verification claims from round 2 passed,
and all three defects above were outside anything they covered. Parity checks
prove a port did not lose the original's rules. They say nothing about whether
the rules themselves are right. That question needed a second opinion from the
data, not a third look at the code.

### Round 9 — guarding the map (done)

`test_system_map.py`. The map drifts the same way the code does and had no guard:
a rule changes, the card keeps describing the old rule set. It happened three
times in one week.

The guard checks citations rather than completeness, and the distinction is the
whole design: demanding that every rule appear in the map would make it a second
source of truth, which is what goes stale. It found a real stale reference on its
first run. D48.

### Round 10 — the internal link graph (done)

Asked what the skill was still missing, well after it was finished, the answer was
one shape repeated: a reference file describing something no rule measured.
`internal-linking.md` was 102 lines about orphan pages, anchor text and crawl
budget with nothing behind any of it — and broken internal links, the commonest
architectural defect there is, were not visible at all. `page.py` read `<a>` for
exactly one thing: whether it was a skip link.

Four more gaps came out of the same review and are filed as issues rather than
fixed here — `robots.txt` and sitemap integrity, `hreflang`, pagination, video
delivery, and the redirects source D47 deferred. This round closed the one that
was both common and invisible.

**What landed.** `Page.links`, carrying `href` and nothing else, because an
anchor's text is authored prose and D13 has no place for it (D50). A sixth
capability with three rules: a URL the build does not serve, a page nothing
reaches from `/`, and a page four or more clicks deep (D51). Static only, and it
raises on `--live` rather than drawing a graph of a crawl and calling it the
site. One finding per missing URL rather than one per linking page (D52).

**Measured on the reference site, first run:** 173 pages, 2884 internal links, 3
broken targets, 7 unreachable pages, 0 deep. Every one was checked by hand in the
markup. The three broken links are absolute `www` URLs left from a previous site
structure that no longer answers; the seven orphans are four generated taxonomy
lists and three pages of test content the navigation never reaches.

**What this round did not do.** Anchor text, redirect-aware resolution, and links
added by JavaScript stay out of the graph, each for a stated reason rather than by
oversight — `capabilities/links/README.md` names them, and
`references/internal-linking.md` now says which of its own rules the tool cannot
check.

---

## 9. Source authority — settled by the house vocabulary

**No new vocabulary.** The Dual Evidence Framework (ADR-0002,
`evidence-based-decision-architecture.md`, normative) already defines the axes a
rule needs. This skill uses them rather than inventing `spec` / `practice` /
`observed`:

| Axis | Values | Where it is written |
|---|---|---|
| Zone (pillar) | `references` = de jure, `evidence` = de facto | the store a file lives in |
| `evidence_level` | `normative`, `observed` | file front matter |
| `trust_level` | `trusted_curated`, `observed`, `untrusted_external`, `working` | artifact receipts |
| `support_level` | `fully_supported`, `partially_supported`, `unsupported` | per rule, per claim |

**How this resolves the original question.** Vendor guidance such as the Yoast
material is not a third class — it is a `references/` file whose claims each
carry a `support_level`. The First-Link principle is `partially_supported` with
the article cited; the `layouts/robots.txt` sitemap directive is `observed`,
dated, with the sites it was learned from named. A claim that is only our own
reasoning is `unsupported` until a run supports it, and an unsupported claim
triggers a review gate instead of being quietly stated as a rule.

**Mechanics.**

- In-situ attribution (ALCE rule 3): every reference file carries `references:`
  anchors in its front matter at the moment it is written. Attribution is never
  added post-hoc — post-hoc attribution fails in over half of all attempts.
- `references/sources.md` remains the log: URL, date consulted, what it taught,
  which file cites it. Same convention as the `hugo` skill.
- Undocumented or proprietary behaviour is never a rule. Undocumented ranking
  factors go into `sources.md` as an explicitly unverified note, or nowhere.
- Each `observed` rule carries its date and a revalidation trigger. Undocumented
  behaviour ages silently; the Hugo `robots.txt` trap is valid in 2026 and will
  not stay valid forever.

**Factored verification applies to the tool, not only to agents.** A capability
must not read a narrative conclusion before it measures. Findings are atomic
facts — `rule_id`, observed value, expected value, source location,
`support_level` — and the verdict is derived afterwards. This is FActScore
atomicity and CoVe isolation applied to auditing: a checker that has already read
"this site is fine" does not independently re-derive it.

## 10. Classification and retention

Accepted as D19. The reasoning is kept here because it is the part that gets
re-litigated; the decision itself lives in `decision-log.md`.

The data-zone schema requires `data_classification` and `retention_class` on
every artifact. Accepted values:

**Classification: `internal` by default, escalating to `confidential` on
contact with non-public surface.**

| Value | When |
|---|---|
| `public` | never the default — see below |
| `internal` | a crawl of a public site with no authenticated or private surface |
| `confidential` | the crawl touched authenticated URLs, a staging host, or an internal hostname |
| `restricted` | never for audit runs; reserved for secrets and personal data |

**Why not `public` as the default.** The audited site is public, so the report
superficially looks public — and that is exactly the trap. A crawl surfaces
material the site owner never intended to publish: `robots.txt` routinely names
`/admin/`, sitemaps leak staging hosts, canonicals and verification meta tags
carry internal hostnames, and analytics scripts name tenant and advert IDs. A
report marked `public` on that basis invites being committed to a public
repository. `internal` keeps it versionable — which the standard permits — while
leaving the escape hatch for the case where it matters.

**Why the escalation is a run-level decision, not a per-finding one.** A single
run either met private surface or it did not; that fact belongs to the run. The
receipt records it once, and `data_classification` is decided from the crawl
inputs, not guessed while writing findings.

**Retention: two named classes, because two different things are being kept.**

| Class | Applies to | Rule |
|---|---|---|
| `audit-run` | reports and receipts in `memory/evidence/` | kept for as long as the site record is active; minimum 24 months; nothing is auto-purged; a superseded run is never overwritten or deleted |
| `crawl-ephemeral` | raw crawl output in `data/` | regenerable at will, git-ignored, freely deletable |

**Why not a plain number like "12 months".** The run history is the only record
of *when* a regression appeared — deleting it destroys the one thing `compare`
exists to provide. And the standard is explicit that "archived" without a named
target path and a retention decision is not a valid state, so the class has to
name a procedure rather than a duration. Legal hold and statutory deletion still
override both classes; the standard is clear that evidence is append-only but
not undeletable.

**Retention is not uniform over time, only over class.** Within `audit-run`,
the newest run is the working reference and older runs are superseded — that is
the `status` field, and superseded runs stay readable.

## 11. Settled

Closed on 2026-10-15, recorded in `decision-log.md`:

- **Baseline location** — in the consuming workspace, in the site's Evidence
  zone as append-only run folders; not in the skill. See 4.3, D8.
- **Live crawl** — `playwright-cli` is presumed available and is a declared
  dependency of the live path, invoked as an external CLI. See 4.5, D9.
- **Catalog blast radius** — `workspace_scoped`, settled by 4.3. See 4.4 and
  round 2, D10.
- **First capability name** — `on-page`, not `seo`. See D11.
- **Source authority** — house vocabulary, no invented classes. See §9, D14.
- **Crawled content** — untrusted external, data never instruction. See 4.6, D13.
- **Pre-migration workspaces** — standard-shaped data is written from run one,
  with receipts, even where zones are not yet declared. See 4.3, D16.
- **`owner`** — always the consuming workspace slug. See D17.
- **Phase order** — round 3 splits into 3a references, 3b system map. See D18.
- **Finding shape** — atomic facts, derived verdict. See D15.
- **Classification and retention** — `internal` default with escalation,
  `audit-run` / `crawl-ephemeral` retention. See §10, D19.

No open design questions remain. Everything below is either an approval gate or
mechanical implementation inside round 2.