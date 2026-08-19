# Human-Reviewed Wayside YAML: Item-1 Workflow

Use this reference when TAPAS topology and wayside assets must become a human-reviewed YAML single source of truth before JSON, PLC/ST, or dispatch-console implementation.

## 1. Freeze the patch boundary

Write the active item at the top of the plan and Gerrit description:

- **Item 1 only:** YAML schemas, known TAPAS entity data, inline review TODOs, and a short review README.
- Explicitly excluded: JSON generators/outputs, Python runtime models, Pydantic loaders, ST/OpenPLC code or mappings, FastAPI, Angular, Compose, and runtime simulation.
- One item is one Gerrit patch/review cycle. Wait for approval before starting the next item.

A user request to reset or forget the previous process supersedes prior architecture assumptions. Treat previous artifacts only as reference evidence.

## 2. Author for Gerrit review

Recommended Item-1 tree:

```text
README.md
data/
  site.yaml
  vertices.yaml
  blocks.yaml
  sub_blocks.yaml
  signals.yaml
  switches.yaml
  detection_sections.yaml
  abs_directions.yaml
  routes.yaml
schemas/
  common.schema.yaml
  site.schema.yaml
  enums.schema.yaml  # canonical domain names + numeric interface codes; asset schemas $ref it
  vertices.schema.yaml
  blocks.schema.yaml
  sub_blocks.schema.yaml
  signals.schema.yaml
  switches.schema.yaml
  detection_sections.schema.yaml
  abs_directions.schema.yaml
  routes.schema.yaml
```

Use JSON Schema Draft 2020-12 written as YAML, or another explicitly approved YAML schema language. Every entity schema should:

- reject unknown fields;
- require every behavior field;
- allow `null` only where engineering input may be unresolved;
- include field descriptions for human reviewers;
- use stable IDs and explicit units in field names where practical;
- keep cross-entity references as IDs, not embedded duplicate objects.

Add a YAML language-server schema hint to each data file when supported by the editor.

## 3. Normalize the SSOT

Define an entity or relationship once:

- `sub_block.block_id` owns block membership; do not also maintain a hand-edited block member list.
- `detection_section.covered_sub_block_ids` owns occupancy coverage. Derive block occupancy through the covered sub-blocks' `block_id`; do not repeat detector lists or occupancy state on each block.
- A signal references its governed sub-block and anchor vertex by ID.
- A route uses operational blocks for path, overlap, and release, plus switch/detection/signal/ABS resources by ID. Do not maintain an ordered sub-block path alongside the ordered block path; sub-blocks are physical topology, not a second route truth.
- Domain names/codes live once in a canonical referencable schema such as `schemas/enums.schema.yaml`. Put reviewed numeric interface codes in schema metadata (for example `x-codes`) and make every domain-valued asset field `$ref` the canonical definition. This lets ordinary schema validation reject arbitrary strings without duplicating enum members between a data file and entity schemas.
- Shared operational behavior lives once. Put a no-entry-expiry profile under site metadata and let each route reference its profile ID; do not repeat the same timeout/action object on every route. A fail-safe expiry profile should explicitly encode entry-occupancy cancellation, restrictive command and independent proof, clear/healthy approach proof, lock retention, final release scope, and released-switch physical-position behavior.
- Display coordinates may live on the vertex for the approved console projection, but they must not be confused with surveyed/GPS geometry.
- Later JSON/ST generators may denormalize; generated projections never become authoring inputs.

Use one data file per entity kind so a reviewer can compare every instance against one schema.

## 4. Fields needed for wayside simulation

At minimum, model these behavior classes directly in the type schemas:

- **Vertex:** stable ID, name, chainage/milepost, platform/yard flags, review display coordinates.
- **Block:** stable ID/name/aliases only; occupancy is derived from detection coverage through sub-block ownership.
- **Sub-block:** stable ID/name, owning block, endpoint vertices, speed limit.
- **Signal:** location, track-line enum, movement-direction enum, approach block, governed sub-block, anchor vertex, restrictive/proceed aspects, startup aspect/health, proving timeout, feedback freshness timeout.
- **Switch/point:** anchor vertex, normal/reverse topology, startup position/health, movement proving timeout, feedback freshness timeout.
- **Detection section:** covered sub-blocks, startup occupancy/health, clear-hold/debounce, freshness timeout.
- **ABS direction:** member blocks, allowed directions, startup direction/health.
- **Route:** entrance/destination signal, ordered operational blocks, required switch positions, clear/entry/approach detections, additional non-duplicative proof conditions, overlap blocks, flank protection, conflicts, ABS direction, proceed aspect, startup state, locking timeout, shared no-entry-expiry profile reference, sectional block/switch release, and final release. Final release must identify or unambiguously derive every remaining owned signal/block/switch/ABS resource plus its restrictive/clear proof conditions.
- **Enums/site metadata:** canonical domain names/codes, units, provenance, and shared behavior profiles. An entirely unresolved enum should be null-only with inline TODOs; do not guess conventional names merely to satisfy the schema.

This is a field checklist, not permission to fabricate site values.

## 5. Unknown values: direct and visible

Prefer the human-readable form:

```yaml
governed_sub_block_id: null  # TODO(Preston): choose C3T_1 or C3T_2 for signal 14R.
```

Rules:

- Known values are direct scalars/lists.
- Unknown values are direct `null` plus a specific inline TODO naming the entity and decision needed.
- A plausible-looking scalar with an inline “TODO: confirm” is **not** a known value. Replace it with `null # TODO` until the authoritative source confirms it; otherwise a provisional legacy default can silently become claimed as-built data.
- `[]` means an authorized reviewer confirmed the set is empty. Never use it as “unknown.”
- Do not wrap each field in `state/value/source_refs/unresolved_question/responsible_party` unless the user explicitly asks for that review model.
- Keep source provenance compact and file-level; do not bury the asset data under repeated metadata.
- If an entity inventory itself is unknown, make the top-level collection `null # TODO(Preston): provide the complete confirmed inventory` and let the schema accept either a non-empty reviewed array or `null`. Do not create placeholder IDs, and do not use `[]`: that means a reviewer confirmed there are no entities.
- Apply the same rule to a wholly unresolved enum: its canonical schema definition should be null-only and its code map `null # TODO`, not a guessed set of conventional member names.

## 6. Source handling

Use the most direct authoritative sources available, but keep historical material in its proper role:

- Existing TAPAS/Thalos constants can establish known IDs and values when pinned to a real revision.
- Testbed fixtures and prior YAML can supply migration reference data.
- Decks/screenshots can identify review questions and simulation behaviors, but do not prove as-built switch, detection, overlap, flank, or release relationships.
- Graph degree does not prove a physical switch/point machine.
- Preserve compact file-level source locators; do not copy entire provenance graphs into each entity. Verify every retained path/locator resolves to an actual source. Use a pinned repository commit where possible and an immutable SHA-256 for standalone artifacts when no repository revision exists.

## 7. Clean-repository reset

When the user explicitly asks to “leave only YAML-related information,” the Item-1 patch should contain only the YAML schemas/data plus minimal review support such as README and `.gitignore`.

Remove from that patch:

- Python/Pydantic model and loader code;
- unit tests and package metadata for deleted code;
- generated JSON, PNG/SVG, ST, PLC bindings, and build artifacts;
- OpenPLC runtime configuration;
- stale implementation plans/specs that describe later items;
- duplicate legacy-baseline data that could be mistaken for a second truth.

Do not preserve compatibility code for consumers that belong to a later item unless the user explicitly asks for it.

## 8. Item-1 verification

Use disposable/off-repo tooling so verification does not reintroduce code into a YAML-only patch:

1. Parse every YAML file with duplicate keys rejected.
2. Validate every schema against its metaschema and recursively require a meaningful description on every nested property. Presence-only checks are insufficient: generated generic text can describe the wrong field.
3. Validate every data document against its matching schema. Add negative mutation tests for representative domain fields (signal aspect, route state, ABS direction, occupancy, switch position): deliberately misspelled values must fail normal schema validation. If they pass, enum membership is still prose rather than enforced SSOT.
4. Verify unique IDs, aliases, expected inventory counts, enum name/code uniqueness, and every non-null domain value's membership in the single enum SSOT.
5. Verify all non-null cross-references:
   - sub-block → block/vertices;
   - signal → block/sub-block/vertex and, when governed sub-block is known, that approach block and governed sub-block touch the anchor boundary;
   - switch/detection → topology;
   - ABS → blocks;
   - route → signals/blocks/switches/detections/ABS/routes, shared behavior profile, overlap, and release resources.
   Report confirmed and unresolved counts separately. A validator that skips null references proves only that known references are coherent; it does not prove every relationship is confirmed.
6. Verify every actual `null` value across both human-reviewed data and canonical enum/code metadata has an inline TODO, while reviewed empty lists remain distinguishable from unresolved inventories/enums.
7. Before amending away the prior patch set, save the prior revision as an explicit ref or compare directly against its commit hash. Run migration parity against that immutable input; after amend, `HEAD` no longer denotes the old patch set.
8. Inspect representative beginning/middle/end entities in each large file; do not trust generator self-report.
9. Verify the final repository allowlist contains no Item-2/3/4 implementation or generated artifact. Inspect ignored files too: `git rm` does not remove ignored/untracked generated bundles, caches, or local environments. Delete only explicitly approved artifacts and re-check the real workspace.
10. Stage **all** replacement files, then assert there is no staged/unstaged split and no non-ignored untracked file. Run `git diff --cached --check`, inspect the complete staged patch, preserve the approved Change-Id, and amend locally.
11. Treat asynchronous review findings as revision-bound evidence. Record the reviewed commit/tree state; if the tree changed during review, re-check each finding against the final staged commit and do not apply stale index/scope claims blindly. Resolve valid findings before push.
12. Push the next patch set, query Gerrit, and prove the current patch-set revision equals local `HEAD`. Re-run clean-tree and governed-plan validation before reporting completion.

The Item-1 success criterion is a compact, coherent, human-reviewable YAML contract with honest blanks—not an executable simulator and not a “zero blockers” target gate.

## 9. Common failure modes

- **Runtime-first spiral:** designing PLC allocation, recovery FSM, Modbus probes, or UI command lifecycle before the YAML fields and entities are reviewed.
- **Validation becoming the product:** building a large Python/Pydantic validator framework when the requested artifact is reviewable YAML.
- **Metadata drowning the data:** repeating status/provenance wrappers on every scalar.
- **Invented completeness:** treating unknown lists as empty, filling unresolved inventories/enums with conventional names, deriving physical asset IDs from topology drawings, or keeping a plausible legacy scalar beside “TODO: confirm” instead of using null.
- **Parallel route truths:** storing both ordered blocks and ordered sub-blocks, defining block occupancy again instead of deriving it from detector coverage, or repeating one shared expiry sequence on every route.
- **Unenforced enum SSOT:** defining domain members in a data document while entity schemas accept arbitrary strings, or copying the same literals into every entity schema. Use one referencable canonical enum schema and prove misspellings fail.
- **Overclaiming partial validation:** reporting all signal boundaries as confirmed when the gate only validated non-null references; always publish known/unresolved counts.
- **Stale asynchronous review:** applying index/scope findings from a reviewer that observed an earlier tree without checking the reviewed revision against the final staged commit.
- **Plausible but wrong descriptions:** satisfying a description-presence check with generic generator text that does not explain the actual field.
- **Ignored leftovers:** assuming tracked-file cleanup removed ignored/untracked generated artifacts; inspect the actual workspace before claiming YAML-only scope.
- **Crossing patch boundaries:** including JSON/ST/console preparation in Item 1 because it seems efficient.
- **Defending old work after a reset:** continuing prior plans instead of rebuilding around the user's corrected deliverable.
