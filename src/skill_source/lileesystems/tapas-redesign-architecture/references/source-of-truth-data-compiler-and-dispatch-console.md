# Source-of-Truth Data Compiler and Dispatch Console Contracts

Use this reference when a TAPAS redesign task owns canonical topology/wayside data, generated PLC artifacts, or a future dispatch console.

## Repository product boundary

Treat the repository as a data compiler when it:

- owns human-reviewable canonical topology and wayside asset data;
- validates and resolves that bundle into one immutable model;
- generates cross-component JSON and OpenPLC Structured Text from the same model.

Classify every tracked file as one of:

1. canonical authoring source;
2. tracked release contract;
3. product source/test/schema;
4. migration/review tooling;
5. evidence/reference;
6. disposable generated/local output.

A repository dominated by screenshots, review diagrams, duplicated imported baselines, and external-repository notes is still a discovery package, not a mature source-of-truth product.

## Generated files are not automatically disposable

Before adding `.gitignore` rules, ask how consumers obtain artifacts.

If consumers reference files from a repository tag:

- commit the generated JSON/ST at fixed paths;
- ensure the paths and filenames are stable;
- generate deterministically without timestamps, host paths, or environment leakage;
- make CI regenerate and fail on any diff;
- require canonical/generator changes to include corresponding artifact diffs.

Ignore review images, reports, archives, caches, external checkouts, and temporary build output. Do not blanket-ignore the directory containing tag-addressable contracts.

A proven layout is:

```text
data/canonical/                  # modular authored bundle
artifacts/topology-assets.json   # tracked runtime contract
artifacts/openplc/plcsim.st      # tracked PLC contract
schemas/topology-assets.schema.json
tools/migration/                 # external importers; not runtime package
tools/review/                    # optional generation; outputs ignored
```

## Canonical compilation seam

Prefer modular authoring files (`manifest`, `topology`, `wayside`, `routes`, `interfaces`, `display`, target config) compiled into one immutable `CanonicalModel`.

Generators must accept the resolved model, not read YAML independently or consume one another's output. This prevents JSON, ST, and UI metadata from becoming separate truths.

Keep display pixel coordinates separate from physical topology/GPS. Keep generated PLC address allocation separate from logical asset/I/O identity and authority. Preserve `confirmed`/`provisional`/`incomplete`/`not_applicable`, unresolved question/owner, and provenance through review contracts; executable targets must reject unresolved safety-critical engineering. A reviewed empty list means “none required,” while `incomplete` means unknown.

## Console-ready command/state design

A future dispatch console should not force a PLC-centric redesign of the data contract. Include from the start:

- stable site/entity IDs and renderable display anchors;
- declared asset command capabilities;
- typed command parameters and enum encodings;
- command sequence/correlation fields;
- separate command receipt/lifecycle from an explicit achieved condition;
- named independent field/simulator feedback, health, and freshness predicates for proved completion; command, owner, PLC state, and output read-back cannot prove themselves;
- a one-to-one mapping from each logical JSON field to its generated ST symbol/address binding without authoring target addresses in the logical contract.

Browser actions are command intents. They must not directly overwrite observed signal aspects, proved switch positions, route state, or fault state. Request acceptance is distinct from proved completion.

A useful lifecycle is:

```text
requested -> accepted | rejected
accepted -> executing -> proved | failed | timed_out
```

`proved`, `rejected`, `failed`, and `timed_out` are terminal. A command cannot report `proved` without its declared read-back condition.

For a first Compose environment, keeping the backend PLC adapter in the Dispatch Console container is a simple boundary:

```text
Browser -> Dispatch Console backend adapter -> OpenPLC
```

The browser never connects directly to OpenPLC.

Realtime state and events need different semantics:

- `LATEST`: complete asset/route/PLC snapshots; slow consumers may coalesce intermediate snapshots.
- `ALL`: command lifecycle, rejection, timeout, fault, and operator-audit events; active consumers receive each event in order.

Let one backend layer own the initial snapshot; do not seed the same snapshot independently in the subscription layer.

## External dispatch UI references

Dispatcher simulators can provide valuable interaction scenarios (manual switch command/locking, substitute-signal confirmation, pending versus proved direction indication, command counters). Treat them as UX/state-machine references only. Do not copy foreign railway command names, timer values, or operating rules into TAPAS requirements without separate authoritative approval.

## Scope discipline

A short-term topology/asset JSON + ST compiler can be console-ready without implementing the web frontend, adapter, or Compose runtime in the same change. Record the medium-term boundary in the contract/design, then give the GUI/Compose subsystem its own spec, implementation plan, and review change.
