# Decision Log

Durable decisions for this skill, with the reason. Entries are append-only.

Every entry carries `support_level`. A decision justified by an architecture
standard is `fully_supported` and names the anchor. A decision that is our own
reasoning is `partially_supported` until a run or a precedent settles it — and
saying so is the point of the field, not an admission of weakness.

## D1 — Single skill with a router, not one skill per topic

**Date:** 2026-10-15
**Status:** accepted

A `website-optimizer` superskill with a compact dispatch table in `SKILL.md`,
instead of separate `static-site-seo`, `image-optimization`, `schema-markup`
skills.

**Reason:** The topics share one workflow (discover → audit → compare) and one
report format. Splitting them would duplicate the router logic across skills and
force the agent to load three entry files to answer one question. The blast
radius is contained: one skill, one workflow, one artifact.

**Consequence:** The `description` must stay narrow enough not to shadow
`hugo`, `caddy`, `cloudflare-pages`, and `playwright-cli`. The "Not this skill"
section in `SKILL.md` is part of the design, not documentation nicety.

## D2 — One entry point, capabilities as packages

**Date:** 2026-10-15
**Status:** accepted

Scripts use a single entry point `scripts/wo.py` with Python packages beneath
it (`scripts/wo/`, `scripts/wo/capabilities/<name>/`). Not a flat
`scripts/<tool>.py` layout.

**Reason:** Running a script puts its own directory on `sys.path`, so package
imports work without path manipulation. More importantly it makes the pipeline
order executable: `wo.py run-all` performs discover → audit → compare, so the
sequence lives in code instead of in folder numbering. Capabilities share one
envelope, one report schema, and one config loader without copy-paste.

**Deviation:** `authoring-guide.md` prescribes flat `scripts/<tool>.py`. The
guide permits documented justification for deviations; this entry is that
justification.

**Consequence:** There is exactly one entry point. Capability modules are not
directly executable, which prevents two entry points from drifting apart.

## D3 — Report shape is a schema file, not prose

**Date:** 2026-10-15
**Status:** accepted

The audit report conforms to `scripts/schemas/audit-report.schema.json`. The
`--json` envelope is generated centrally, never hand-built per tool.

**Reason:** The structured CLI envelope is required by the authoring guide, but
five tools each building their own envelope is five places to get it wrong.
A machine-readable schema is also the only way to verify backward compatibility
of saved baselines.

**Consequence:** The schema is an interface. Changing it requires a synchronous
`docs/system-map/` update in the same commit (system map synchronicity rule).

## D4 — Capabilities are earned, not scaffolded

**Date:** 2026-10-15
**Status:** accepted

Round 2 delivers exactly one capability (`on-page`). Additional capabilities
(`images`, `schema`, `redirects`, `compare`, `discover`) are added only after
the first runs end to end.

**Reason:** Designing five tools before the envelope, schema, and config are
proven produces five half-finished tools that must be debugged at once. The
config file and baseline concept only pay off once a report exists end to end.

**Consequence:** Empty or speculative capability folders are not created. A
folder appears when its first working tool lands.

## D5 — Static/dynamic split only where the action differs

**Date:** 2026-10-15
**Status:** accepted

Two references carry a static/dynamic split: `references/static-sites.md` and
`references/dynamic-sites.md`. Everything else is platform-neutral.

**Reason:** Splitting everywhere inflates the file count without changing any
instruction. A title formula or an `alt` text rule is identical on both sides;
only generator output versus rendered output, and plugin/CMS mechanisms, actually
differ in the action required.

## D6 — Responsive layout guidance stays with `hugo`

**Date:** 2026-10-15
**Status:** accepted

`mobile-optimierung-und-menue.md` (hugo-wizard) stays in the `hugo` skill. Only
its stack-neutral parts are mirrored here.

**Reason:** Breakpoint discipline, media-query de-duplication, and clickable-box
patterns are Hugo/CSS craft guidance. What belongs here is only the part that is
an accessibility or performance question: responsive layout as an accessibility
obligation, and layout-shift risk as a performance factor.

**Consequence:** `references/accessibility.md` and `references/performance.md`
carry the generalized statements and link onward; they do not restate the Hugo
workflow.

## D7 — No catalog entry until the skill can act

**Date:** 2026-10-15
**Status:** accepted

`skills-catalog.yaml` is not updated in round 1, only in round 2.

**Reason:** The catalog is the discovery source of truth for other workspaces.
An entry promising audits and improvements while no capability exists is a false
promise that shadows nothing and misleads everything. Registration follows the
first working capability, not the scaffold.

**Consequence:** `scripts/validate-skills-catalog.py` is run in round 2, after
the catalog entry is added.

## D8 — Baselines live in the site workspace, not in the skill

**Date:** 2026-10-15
**Status:** accepted

Each website gets a folder in the consuming workspace, following that
workspace's own conventions. Baselines, reports, and crawl artifacts are written
there. The skill stores no run state.

**Reason:** a baseline is dated evidence about a site. Evidence is only useful
if it is reviewable, diffable, and attributable to a commit — which means it
belongs where the site's other evidence lives, not inside a shared skill repo
where it would be invisible to the workspace and unreviewable by its owner.

**Consequence:** the skill defines *roles* (site record, site config, run
products, local overrides) and never paths. The workspace maps roles to its own
layout. In `hugo-wizard` that means `memory/references/websites/<domain>/` for
the record and `data/websites/<domain>/` for generated products, honouring its
existing data/crawl separation rule.

**Superseded in scope by D12:** baselines live in the site's Evidence zone as
append-only run folders, not as a single mutable file.

## D9 — `playwright-cli` is a declared dependency of the live path

**Date:** 2026-10-15
**Status:** accepted
**support_level:** fully_supported
**references:** `skills/playwright-cli/SKILL.md`

Live page rendering assumes `playwright-cli` is available on the system. It is
invoked as an external CLI via subprocess, probed for version at runtime, and
recorded in the run receipt's `source_version`. It is never imported as a Python
dependency.

**Reason:** the alternative — describing dynamic-site handling procedurally
because no browser is guaranteed — leaves the entire dynamic branch unverifiable.
Rendering is what makes `dynamic-sites.md` testable instead of advisory.

**Consequence:** the skill stays stdlib-only, because a subprocess call is not an
import. Every static-side capability runs without the tool; only live mode
requires it, and its absence produces a self-correcting error naming what is
missing, not a traceback.

## D10 — The catalog blast radius is `workspace_scoped`

**Date:** 2026-10-15
**Status:** accepted

The catalog entry declares `workspace_scoped`, not `read_only`.

**Reason:** D8 makes writing reports and baselines into the consuming workspace
the intended behaviour. A narrower declaration would be false at the moment the
first capability runs, and a blast radius that understates itself is worse than
one that overstates itself.

**Consequence:** review mode remains the default for consumers, and dry-run
applies to any command that would write outside its own output directory.

## D11 — The first capability is called `on-page`

**Date:** 2026-10-15
**Status:** accepted

The first capability module is `capabilities/on-page/`, invoked as
`wo.py on-page`.

**Reason:** it audits on-page signals — titles, descriptions, canonicals, heading
structure, headings and alt text. Naming it `seo` would promise the whole of
search visibility, which lives across `indexing`, `structured-data`, and
`redirects` too. A capability whose name overpromises gets invoked for jobs it
cannot do, and the router then needs a second sentence explaining the mismatch.

**Consequence:** `seo-core.md` keeps its name — that is a reference about search
basics, not a capability — but the capability and the reference are distinct
namespaces and must not be conflated in the router.

## D12 — Conformance with the Dual Evidence Framework and Data Zones standard

**Date:** 2026-10-15
**Status:** accepted
**support_level:** fully_supported
**references:**
  - `agent-architecture/governance/decisions/0002-dual-evidence-framework-and-factored-verification.md`
  - `agent-architecture/standards/evidence/evidence-based-decision-architecture.md`
  - `agent-architecture/standards/workspace/workspace-memory-tiers-standard.md`
  - `agent-architecture/governance/decisions/0005-workspace-data-zones-and-icm-migration.md`

Run products follow the house data zones rather than an invented layout. The
site's authoritative record stays in `memory/references/`; audit runs, reports,
and baselines go to `memory/evidence/` as append-only, run-scoped folders;
receipts conform to `data-zone-artifact.schema.json`; bulky raw crawl output
stays in `data/`.

**Reason:** these are normative, `applies_to: all`, and already validated by the
workspace linter (`WS-M01`, `WS-M02`, `WS-D01`, `WS-D02`). A private layout
would be unenforceable by any existing check and would fork the vocabulary that
other workspaces already read.

**Three corrections this produced:**

1. **The skill's `references/` is not a workspace zone.** It is portable method.
   A workspace's `memory/references/` is authoritative fact about one site.
   Keeping them distinct is what stops a rule learned from four sites becoming a
   fact about the fifth.
2. **A baseline is not a mutable file.** Evidence is logically append-only, so
   runs are folders under `memory/evidence/websites/<domain>/runs/<timestamp>/`
   and `compare` names an earlier run. No pointer file exists to drift.
3. **Receipts use the house field names** — `source_version`, `synced_at`,
   `converter`, `artifact_sha256`, `promotion_policy` — instead of a private
   `provenance` block, so the workspace linter can read them.

**Consequence:** the workspace, not the skill, owns zone placement. This skill
defines what a run produces; it never says where the run lives.

## D13 — Crawled page content is untrusted external data

**Date:** 2026-10-15
**Status:** accepted
**support_level:** fully_supported
**references:**
  - `agent-architecture/standards/workspace/workspace-memory-tiers-standard.md` (Cloud zone, `instructions_are_data`)
  - `agent-architecture/standards/evidence/evidence-based-decision-architecture.md` (OWASP LLM09)

Crawled pages are treated as untrusted external content. Page text is data and
never instruction: it cannot change which checks run or which thresholds apply.
The crawler extracts fields and never carries page prose into a report or an
agent context. Findings quote extracted values with a source location.

**Reason:** this skill renders arbitrary websites. That is a deliberate ingestion
path for attacker-controlled content, and the standard already assigns exactly
this trust class to mirrored external sources. Declaring the treatment is
cheaper than discovering the injection later.

**Consequence:** each run records which pages were crawled and marks them
untrusted. This applies to live crawling most sharply, but static output is
author-generated content on the same site and gets the same handling.

## D14 — Source authority uses the house vocabulary, not invented classes

**Date:** 2026-10-15
**Status:** accepted
**support_level:** fully_supported
**references:**
  - `agent-architecture/standards/evidence/evidence-based-decision-architecture.md`
  - `agent-architecture/governance/decisions/0002-dual-evidence-framework-and-factored-verification.md`

Rules are weighted with the existing axes — zone, `evidence_level`,
`trust_level`, and a per-claim `support_level` — instead of a new
`spec`/`practice`/`observed` scheme. Vendor guidance is not a third class; it is
a references file whose claims carry a support level.

**Reason:** the original three-class proposal was our own vocabulary. Inventing
one duplicates terms that already carry agreed meanings across every workspace,
and an agent that has learned `support_level: unsupported` elsewhere does not
know what our `observed` means.

**Consequence:** attribution happens in situ in front matter when a file is
written, never post-hoc. A claim resting only on our own reasoning is marked
`partially_supported` and triggers a review gate instead of being stated as a
rule. Undocumented ranking factors are never rules.

## D15 — Findings are atomic facts; the verdict is derived

**Date:** 2026-10-15
**Status:** accepted
**support_level:** fully_supported
**references:**
  - `agent-architecture/standards/evidence/evidence-based-decision-architecture.md` (FActScore atomicity, CoVe isolation)

A capability measures without reading any narrative conclusion. Each finding is
an atomic fact — rule, observed value, expected value, source location, support
level — and the verdict is computed from the findings afterwards.

**Reason:** a checker that has already read "this site is fine" does not
independently re-derive it. The same exposure bias that makes a model repeat its
own draft makes an auditor confirm a page summary it was handed.

**Consequence:** the report schema makes `support_level` mandatory per finding,
and no capability is allowed to accept prose context about a page's quality as
input.

## D16 — Standard-shaped data is written before the workspace has migrated

**Date:** 2026-10-15
**Status:** accepted
**support_level:** fully_supported
**references:**
  - `agent-architecture/standards/workspace/workspace-memory-tiers-standard.md`
  - `agent-architecture/scripts/lint_workspace.py` (`WS-D01`, `WS-D02`, `WS-M01`)
  - `agent-architecture/scripts/migrate_workspace.py`

Runs are written to the standard zones from the first run, even when the
consuming workspace has not declared `capabilities.data_zones` yet. No fallback
layout, no interim folder.

**Reason:** conformance is a direction, not a switch. Writing early introduces no
new lint finding — `WS-D02` only fires after the declaration exists, and `WS-M01`
already passes in a workspace holding both pillars — while a private interim
layout would be a second vocabulary that the eventual migration then has to
translate. The migration script treats a zone-conformant tree as `move`, not as
a merge.

**Conditions:** the receipt is written from run one, so artifacts are
self-describing and migration stays a file move; and the missing declaration
remains a tracked chore in the consuming workspace, because undeclared zone data
otherwise accumulates behind an unattended lint error.

## D17 — `owner` in every receipt is the workspace slug

**Date:** 2026-10-15
**Status:** accepted
**support_level:** fully_supported
**references:**
  - `agent-architecture/standards/workspace/workspace-memory-tiers-standard.md`
  - `agent-architecture/schemas/data-zone-artifact.schema.json`

The `owner` field carries the slug of the consuming workspace, for example
`hugo-wizard`. It is not the skill, not the tool, and not a person.

**Reason:** evidence belongs to the workspace that observed it, and the standard
makes owner mandatory precisely so a reviewer can ask whose observation this is.
Writing `website-optimizer` would name the instrument instead of the observer —
and the instrument is already recorded in `converter` and `source_version`.

**Consequence:** the slug is resolved from the workspace root, never passed as
free text. Two workspaces auditing the same site produce receipts naming
different owners, which is correct.

## D18 — Round 3 is split: references first, system map second

**Date:** 2026-10-15
**Status:** accepted
**support_level:** partially_supported
**references:**
  - `icm-architect/references/system-map.md`

Round 3 becomes 3a (the reference set) and 3b (the system map), in that order.

**Reason:** references deliver the actual knowledge and depend on no tool, while
object cards must cite a working implementation to reach `status: verified`.
Doing both together either blocks the references on the tool or writes cards
whose citations do not exist yet.

**Support caveat:** the split is reasoned from the ICM card requirements, not yet
proven by a run. It stays `partially_supported` until round 2's exit conditions
show the citation targets are stable.

## D19 — Classification and retention for run artifacts

**Date:** 2026-10-15
**Status:** accepted
**support_level:** fully_supported
**references:**
  - `agent-architecture/schemas/data-zone-artifact.schema.json`
  - `agent-architecture/standards/workspace/workspace-memory-tiers-standard.md`

`data_classification` defaults to `internal` and escalates to `confidential` when
a run touches authenticated URLs, a staging host, or an internal hostname. It is
never `public` by default and never `restricted`. `retention_class` is one of two
named classes: `audit-run` for reports and receipts, `crawl-ephemeral` for raw
crawl output.

**Reason.** The audited site being public makes a report look public, which is
the trap: a crawl surfaces what the operator never intended to publish — admin
paths in `robots.txt`, staging hosts in sitemaps, internal hostnames in canonicals,
tenant identifiers in analytics tags. `internal` keeps runs versionable, which the
standard permits, and leaves the escape hatch for the case that needs it.
Retention is a procedure rather than a duration because the run history is the
only record of when a regression appeared, and because the standard holds that
"archived" without a named target path and a retention decision is not a valid
state. Legal hold and statutory deletion still override both classes.

**Consequence.** Classification is decided once per run from the crawl inputs and
recorded in the receipt, never guessed while writing findings. Within `audit-run`
the newest run is the working reference and older runs are `superseded` but stay
readable.

## D20 — Site configuration is TOML, not YAML

**Date:** 2026-10-15
**Status:** accepted
**support_level:** fully_supported
**references:**
  - `../authoring-guide.md` (Python-first, standard library only, zero pip dependencies)

Configuration is `site.optimizer.toml`, read with `tomllib`.

**Reason:** Python 3.11 shipped `tomllib` in the standard library; YAML did not.
The authoring guide mandates stdlib-only with zero pip dependencies, so a YAML
config would either break that rule or silently rely on PyYAML being installed on
one particular machine. `yaml` happens to be present on this host, which is
exactly the kind of accident that breaks on the next one.

**Consequence:** the config filename in the plan changes from `.yaml` to `.toml`.
Layering is unchanged: the portable file is committed, the `.local.toml` overlay
is not.

## D21 — Capability directories use identifiers, commands keep hyphens

**Date:** 2026-10-15
**Status:** accepted
**support_level:** fully_supported

The package is `capabilities/on_page/`; the command the user types is
`wo.py on-page`.

**Reason:** D11 named the capability `on-page`, and the first test run failed with
a `SyntaxError` — a hyphen is a valid command name and an invalid Python
identifier, so `wo.capabilities.on-page.audit` cannot appear in an import
statement. The interface keeps the hyphen because that is what a human reads; the
module namespace uses the underscore because that is what Python parses.

**Consequence:** `REGISTRY` maps the command name to the module path, so the two
spellings are related in exactly one place. Renaming a capability touches the
registry entry, the directory, and its README — never the command spelling.

## D22 — The ported capability fixes one defect in the original

**Date:** 2026-10-15
**Status:** accepted
**support_level:** fully_supported
**references:** `hugo-wizard/scripts/audit-site-seo.py`

`audit_html_file()` accepted an `ignore_noindex` parameter that no caller ever
passed, so the flag existed on paper and the `noindex` finding could never be
suppressed. The port wires `--ignore-noindex` through, and a test asserts both
directions.

**Reason:** a finding whose suppression switch does nothing is worse than no
switch, because it teaches the reader that suppression is possible. The parity
test runs with suppression off, which is the original's only observable
behaviour, so parity is unaffected.

**Consequence:** this is the one intentional behaviour change in the port. It is
recorded here because everything else about the port is meant to be
indistinguishable from what it replaces.