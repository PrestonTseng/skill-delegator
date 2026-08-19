# Pipeline Diagnosis vs Validation — Worked Pattern

Use this reference when a release-review section visualizes a timestamped delivery pipeline and the user wants both root-cause localization and improvement evidence.

## The two-layer rule

Keep the investigation and the improvement as different visual layers:

### A. `How We Located the Bottleneck`

This layer represents the problem state at discovery.

- **Delivery/drop row:** baseline item counts only.
- **Latency row:** baseline percentile only, using the same percentile on every card when possible.
- **Root-cause statement:** infer the dominant boundary from baseline evidence only.
- Do not include After values, improvement percentages, fixed-state statuses, or release acceptance claims.

A clear five-stage delivery row is:

1. input published,
2. handler received/published,
3. suspected boundary delivered,
4. downstream received the already reduced stream,
5. client observed the reduced stream.

A clear four-stage latency row is:

1. input/broker → handler receive,
2. handler receive → internal publish complete,
3. internal publish complete → server delivery boundary,
4. client receive → render observation.

### B. `Before / After Validation`

This layer owns all improvement claims:

- matched Before → After values,
- one-variable diagnostic proof,
- stall/event counts,
- release acceptance outcome,
- separate microbenchmark or controlled-test results with explicit harness labels.

## Metric identity key

Before publishing, assign every repeated metric this identity:

```text
boundary | start timestamp | end timestamp | percentile | harness | population | rounding
```

Example:

```text
PubSub complete → GraphQL before-yield
unicorn_pubsub_done_ns → graphql_before_yield_ns
p99
/m1, 2x replay, limit 6000, remote AMD64 Compose
Before n=2732; After n=3538
one decimal in presentation
```

A card and a table may repeat this metric only if every identity component matches. Prefer the exact instrumented boundary (`GraphQL before-yield`) over a looser product phrase (`GraphQL send`) when the latter could imply socket flush completion.

## Human-readable card construction

Each card should contain:

1. one native status label,
2. one boundary/title,
3. one metric or count in bold,
4. one short interpretation sentence.

Use equal-width columns within a row. Status colors should explain the baseline finding, not imply that every stage improved:

- green: stage was not the bottleneck,
- red: loss or dominant controllable gap,
- yellow: upstream limitation or ambiguous contribution,
- neutral/purple/blue: downstream observation or context.

## Population caveat

A fix may retain more slow samples than the baseline path. In that case:

- show `n` for Before and After,
- do not color a flat/worse upstream tail as an improvement,
- explain that the population changed,
- preserve the localization conclusion only for matched boundaries where the evidence supports it.

Render metrics are often sampled subsets. Show the render sample counts separately from backend-stage counts.

## Confluence ADF pattern

For visual cards:

```text
layoutSection
  layoutColumn (equal width)
    panel
      paragraph(status)
      paragraph(strong title)
      paragraph(strong metric)
      paragraph(interpretation)
```

For a panel-like table, do not nest the table inside a panel. Use sibling nodes in one `layoutColumn`:

```text
layoutColumn
  panel (header only)
  table
  paragraph (methodology/caveat)
```

## Verification

After candidate generation and persisted read-back:

- assert the diagnostic subsection contains the expected number of baseline labels,
- assert it contains zero After arrows/fixed-state labels when baseline-only is required,
- assert the validation subsection retains every intended improvement pair,
- count each repeated Before and After value; card/table duplicates should appear the expected number of times,
- compare media and block-card order with the live baseline,
- run the ADF guard on the governed scope when unrelated inherited global violations exist.

## Concrete reconciliation lesson

In the SafeART 0.21 release review, a pipeline card originally showed only baseline p99 while the lower table showed Before/After, and separate harness numbers were labeled too generically. The correction was:

- keep `How We Located the Bottleneck` baseline-only,
- show the four improvement pairs only under `Before / After Validation`,
- repeat identical boundary names and rounding in the lower table,
- rename unrelated rows to `PubSub microbenchmark wall p95` and `Controlled JPS p95`,
- explicitly note that upstream MQTT tail did not improve and that render observations were sampled.
