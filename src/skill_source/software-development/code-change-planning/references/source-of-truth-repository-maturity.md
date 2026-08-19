# Source-of-Truth Repository Maturity Refactors

Use this reference when a user says an existing repository feels like a POC, discovery pack, migration dump, or review artifact rather than the long-lived product it should become—especially when the repository owns canonical data and deterministic code/artifact generation.

## 1. Re-establish the product boundary before proposing folders

Write one sentence each for:

- **Authored truth:** what humans review and maintain.
- **Compiled model:** the single validated in-memory semantic model.
- **Published contracts:** what consumers receive.
- **Generated targets:** code/config produced from the compiled model.
- **Non-product material:** migration importers, source snapshots, review diagrams, screenshots, and investigation reports.

Do not let historical inputs define the product interface. External repos may supply migration evidence, but after migration the canonical repository owns the normalized records.

## 2. Classify every tracked path

Inventory tracked paths by count, bytes, and role. Assign each to one category:

1. **Product core:** canonical data, domain models, loaders, validators, generators, public CLI, stable documentation, tests.
2. **Migration tooling:** importers, compatibility parsers, baseline comparison scripts, one-time fixtures.
3. **Review/evidence:** diagrams, screenshots, discrepancy reports, research notes.
4. **Generated/local:** build outputs, JSON/ST/rendered docs, reports, archives, caches, virtualenvs, distributions.

Typical actions:

- Keep and deepen product-core modules.
- Keep migration/review helpers outside the installed runtime package while they are needed, then remove them after parity/evidence is secured unless a continuing maintenance use is named.
- Keep only durable, concise evidence; add `tests/fixtures/`, migration, or review directories only when the approved change retains real files with an ongoing purpose.
- Remove generated/local artifacts from Git and ignore the complete disposable output directory, not only selected extensions.

Do not turn path classification into a speculative directory taxonomy. Classification explains what a file is; it does not require every category to exist as a folder.

A useful maturity signal is whether product-core code and canonical data dominate the review. If diagrams, screenshots, duplicated snapshots, and generated output dominate the diff or repository size, the repository is still presenting the investigation rather than the product.

## 3. Prefer a small authoring set compiled to one model

“Single source of truth” does **not** require one giant file. It also does not require a manifest, include language, target hierarchy, or nested package layout. For a single current site/target, start with flat files whose names match real responsibilities:

```text
data/
  site.yaml
  topology.yaml
  assets.yaml
  routes.yaml
  interfaces.yaml
  display.yaml
  target.yaml
```

Use fewer files if responsibilities are still small. Add a manifest, profile, or target directory only when a second real site/target creates an actual composition problem.

Compile the authored files through one deep seam:

```python
load_project() -> CanonicalModel
validate(model) -> ValidationReport
render(model, target) -> bytes
```

Rules:

- The resolved model is strict and immutable.
- Global IDs/references are validated after loading all documents.
- Every generator accepts only the resolved model; generators never read YAML independently and never consume another generator's output.
- Non-safety display data remains separate from physical/operational semantics even when the published JSON includes both.
- Start single-site when that is the current requirement; retain a stable `site_id` without inventing a general overlay/patch language.
- Keep source modules flat until a file has a distinct responsibility worth naming and testing separately.

Consider alternatives explicitly:

- **One large authored document:** cheapest initially, but merge-heavy and prone to concern coupling.
- **Small concern-based files → one model:** usually the best current seam.
- **Manifest/profile/target hierarchy:** useful only when multiple real sites/targets already exist; otherwise it is speculative complexity.

## 4. Separate authored version, published contract, and target versions

- Canonical schema version describes the semantic domain.
- Published JSON contract version describes consumer compatibility.
- Generated target version describes renderer/target compatibility.

A formatting-only generator change should not force a canonical-domain major version. Keep deterministic output rules explicit: stable ordering, UTF-8/LF, fixed numeric/address formatting, no timestamps or absolute paths, atomic writes, and hash manifest generation.

## 5. Treat code generation as compilation

For generated PLC/code/config targets:

- Do not make the historical generated file the new authored truth unless byte-for-byte compatibility is an explicit requirement.
- Clarify whether compatibility means text identity, external-interface compatibility, behavior compatibility, or redesign permission.
- Convert target-specific configuration into a typed intermediate representation before rendering when the target has non-trivial control flow, addressing, timers, or repeated programs.
- Unresolved engineering fields must remain explicit; never fill point positions, detection boundaries, conflicts, overlaps, flank protection, or release rules merely to make generation succeed.
- Define the bounded first target honestly. A generator may support only the confirmed simulator profile, but it must fail clearly when a required target input is unresolved.

## 6. Git and repository hygiene

A mature canonical-data repository normally tracks:

- canonical authoring sources;
- source, tests, schema compatibility fixtures, and small golden fixtures;
- architecture, contract, maintenance, and release/versioning docs;
- CI/reproducibility configuration.

It normally ignores:

```gitignore
/build/
/generated/
/dist/
*.zip
```

plus language caches and local environments. Generated JSON/ST may be published as CI/release artifacts. Track generated targets only when consumers explicitly require Git retrieval; if so, use a deliberate release mechanism rather than mixing regenerated binaries and review images into every source-data change.

## 7. Planning and approval sequence

Before editing:

1. Inspect current tracked tree, package modules, generated artifacts, and recent commits.
2. Confirm the product boundary and public output packaging.
3. Confirm compatibility requirements for each generated target.
4. Confirm single-site versus multi-site scope.
5. Ask whether the user prioritizes a minimal current structure or an extension-oriented framework; for this user recommend KISS unless concrete requirements justify otherwise.
6. Present 2–3 architecture options and recommend one.
7. Present design sections for architecture, canonical data model, generation pipeline, error handling, artifact policy, migration, and verification.
8. Get explicit design approval, write the design spec, then create the implementation plan.

If the user requires one Gerrit change for a broad maturity refactor, keep internal milestones and commits reviewable even though the final change is one unit. Call out incomplete engineering as blockers rather than silently narrowing or inventing semantics.

## Pitfalls

- Do not equate “keep useful context” with tracking every screenshot, rendered diagram, and duplicate JSON snapshot.
- Do not retain two published contracts called “canonical” and “legacy.” Legacy data should be migrated, isolated, or clearly compatibility-only.
- Do not put migration importers in the runtime package simply because they were used to bootstrap the data.
- Do not let a large diagram/report module remain the architectural center when the product's stated purpose is data contracts and code generation.
- Do not promise a working target generator based only on counts or identifiers; inspect whether control semantics and target bindings are actually represented.
