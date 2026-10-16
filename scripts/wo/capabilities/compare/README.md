# `compare` capability

Attributes what changed between two stored runs. **A meta capability**: it reads
runs rather than auditing, so it is always available and is not enabled per site.

## Interface

```
python scripts/wo.py compare [--baseline RUN] [--current RUN] [--dry-run] [--json]
```

Without arguments it compares the latest run against the nearest earlier run that
shares at least one capability. Capabilities do not all run every time, so
skipping incomparable runs matters.

## The rule it is built on

**Never refuse, always attribute.**

The obvious alternative is to skip a comparison whenever the tool version or
crawl mode differs. That fails in practice: the tool version changes on every
skill release, so in an actively developed skill the comparison would refuse
almost exactly when it is wanted. A provenance difference is reported as a
qualifier on the comparison, never used as a filter.

What makes that safe is attribution. Each difference is classified by cause:

| Kind | Condition |
|---|---|
| `regression` | a `critical` finding is new, or a severity got worse |
| `improvement` | a finding is gone and its rule still exists |
| `check-change` | the `rule_id` exists in only one run's rule set |
| `site-change` | same rules on both sides, findings differ |
| `unattributed` | the two runs saw different numbers of pages — no cause can be assigned |

`check-change` is the bucket that does the real work. Without it, adding a rule
to the skill looks identical to breaking the site.

## The enabler

Reports carry `rules_run` — every rule id the capability could emit, fired or
not. Without it, "the page is clean" and "this check did not run" are the same
observation, and `check-change` cannot be detected. A test asserts that
`rules_run` matches what the rules can actually emit, in both directions.

A baseline with no `rules_run` (written before the field existed) falls back to
the severity rule rather than guessing `check-change` — guessing would swallow
every real regression against an older run.

## Scope

`unattributed` exists because knowing the rule set is not enough. Two runs of the
same rules over different numbers of pages cannot tell you anything about the
site: more pages is expected to find more, fewer to find less. Concretely, a
baseline that was a live crawl covering 25 of 173 pages compared against a static
run covering all 173 reported `schema.identifier_conflicting` as a critical
regression — and that rule has to meet the same `@id` on two pages before it can
call anything conflicting.

So the comparison reads `summary.audited_pages`, falling back to
`crawl.fetched` for reports written before that field, and withholds attribution
in **both** directions when the numbers differ. The reason string names both
counts, because "we cannot say" without the numbers is just a different verdict.

Two boundaries, both deliberate:

- **Unknown scope does not withhold.** A report without the counter stays fully
  comparable. Refusing against every older report would trade a narrow
  misattribution for total silence.
- **`unattributed` never becomes a finding.** It does not reach `findings`, does
  not count towards `total_critical_issues`, and cannot fail `--strict`. The
  contract for that field is "claims the tool stands behind", and this is not one.

## Legacy reports

Runs written before the `capability` field or before the `subject` rename are
still usable: the capability is inferred from `source.kind`, and findings fall
back to the former `page` key. Losing a real baseline is worse than tolerating a
field that will never appear again.

## Output

`comparison.json` in its **own** run folder, with a receipt. The compared runs are
never modified — evidence stays append-only, and a comparison that overwrote its
inputs would destroy the history it exists to read.

Regressions additionally appear in `findings`, so `--strict` and exit codes work
across all capabilities without special cases.

## Adding another capability

Nothing to do here. A capability is compared automatically as long as both runs
carry it under the same `capability` name.