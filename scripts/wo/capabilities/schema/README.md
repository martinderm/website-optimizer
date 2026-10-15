# `schema` capability

JSON-LD structure and completeness.

## Interface

```
python scripts/wo.py schema [--config FILE] [--strict] [--dry-run] [--json]
```

## What this capability does not do

**It does not validate against the schema.org vocabulary.** It checks structure
and completeness, and points at the authority for the rest.

The reason is durability, not effort. The vocabulary is tens of thousands of
terms with subclass hierarchies; fetching it would make the tool network-
dependent for a check that runs on a build directory, and vendoring it would
create a second copy that ages silently. What the local check proves is what
actually goes wrong in practice.

The report carries the references in its own `references` block:

| Purpose | Where |
|---|---|
| Vocabulary authority | `https://schema.org/docs/full.html` |
| Validate a page | `https://validator.schema.org/` |
| What actually produces a rich result | Google's Rich Results Test |

## Rules

| rule_id | Severity | Fires when |
|---|---|---|
| `schema.none` | warning | page has no JSON-LD block |
| `schema.block_empty` | critical | block present but empty |
| `schema.block_invalid_json` | critical | block does not parse; reports the message and line |
| `schema.block_no_types` | warning | block declares no `@type` |
| `schema.required_field_missing` | critical | a known type is missing a field it cannot work without |
| `schema.context_missing` | warning | no `@context` on the block, so no vocabulary is in force |
| `schema.identity_missing` | warning | site-wide: none of `WebSite`, `Organization`, `Person`, `LocalBusiness` |
| `schema.identifier_conflicting` | critical | one `@id` carries different content on different pages |

`REQUIRED_FIELDS` is a table of what a type cannot function without, not a
completeness rubric. Unknown types are not flagged — the vocabulary's opinion
belongs to schema.org.

## Two things worth knowing

**The same `@id` on every page is correct, not a defect.** A site-wide `@graph`
emits its `Person` and `WebSite` node in every head, and that repetition is what
makes the nodes resolvable. `identifier_conflicting` therefore compares
*payloads*: repeating an identical node 173 times is silent; disagreeing about it
on two pages is a `critical`.

**Unquoted attributes are found.** Minified generator output emits
`<script type=application/ld+json>` without quotes. Requiring quotes made a
fully marked-up site report as having no structured data at all — a confident,
wrong "clean", which is the worst failure shape this capability has.