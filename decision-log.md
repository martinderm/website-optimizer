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
order executable, so the sequence lives in code instead of in folder numbering.
Capabilities share one envelope, one report base schema, and one config loader
without copy-paste.

*(Amended by D23: there is no `wo.py run-all`. Capability subparsers are generated
from `REGISTRY` and each capability is invoked on its own. The reasoning holds;
the command did not survive implementation.)*

**Deviation:** `authoring-guide.md` prescribes flat `scripts/<tool>.py`. The
guide permits documented justification for deviations; this entry is that
justification.

**Consequence:** There is exactly one entry point. Capability modules are not
directly executable, which prevents two entry points from drifting apart.

## D3 — Report shape is a schema file, not prose

**Date:** 2026-10-15
**Status:** accepted

The audit report conforms to `scripts/schemas/audit-report.schema.json`. The
*(Amended by D23: that file was split into `report-base.schema.json` plus one
schema per capability, because the first capability had shaped the schema around
itself.)*
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

## D23 — Reports share a base schema; each capability owns its own

**Date:** 2026-10-15
**Status:** accepted
**support_level:** fully_supported

`report-base.schema.json` carries what every report needs. Each capability has its
own schema that pulls it in via `allOf`. The finding key is `subject`, not `page`,
because a redirect finding has a source URL, not a page.

**Reason:** the first capability shaped the schema around itself — one `summary`
object with `audited_pages` and one `pages` array. The second capability has
`passed`/`failed` and one `checks` array. Carrying both in one schema would have
meant optional fields nobody required, or a generic `summary: object` that
validates nothing. The trigger was concrete: the second capability failed at
runtime with `KeyError: 'audited_pages'`, in a message that had hard-coded the
first capability's vocabulary.

**Consequence:** adding a capability means adding a schema file and one registry
entry. The registry — not the CLI parser — declares what a capability is; the
subparsers are generated from it, so a new capability cannot be half-wired.

## D24 — Nothing is written before every fallible step has run

**Date:** 2026-10-15
**Status:** accepted
**support_level:** fully_supported
**references:** `scripts/wo.py` (`_run_capability`)

The report is composed, validated and summarised before `write_run` is called.

**Reason:** an evidence run is an append-only observation. An artifact written by
a process that then crashes records the tool's failure, not the site's state —
and it sits in the history a future `compare` will read as if it were real. Two
such orphan runs were produced during development and removed rather than kept.

**Consequence:** a run folder exists only if the run completed. Failure leaves no
trace in the evidence zone; the failure is visible in the envelope instead.

## D25 — `compare` never refuses; it attributes every difference

**Date:** 2026-10-15
**Status:** accepted
**support_level:** fully_supported

A comparison always runs. Every difference is classified as `regression`,
`improvement`, `check-change`, or `site-change`. A provenance difference (tool
version or crawl mode) is reported as a qualifier on the comparison, never used
as a filter.

**Reason.** The strict alternative — refuse to compare when `source_version`
differs — was considered and rejected on its own merits: the tool version changes
on every release, so the comparison would refuse exactly when it is wanted, and
silence is the worse failure. Attribution is what makes tolerance safe:
without knowing which rules ran, "a rule was added" and "the site broke" are the
same observation.

**Consequence.** Reports carry `rules_run` — every rule id a capability can emit,
fired or not — because `check-change` cannot be detected without it. A test
enforces that the declared set matches the rules in both directions. A baseline
without `rules_run` falls back to severity rather than guessing `check-change`,
since guessing would swallow every regression against an older run. `compare` is
a meta capability: it is not enabled per site, because enabling it changes what
the tool can do, not what the site looks like.

## D26 — Live page rendering is an on-request diagnostic, not a check

**Date:** 2026-10-15
**Status:** accepted
**support_level:** partially_supported
**references:**
  - `../playwright-cli/SKILL.md` (session handling, `--raw`, page-content rule)
  - [performance.md](../../../references/performance.md) (LCP, Core Web Vitals)

Not yet implemented. When it is, it runs only when asked for — never from a hook,
never in CI.

**Reason.** Four independent reasons converge, and the last one is decisive:
(a) a browser crawl costs minutes where a static audit costs seconds; (b) browser
sessions are a shared resource and two harnesses in one workspace collide — the
`playwright-cli` skill says so explicitly; (c) results depend on viewport,
consent state and cookie banners, so a hook would fail intermittently, and an
intermittently failing hook gets disabled, which is worse than no hook;
(d) a crawl of a site behind a consent wall finds the wall on every page and
reports it as the page's content — consistently wrong in a way that looks real.

**Consequence.** `on-page` against build output and `redirects` are the hook-
grade checks: fast, deterministic, and a failed run means something. The live
crawl answers a question a person asked. Its report is marked `crawl_mode: live`,
which `compare` reports rather than filters.

**Support caveat:** partially supported until the capability exists and its
runtime is measured on a real site.

## D27 — Crawl artifacts are written beside the run, not into it

**Date:** 2026-10-15
**Status:** accepted
**support_level:** fully_supported
**references:**
  - `agent-architecture/standards/workspace/workspace-memory-tiers-standard.md`

When live rendering lands, the raw crawl output is written outside the evidence
zone, next to the run rather than inside it. `memory/evidence/` holds one report
and one receipt per run; bulk, regenerable crawl data is not knowledge and does
not belong in an append-only history that humans read.

**Reason:** mixing the two would put hundreds of megabytes of regenerable HTML
into the folder a reviewer is meant to open, and every retention decision for
evidence would then apply to data that can simply be crawled again.

**Consequence:** the evidence zone stays small enough to read; a run folder keeps
being `report.json` + `receipt.json` only.

## D28 — `schema` checks structure, not the schema.org vocabulary

**Date:** 2026-10-15
**Status:** accepted
**support_level:** fully_supported
**references:** `https://schema.org/docs/full.html`

`schema` validates JSON-LD structure and completeness locally — parses, `@type`
present, required fields present, `@context` declared, `@id` consistent — and
hands vocabulary validation to schema.org's validator and Google's Rich Results
Test. The report carries those references in its own `references` block.

**Reason:** the vocabulary is tens of thousands of terms with subclass
hierarchies. Fetching it would make a build-directory check network-dependent;
vendoring it would create a second copy that ages silently. The approved scope
was structure plus a pointer to the authority.

**Consequence:** unknown types are not flagged. `REQUIRED_FIELDS` holds only
what a type cannot work without, not a completeness rubric — the vocabulary's
opinion belongs to schema.org.
---

## D29 - The local config layer applies whenever the base file is named

**Status:** accepted
**Support level:** observed

**Decision:** `--config site.optimizer.toml` loads `site.optimizer.local.toml`
from the same directory if it exists. The explicit path names the base file, not
a request to work without the overlay.

**Reason:** the overlay was only merged in the auto-discovery branch. The
documented call - which is what `AGENTS.md`, `PLAN.md` and `SKILL.md` all tell
the reader to type - therefore dropped every machine-specific path and failed
with `Static output directory not found: .../hugo-wizard/public`. The message
named a directory that the configuration appeared to define and did not. A
reader debugging this would have moved a directory that was already correct.

**Consequence:** naming the local file explicitly is still safe; the merge is
skipped when the two paths resolve to the same file. An overlay with no `[site]
url` is rejected on its own, because it carries overrides and not an identity -
that behaviour was already correct and is now pinned by a test.

**Found by:** re-verifying the image capability against a real site. The four
parity checks from round 2 all passed, and none of them touched the config
layering, because they called the capability module directly.

---

## D30 - Coverage limits are documented next to the rule, not only in the plan

**Status:** accepted
**Support level:** observed

**Decision:** a rule whose scope is narrower than its name suggests carries the
limit in the capability README, with the measured size of what it misses.

**Reason:** `image.loading_unset` fires only when no image on a page declares a
strategy. That is defensible - a fold heuristic belongs to `performance.md` -
but it is invisible in the output. A count of 19 on a site with 142 images
without a `loading` attribute reads as clean, and 121 pages are mixed-declared
and reported not at all.

**Consequence:** a `loading_unset` count of zero means *"no page declares no
strategy"*, never *"every image declares one"*. Reading a finding count as a
statement about the site rather than about the rule is the failure mode this
entry exists to prevent.

---

## D31 - An element that fetches nothing is not a delivery finding

**Status:** accepted
**Support level:** observed

**Decision:** an `<img>` whose `src` is empty or absent is reported once, by
`image.src_missing`, and is excluded from `image.dimensions_missing` and
`image.srcset_missing`. `page.py` keeps the presence of the key separately from
its value, so a bare `src` attribute can be told from a missing one.

**Reason:** nothing is downloaded for such an element, so it reserves no space
and shifts nothing. Counting it as a missing dimension says the site will have a
layout shift where it will not. On the reference site this was 140 of 469
critical findings - thirty percent of the headline number - all instances of one
Hugo lightbox template. The same element was also reported as a missing `srcset`,
so one `<img>` produced three findings and the most alarming of them was false.

**Why the two cases are one rule:** both are fixed the same way, by a template
that emits a real URL. Splitting them would double the count without adding a
decision. They are separated in the message instead, because the bare attribute
is the more serious one: `<img src alt>` parses as `src=""`, which resolves
against the document, so the browser issues a real request for the page itself
as an image.

**Consequence:** the critical count for that site is 329, not 469. Both numbers
were correct for the rules as written; only one describes the site.

---

## D32 - A crawl is checked against what it saw, before its findings are read

**Status:** accepted
**Support level:** observed

**Decision:** every live report carries a `crawl` block — requested, fetched,
failed, limit, artifacts, retention class — and the envelope repeats it. The
first time a live run reported `0 findings`, that number was meaningless: it
could have meant 400 clean pages or 3 pages and a timeout. The reach of a run is
part of its result.

**Reason:** the finding count answers "what is wrong", never "how much did you
look at". A run that fetched three pages of four hundred and reported nothing
is indistinguishable, in the output, from a clean site. That is the failure this
prevents, and it is the same one `rules_run` prevents from the other side.

**Consequence:** `compare` can attribute a difference between a static and a live
run, because it knows both were looking at something. D25 made provenance a
qualifier rather than a filter; this is what makes the qualifier available.

---

## D33 - The live path is the same code path

**Status:** accepted
**Support level:** observed

**Decision:** capabilities have no `--live` branch. `wo.pages.resolve()` returns
`Page` objects from either source and the rules above it cannot tell them apart.
JSON-LD is the one exception and it is explicit: `PageSet.raw` carries rendered
markup for capabilities that need the document rather than the fields.

**Reason:** a duplicated code path is a place for the two versions to disagree,
and the disagreement would be invisible until a site produced different findings
for the same defect depending on how it was audited. Verified against 25 real
pages: static and live agree exactly, on all three capabilities.

**Consequence:** `extract_page_from_html` is the only new extraction entry point,
and a rule that would only work on files cannot be written without deliberately
reaching past the interface.

---

## D34 - A crawl that sees one page repeatedly reports nothing

**Status:** accepted
**Support level:** partially_supported

**Decision:** if most rendered pages are byte-identical, the audit raises and
produces no findings. Two pages are never enough evidence to refuse; a majority
repetition is.

**Reason:** D26 named this failure — a consent wall is found on every page and
reported as that page's content, consistently wrong in a way that looks real.
Making it mechanical matters more than documenting it, because the wrong report
is more convincing than the caveat.

**Why identical markup and not "a dialog is present":** the honest signature is
that distinct URLs cannot return the same document. Consent markers
(`consent`, `onetrust`, `cookieyes`, ...) sharpen the message but never decide
it — plenty of real pages carry those words, and a JavaScript shell behind the
same behaviour produces the same unusable result with no marker at all.

**Not yet supported:** the guard does not know *why* pages repeat. A site that
redirects every URL to one page is not behind a consent wall and will still be
refused. The message says so rather than naming a cause it cannot establish.

---

## D35 - Rendered HTML is decoded as UTF-8, not as the terminal speaks

**Status:** accepted
**Support level:** observed

**Decision:** the crawl reads subprocess output as bytes and decodes UTF-8 with
`errors="replace"`.

**Reason:** `text=True` decodes with the machine's locale code page. On a German
Windows install that is cp1252, and the first rendered page containing a
character outside it raised `UnicodeDecodeError` inside a reader thread and took
the process down with a traceback. A tool whose input is arbitrary web pages
cannot inherit the terminal's encoding — the page is not written in the
operator's language.

**Found by:** the first real crawl of a real site. No test could have caught it,
because a fixture containing only ASCII decodes under any code page.

---

## D36 - The browser CLI is invoked without a shell where possible

**Status:** accepted
**Support level:** observed

**Decision:** the npm `.CMD` shim is parsed for its node entry point and that JS
file is executed with `node` directly. `cmd.exe` is the last resort, not the
first.

**Reason:** `subprocess` cannot execute a `.CMD` without a shell, and a shell is
actively wrong for URLs — `playwright-cli`'s own documentation calls out that a
URL containing `&` gets split by `cmd.exe` before the browser sees it. Going
through node removes an entire quoting layer rather than escaping it.

**Consequence:** `[crawl] cli_path` exists as an escape hatch for an
installation this resolution cannot see, rather than as the normal path.

---

## D37 - A sitemap is not always a list of pages

**Status:** accepted
**Support level:** observed

**Decision:** a sitemap whose root element is `<sitemapindex>` is followed to its
children, up to two levels, before any page is rendered. Discovery tries
`robots.txt` before the well-known filenames.

**Reason:** WordPress Core (`/wp-sitemap.xml`) and Yoast (`/sitemap_index.xml`)
both emit an index. The original reader took every `<loc>` as a page, so on a
WordPress site it would have visited the XML files as though they were pages and
reported on documents that are not documents. A wrong result produced
confidently is worse than no result: the tool's whole claim is that its findings
are about the site.

**Why `robots.txt` comes before the guesses:** it is the site naming its own
file, in the one document whose purpose is to say what should be crawled. That
outranks a filename inferred from convention. The well-known paths follow
because the convention is common enough to be worth trying and a miss costs one
404 - cheaper than asking someone to look it up.

**Consequence:** a WordPress workspace needs no sitemap configuration at all. It
also means the tool reaches WordPress without knowing anything about WordPress,
which is the better dependency: no plugin-specific code that ages.

**Still open, and named:** `redirects` has no source on a WordPress site. It
reads a rule file; WordPress on nginx has no `.htaccess`, and its redirects live
in the database or a plugin. Enabling that capability there today would report
"no rules found" about a site that has redirects. It must either gain a source
or be explicitly switched off per site, and the second is what the config
already supports.

---

## D38 - A host disagreement is reported at the severity of what it is

**Status:** accepted
**Support level:** observed

**Decision:** a canonical naming a different **host** than `[site] url` is
`canonical.host_differs` at warning severity and names the fix. `canonical.mismatch`
stays critical, for a canonical falling outside a path-prefixed base.

**Reason:** found by pointing the live crawl at a real WordPress site. Twelve of
twelve pages reported a critical canonical mismatch; every canonical was correct.
The site canonicalises to `www`, the configuration named the apex host - the
commonest WordPress misconfiguration there is. One wrong line of configuration
became a dozen identical criticals, and a reader who sees a dozen identical
criticals learns to ignore the rule. The one thing actually wrong disappeared
inside them.

**Why two rules rather than one with a softer severity:** the two disagree in
kind. One is a configuration value the operator can fix once; the other is a page
whose canonical points somewhere else and is a defect in that page. Collapsing
them into one rule at one severity would misdescribe half of them.

**Nothing is suppressed.** The host disagreement is still reported on every page,
because a page whose canonical disagrees with the configured host is worth seeing.
It is simply no longer dressed up as a broken page.

**Also found, and older:** `canonical.mismatch` is unreachable when `[site] url`
is a bare host, since every canonical on that host starts with it. It only fires
for a base carrying a path prefix. That was true before this change, so the rule
was silently dead for most single-host installs. The tests now cover the one
shape that reaches it.

---

## D39 - No CI; a parity check runs at launch or when someone asks

**Status:** accepted, provisional
**Date:** 2026-10-16
**Support level:** inherited

**Decision:** no continuous integration. Every capability is run manually - at a
site launch, or on demand when something looks wrong.

**Reason:** the value of a parity check here is catching a port that drifts from
the thing it replaced, and both originals are now deleted, so there is nothing
left to diff against. What remains worth automating - the 142 tests - runs in
under three seconds and needs no network, no browser and no fixtures beyond what
is in the repository.

**Consequence, stated plainly:** a regression in a rule now reaches a site audit
before anyone notices. The tests make that unlikely; they do not make it
impossible to be late. If the skill is bound in more workspaces than two, this
decision should be revisited, because "someone remembers to run it" degrades with
the number of places it has to be remembered.

**What would change the decision:** a third workspace binding, or a rule change
that is hard to review by eye. Nothing has hit that yet.

---

## D40 - A question the audit cannot answer is raised, not dropped

**Status:** accepted
**Date:** 2026-10-16
**Support level:** observed

**Decision:** `image.loading_partial` is a warning that fires once per page when
some images declare a `loading` strategy and some do not. It states how many, and
says what would close the question. It does not assert that those images are
wrong. The measurement that would settle it - each image's position against the
viewport - exists but is not run automatically.

**Reason:** silence read as clean. On the reference site 121 pages, and on a real
WordPress site 26 of 29, carried images with no strategy and reported nothing -
including one page with 42 OpenStreetMap tiles, every one of which the browser
fetches immediately regardless of whether it is in the viewport.

The earlier reasoning - that a static audit cannot tell an above-the-fold image
from a lazy-load candidate, so widening the rule would report images it cannot
justify - was right about the *verdict* and wrong about the silence. A finding
that says "this is open, and here is what would close it" is not a verdict, and it
does not need to be justified as one.

**Why the measurement is not automatic:** a crawl per page is the most expensive
thing this tool does, and it would be spent answering a question that on most
sites is cheap to ignore. The rule is the prompt; taking the measurement is a
decision.

**Measured effect, same site, same code path otherwise:** 1209 findings became
1330. The 121 added are exactly the pages that were silent. Critical count
unchanged at 329.

---

## D41 - A browser profile is per site, configured, and off by default

**Status:** accepted
**Date:** 2026-10-16
**Support level:** inherited

**Decision:** `[crawl] profile` names a directory. When set, the crawl opens the
browser with `--profile=<dir>`; when absent, the in-memory default stands. A
relative path resolves against the workspace root, so "one profile per agent
workspace" and "one profile per machine" are both expressible and neither is
imposed.

**Reason:** it is the only way past a consent wall that a crawl can meet.
Accepting once in a headed session and reusing that profile is exactly the
`playwright-cli` feature for it. Consent plugins are the normal case on
WordPress, so the wall guard of D34 will refuse frequently there, and without
this the only available answer is not to crawl.

**Why off by default:** nothing about it is needed until it is, and a tool that
creates browser profiles nobody asked for is a tool that leaves directories
containing session cookies behind.

**The path is a secret and the tool treats it as one.** `playwright-cli`'s own
documentation says a persistent profile directory is secret, because a profile
used to log in carries the session cookie. The tool creates the directory and
never reads, writes, or reports its contents; the config names it by path only.
Any workspace using this must keep the path out of git - the profile directory
itself is the sensitive artifact, not the line pointing at it.

---

## D42 - Advisory guidance belongs in references, marked as advisory

**Status:** accepted
**Date:** 2026-10-16
**Support level:** observed

**Decision:** the trade-offs of the available redirect sources are documented in
`references/redirects.md` under a heading that says it is advisory, not a rule.
The recommendation is that a URL list checked against the live server beats every
form of reading the stored rules. The decision remains the site's.

**Reason:** the skill's job is to measure *and advise* - that is its own
definition - so advice is in scope. What is not in scope is the decision, because
a recommendation written into a shared skill becomes a default in disguise: the
next workspace inherits it without the context that produced it, and the site
whose nginx config is right gets talked out of reading it.

**Where it lives, and why not elsewhere.** Not the decision log: that records
what was decided here, and no decision was made. Not `SKILL.md`: that is a router
carrying no content. In the topic reference, next to the rule it qualifies - the
checklist already demands redirects be verified by fetching them, and this is what
that means when fetching them is the only option left.

**Marked, not claimed.** The section says in its first line that it is advisory.
An unmarked opinion in a file whose front matter says `evidence_level: normative`
would be read with the authority of the rule above it, which is the same failure
in miniature as writing the decision at all.

---

## D43 - The version moves when the rules move

**Status:** accepted
**Date:** 2026-10-16
**Support level:** observed

**Decision:** `TOOL_VERSION` is bumped whenever a rule is added, removed, split
or re-severitied — that is, whenever `rules_run` would differ between two runs of
the same site. Not for anything else.

**Reason:** `0.2.0` covered at least three mutually incompatible rule sets. The
seventeen runs stored across the two workspaces all read
`source_version: website-optimizer 0.2.0`, while their `rules_run` arrays show
eight distinct rule sets underneath. A receipt is supposed to say what produced
the artifact beside it; this one said something that was true of none of them
individually.

**What was not the problem, and matters to say.** `rules_run` worked. Across the
sixteen runs that carry it there are eight distinct signatures, which is exactly
what makes them distinguishable — including the live runs, whose `images` sets
hold eight rules against the static nine because `icon.file_missing` correctly
drops out where there is no build directory. D25's mechanism held; only the
coarse label above it had gone stale.

**The old receipts stay untouched.** Evidence is append-only (D24, D8), and a
receipt is a record of what a run claimed at the time. Rewriting seventeen
receipts to carry a version none of them ran under would be worse than the defect
it fixed. `0.2.0` now names a real historical state, and `rules_run` describes
what inside it varied.

**How this would have been caught.** A check that the version string differs
whenever `CHECKS` does — the same shape as the existing round-trip test between
`CHECKS` and the rules a capability can actually emit. Not built; noted so the
next person does not rediscover it.

---

## D44 - A difference between runs of different size belongs to neither side

**Status:** accepted
**Date:** 2026-10-16
**Support level:** observed

**Decision:** when the two runs of a capability observed different numbers of
pages, every finding-level difference is labelled `unattributed` and carries a
reason naming both counts. `unattributed` is not a cause and never becomes a
finding, so `--strict` cannot fail on something the tool cannot explain.

**Reason:** found by running `compare` for the first time against real stored
runs. A baseline that was a live crawl covering 25 of 173 pages, compared with a
static run covering all 173, reported `schema.identifier_conflicting` as a
critical **regression**. The rule sets were identical and the site had not moved.
That rule has to meet the same `@id` on two pages before it can call them
conflicting, and a quarter of the site cannot produce that.

`compare` read `rules_run`, tool version and crawl mode. It never read
`audited_pages`. So the depth of observation was invisible to it, and a change in
coverage was reported as a change in the site - which is the one claim a reader
will act on.

**Both directions are confounded, not only the alarming one.** Fewer pages is
expected to find less, so a vanished finding is no more evidence of a fixed site
than a new one is of a broken one. Withholding only regressions would have left
the mirror-image error in place.

**Why not a fifth *cause*:** naming a category `scope-change` asserts that the
scope is the reason. Sometimes it is, and sometimes two things moved at once.
`unattributed` asserts only what is true in every case - that no cause can be
assigned - and hands the reader the two numbers to decide with.

**What is still attributed, and why.** The rule-set difference is not withheld.
With unequal scope we still know the tool changed, and losing that would trade a
misattribution for a less informed report.

**Unknown scope does not withhold.** A report without the counter stays
comparable, because refusing against every older report would trade a narrow
misattribution for total silence - the exact trade D25 exists to prevent.
