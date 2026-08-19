# Performance Evidence Visualization for Release Reviews

Use this pattern when a release note contains latency, throughput, or stability evidence from more than one test context.

## Start with the release question

The visible chapter should normally answer:

> What changed for users and operators from the previous product release to the current product release?

Do not let internal beta chronology (`stock bN`, branch, patch set, later beta) become the presentation structure. Keep exact build provenance in linked RCA pages, evidence notes, or traceability unless the build identity itself is material to the shipped behavior.

## Choose the visual structure

### Pattern A — One investigation-to-release story (preferred for one product outcome)

Use this when several investigations or fixes contributed to the same user-facing improvement.

Show:

1. **Symptom** — the observable degradation.
2. **Measure** — instrumentation at each pipeline boundary.
3. **Isolate** — a one-variable diagnostic that identifies the dominant gap.
4. **Correct** — the production behavior that changed.
5. **Validate** — matched before/after proof followed by a complete-release gate.

A presentation-ready layout is:

- a short timeline,
- a pipeline bottleneck map with `OK` / `DOMINANT GAP` status controls,
- one consolidated before/after evidence block,
- release-gate metric cards,
- a visible rule explaining which values are directly comparable.

Merge related runtime-hardening evidence into the consolidated before/after block when it explains the same release outcome. Do not leave a separate internal issue/fix mini-chapter merely because that evidence was collected in a later beta.

### Pattern B — Two-lane evidence flow (for genuinely separate questions)

Use this when the audience needs to distinguish causal optimization proof from integrated release stability and combining them would imply a false direct comparison.

#### Lane 1 — Matched diagnostic / controlled A/B

Purpose: establish localization or improvement under matched conditions.

Show:

1. fixed replay/input and workload,
2. before run,
3. after run,
4. same instrumentation and measurement boundary,
5. matching percentile/count comparison within the pair.

#### Lane 2 — Full-topology release validation

Purpose: establish that the current release remains stable when the complete service topology runs together.

Show:

1. current release artifact,
2. full service topology and environment,
3. reproduced workload,
4. acceptance gates such as success count, timeout threshold, errors, and pending-task signatures,
5. integrated verdict.

The two evidence questions can remain visually separate inside one product story; they do not have to become separate top-level chapters.

## Label discipline

Prefer visible labels such as:

- `Previous release behavior`
- `Before optimization`
- `SafeART X.Y`
- `Current release`

Avoid visible labels such as `stock X.YbN`, `candidate branch`, or patch-set IDs unless specifically requested.

If an early beta merely carries forward previous-release behavior, describe it that way only when equivalence is confirmed by the product owner or evidence. Otherwise use `Before optimization`; do not relabel a tested beta as the previous GA release without support.

Do not state that one fix caused a later issue unless the release note intentionally includes that causal RCA and authoritative evidence supports it.

## Mandatory interpretation rule

Place a visible note near the metrics:

> Compare values only inside the same matched harness or measurement boundary. Full-topology validation establishes integrated release confidence; its raw latency must not be subtracted from browser-gap, isolated PubSub, or other differently bounded measurements.

A full-topology p95 can be higher than a controlled after-value without representing a regression because topology, background services, state, and workload differ.

## Confluence-native implementation

Use native ADF so the visual remains editable:

- `layoutSection` / `layoutColumn` for timelines, pipeline stages, and metric cards,
- `status` nodes for step labels, bottleneck verdicts, and release gates,
- tables with explicit widths for matched comparisons,
- a warning panel for the evidence rule,
- inline smart links to detailed RCA/evidence pages.

### ADF nesting rule

A Confluence `panel` cannot contain a `table`, another panel, an expand, or a blockquote. A common invalid construction is `panel(header, table, note)`, which can fail persistence with an unhelpful server error.

For a card with a table, use sibling nodes inside one layout column:

1. panel containing the status/header,
2. table,
3. explanatory paragraph or panel.

Validate nesting before PUT, then read back the persisted ADF.

## Evidence integrity checks

- Every environment, load, count, and boundary comes from an authoritative run report.
- Diagnostic queue/prototype behavior is labelled as diagnostic evidence, not as the production patch.
- Metrics are compared only within one matched harness/boundary.
- Projected CPU savings are not presented as measured production CPU.
- Exact build provenance remains available in detailed evidence even when omitted from presentation labels.
- The final release gate is not used as a direct latency comparison against an isolated or browser-level test.
- The visible product story does not contradict the linked RCA pages.
- If the user has manually edited the live page, refresh immediately before mutation and preserve those edits surgically.
