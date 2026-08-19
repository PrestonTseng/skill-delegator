---
name: tapas-redesign-architecture
description: >
  Work on ongoing TAPAS architecture redesign, plcsim topology/wayside YAML
  source-of-truth authoring and migration, service boundaries, generated PLC
  contracts, and dispatch-console integration. Produce reviewable designs and
  keep governed task state under the effective knowledge policy.
---

# TAPAS Redesign Architecture

Use this skill when the user asks for TAPAS redesign research, architecture partitioning, daemon/module maps, CBTC/TMS comparisons, MMS dispatcher workstation design, or follow-up artifacts derived from Jia-Ru/Preston redesign materials.

## Core rule

The overall redesign is **ongoing**. Treat Jia-Ru's files and derived documents as strong design inputs, not final platform truth. Individual design specs may be explicitly approved before the broader redesign; record that approval narrowly and allow implementation planning only for that approved scope. Do not promote one approved sub-design into a claim that the whole redesign is approved.

### Step-by-step review gate

When Preston asks to review each analysis item before approval:

- treat every item as an independent approval gate; approval of Item N does not authorize Item N+1;
- default to presenting the complete conclusion in chat before Confluence publication;
- if Preston explicitly asks for a Confluence page to make review easier, that request authorizes an **`IN REVIEW` review page**, not approval:
  - label the page `IN REVIEW` and state that its conclusions are not approved;
  - organize the main body for human review rather than pasting the raw evidence matrix;
  - keep detailed file/symbol evidence in an appendix or the canonical plan evidence;
  - do not add the unapproved conclusions to the parent summary;
  - after creation, read the page back and verify title, parent, TOC-first, status, and key terminology/decision sections;
- after explicit approval, change the page to `APPROVED`, add only the approved scope to the parent summary, and read both pages back;
- while an item is under review, the parent may show `IN REVIEW` but must not contain that item's unapproved conclusions;
- if a step was published as approved too early, replace the current published body and verify it is withdrawn. Setting an update to `status="draft"` does not retract an already published current version; it can leave the live page unchanged while creating a separate draft.

Do **not** update stable TAPAS memory or the stable `tapas-knowledge` references with redesign conclusions until the applicable scope is approved and implementation planning begins. Keep task state in the canonical plan location selected by the effective knowledge-policy manifest and `plan-policy.md`; do not hardcode a legacy `/opt/data/plans` location. Keep durable working artifacts in an approved workspace such as `/opt/data/workspace/tapas-redesign/`.

## Required starting steps

1. Load `tapas-knowledge` for current TAPAS baseline terminology and service boundaries.
2. Inspect existing redesign artifacts in `/opt/data/workspace/tapas-redesign/` before creating a new draft.
3. If the task touches operating rules, train movement authority, blue-signal/track-worker protection, radio/communications, signaling, route release, TSR/Form-A/Form-B, or other regulatory boundaries:
   - load any relevant railroad/railway rules skill if available,
   - otherwise state clearly that no rule skill/source was available,
   - treat Jia-Ru's rule-sensitive notes as study input only,
   - do not make uncited regulatory assertions.
4. Validate `/opt/knowledge/00-system/policy-manifest.yaml`, load the effective `plan-policy.md`, and create or resume the canonical task plan it selects before deciding durable task-state behavior.

### Current-support audits

When comparing the live TAPAS stack against an approved manual-control, degraded-operation, earthquake, or incident design:

- pin exact Unicorn, Crystal, Thalos, WSS-agent/PLC, tapas-icd, and topology-source commits and inspect dirty state before drawing conclusions;
- audit committed `HEAD`, excluding unrelated local instrumentation from shipped-support claims;
- inspect both the interface contract and runtime implementation. Treat contradictions between ICD enums, handler mappings, API prose, and tests as explicit interface drift rather than choosing the most convenient value;
- classify each function as supported, strong primitive, partial, or missing;
- distinguish integration primitives from governed workflows: DOM is not automatically a persistent hold, route authorization is not automatically a protected corridor, and schedule audit is not operational-command audit;
- trace command intent through Crystal → Unicorn → Thalos → WSS/ADS, then distinguish request accepted, interface ACK, actual applied state, physical proof, and operator-visible final result;
- inspect failure propagation at every boundary. A lower-layer reject or timeout that is only logged can still make an upper REST/GraphQL call look successful;
- for bulk vehicle commands, inspect the actual target-list source. A command cache is neither “all connected vehicles” nor an authoritative all-train census; reconcile expected, connected, reporting, stale, unknown, and non-reporting vehicles explicitly;
- for WSS commands, determine whether ACK means parse receipt, accepted intent, PLC execution, or proved field state. Check sequence/correlation IDs, whether pending request values are echoed as observed state, and whether the ACK has an end-to-end consumer;
- do not infer door/PSD operational support from schema fields alone; inspect mission handlers, WSS status caching, command correlation, and physical-state proof;
- check backend authorization, Crystal route/button guards, command acknowledgment, telemetry freshness, bulk partial-failure behavior, tests, and UI coverage separately;
- inspect fail-safe defaults directly: stale data that is logged as ignored may still update a tracker, and absent occupancy must not silently become `FREE`;
- distinguish current deployed PLC/ST from a YAML-only topology foundation branch; never describe ungenerated YAML as current runtime support;
- produce both a KISS extension and a full-refactor option while preserving the Safety Server/WSS/SS vital boundary. In the KISS option, first test whether existing ADS Type 2/3/4 plus non-service MA can support the operation before proposing an external ADS/TriOps interface change.

See `references/manual-control-support-audit.md` for the capability matrix, evidence rules, interpretation traps, and recommendation format.

### Dispatcher-centered page architecture

When Preston asks to move from system capabilities to the dispatcher user experience:

- start with the complete logical page inventory, not repositories, services, or architecture layers;
- make the **Field Overview topology itself the primary operating surface** for routine train and wayside control. Fleet Control and Wayside Control are capabilities inside Field Overview, not separate peer pages;
- let the dispatcher select trains, signals, switches, blocks, routes, sectors, platforms, PSDs, and power assets directly on topology, preview impact there, confirm there, and observe actual results there;
- use contextual popups only for parameters, reasons, approvals, and confirmation. Do not make a side panel or page switch the default route for routine control;
- treat Emergency Movement as a protected workflow launched from a selected train and route on topology, not automatically as a permanent first-level page;
- for every main page, use the fixed review structure `User goal → Functions → Current Crystal support → Missing functions → Acceptance criteria`;
- distinguish the three physical M1-M3 screens from logical work pages. Do not assign fixed workflow roles to M1, M2, or M3 without an approved operating study;
- map current Crystal pages into target topology interactions before declaring capability missing; compare interaction capability rather than mechanically preserving every current page;
- if Preston asks for the full roadmap view, omit KISS/full-target splitting and show the complete missing work directly;
- define cross-screen context sharing, requested-versus-observed state, data trust, command result persistence, and restart restoration as shared workstation requirements;
- keep the page `IN REVIEW`, use native status controls for support levels, and verify every repeated page subsection after Confluence read-back.

See `references/dispatcher-workstation-page-architecture.md` for the topology-first six-page starting inventory, current Crystal mapping pattern, shared rules, pitfalls, and acceptance-criteria examples.

## Source handling

Known redesign source directory:

- `/opt/data/workspace/tapas-redesign/`

Common source files seen so far:

- `tapas_redesign_20260630.pptx` — Jia-Ru's architecture study covering signaling concepts, event-driven modules, delay/conflict handling, dispatcher UI, TSR/Form-A/Form-B, and TAPAS repartitioning.
- `cbtc_arch.md` — Jia-Ru's CBTC note contrasting train-centric CBTC with integrated wayside ATP / OCC-side ATP.

For PPTX files, extract reviewable text into the same workspace before summarizing, for example:

```bash
python3 - <<'PY'
import zipfile, xml.etree.ElementTree as ET, pathlib, re
ppt = pathlib.Path('/opt/data/workspace/tapas-redesign/tapas_redesign_20260630.pptx')
out = ppt.with_name(ppt.stem + '_extracted.md')
ns = {'a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
with zipfile.ZipFile(ppt) as z:
    slides = sorted(
        [n for n in z.namelist() if re.match(r'ppt/slides/slide\\d+\\.xml$', n)],
        key=lambda n: int(re.search(r'slide(\\d+)\\.xml', n).group(1))
    )
    parts = [f'# Extracted text: {ppt.name}\n\nSlides: {len(slides)}\n']
    for idx, s in enumerate(slides, 1):
        root = ET.fromstring(z.read(s))
        texts = [t.text.strip() for t in root.findall('.//a:t', ns) if t.text and t.text.strip()]
        compact = []
        for x in texts:
            if not compact or compact[-1] != x:
                compact.append(x)
        title = compact[0] if compact else f'Slide {idx}'
        parts.append(f'\n## Slide {idx}: {title}\n\n')
        parts.extend(f'- {x}\n' for x in compact)
out.write_text(''.join(parts), encoding='utf-8')
print(out)
PY
```

## Architecture framing to preserve

Use this as the current working mental model unless later source review changes it:

1. **WSS / Vital wayside + interlocking layer** — validates route safety, field/infrastructure state, route grant/reject/release, signal/wayside output, vital holds.
2. **SS / Safe train movement + vehicle gateway layer** — owns live train tracking needed for MA, Movement Authority, EoA, speed profile, vehicle command gateway, and restriction projection into train authority.
3. **JPS / New_JPS traffic management brain** — evolves from offline planning into live TMS: topology SSoT, timetable, trip activation, progress, delay, route queue, conflict prediction, ATR/regulation, restriction lifecycle metadata.
4. **MMS / Dispatcher workstation** — exception-based human supervision: pages/panels, role-gated commands, track map, timetable, conflict panel, alarms/emergency panel, audit, remote GoA4 workflows.

### M1-M3 naming and workstation rule

- `M1-M3` is **one workstation/display name**, not three roadmap items, maturity levels, releases, or implementation phases.
- It comprises **three real-time screens** for track topology, wayside state, and vehicle state.
- Do not invent a split such as “M1 awareness, M2 control, M3 recovery.” The exact content, area, density, alarm placement, and command placement for each screen remain open until Preston specifies them.
- Model route request, route release, switch control, incident control, and audit as shared workstation/backend capabilities. Do not assign them to M1, M2, or M3 as staged delivery semantics.
- All three screens should consume one versioned topology and one trusted real-time state contract with source time, received time, age, freshness, validity, trust/conflict state, and reason codes.
- All command-capable screens should use one role-gated command gateway with preview, eligibility, confirmation, command ID, per-target result, timeout, rollback/compensation, and audit. The UI must not write PLC state directly.

Important boundary language:

- JPS/TMS decides what to request and in what priority.
- WSS decides whether a route request is safe.
- SS converts granted route/restriction state into MA/EoA/speed profile/vehicle commands.
- MMS displays exceptions and captures dispatcher decisions; it should not become the core traffic brain.

## Wayside source-of-truth delivery sequence

When a redesign repository owns topology/wayside data for simulation, use this strict four-patch sequence unless Preston explicitly changes it:

1. **Human-reviewed YAML SSOT** — derive the exact entity/catalog list from the latest reviewed design rather than copying a legacy list. The current minimum review baseline uses `vertex`, `sub_block`, `block`, `stopping_place`, `switch`, `detection_section`, `signal`, `marker`, `route`, and generic `direction_lock`, with separate line/track and operational catalogs; populate every known TAPAS entity with every schema field and leave unknown values as direct `null # TODO(Preston): <specific question>` entries.
2. **Generated JSON** — only after Item 1 is approved in Gerrit, add deterministic JSON generation for all microservices. JSON derives from YAML; it never becomes a second authoring source.
3. **Generated OpenPLC ST** — only after Items 1–2 are approved, generate ST from the same YAML and prove PLC/Modbus behavior.
4. **Dispatch Console** — only after the data contract is approved, build the Python/FastAPI backend and Angular UI that consume the generated JSON, display live wayside state, and issue switch/block/route commands.

One item equals one Gerrit patch/review cycle. Do not pre-build the next item “to prepare,” and do not let runtime concerns dominate an earlier patch.

### Item-1 authoring rules

- Optimize for a human reviewing Gerrit, not for an internal Python object model.
- Prefer `schemas/*.schema.yaml`, normalized `data/*.yaml`, and a short README. If Preston asks to clean the repository to YAML-only information, remove Python/Pydantic models, tests, package/build files, generated JSON/ST, OpenPLC mappings, runtime code, and stale implementation specs from that patch.
- Keep one data file per entity kind and define each entity/relationship once. Later generators may project denormalized views.
- Put behavioral fields needed by later simulation directly on the owning type: signal aspects/proving/freshness; switch topology/positions/timing; detection coverage/occupancy/timing; route-owned direction-lock requirements; and route path/proof/locking/conflict/overlap/flank/release/expiry. Do not store derived block occupancy inputs on `block`: derive block occupancy from `detection_section.covered_sub_block_ids` through `sub_block.block_id`.
- Model route path, overlap, and release with operational block resources. Keep `sub_block` as the physical topology graph; do not maintain both ordered blocks and ordered sub-blocks as parallel route truths.
- Define domain values once in a canonical referencable enum schema such as `schemas/enums.schema.yaml`, including reviewed numeric interface codes as schema metadata. Every domain-valued asset field must `$ref` that schema so ordinary JSON Schema validation rejects arbitrary strings; prose enum references or a separate data enum plus repeated schema literals are not a sufficient SSOT. If an entire enum is unresolved, make its canonical definition null-only with `# TODO(Preston)` rather than inventing conventional member names.
- Do **not** wrap every value in `state/value/source_refs/unresolved_question`. Known values are direct scalars/lists; unknowns are direct `null` with an actionable inline TODO comment. Use `[]` only for a reviewed empty set. A plausible scalar followed by “TODO: confirm” is still an unknown and must be `null`; do not promote provisional legacy defaults as TAPAS as-built.
- Define shared behavior once and reference it. For example, put a site-level no-entry-expiry profile in `site.yaml` and let routes reference the profile ID rather than duplicating timeout/action fields on every route. The profile must encode the full accepted fail-safe sequence—not only the timer—including restrictive command/proof, approach clear/healthy proof, lock retention, release scope, and retained switch position.
- Keep design evidence outside the formal topology schema unless the user explicitly requires machine-readable provenance. Historical code, decks, screenshots, and prior drafts belong in review documents, commits, and change records; they are not parallel truths or per-object `source` fields. Every cited locator/path must resolve to a retained source, with immutable hashes when a repository commit is unavailable.
- Keep protocol-ID conversion entirely in each service's business logic unless the user explicitly asks for a shared adapter contract. Do not add canonical `interface_mappings`, generated interface maps, or legacy-ID catalogs to the topology model merely to make adapters convenient.
- Do not create a generic station/place hierarchy in the topology SSOT without a safety or infrastructure requirement. For train stops, prefer a graph-attached `stopping_place` defined by `sub_block_ref + milepost_m`; derive its track from the sub-block. Station/platform grouping belongs to timetable, service, or UI models. Model a platform edge or stopping tolerance as a separate reviewed linear feature only when its physical extent is actually required.
- Make ordinary turnout positions directly projectable to railML 3.3-SR2: author one `tip_sub_block_ref` and canonical `left/right` branch facts, use `left/right` in route proof and commands, and generate `NetRelation`, `SwitchIS.leftBranch/rightBranch`, `SwitchIL.branchTip/branchLeft/branchRight`, and `SwitchAndPosition.inPosition` from those same facts. Hardware `normal/reverse` conversion stays in the service adapter; do not invent custom `toward-*` position IDs and hope geometry can recover railML branch semantics.
- Treat a TAPAS `direction_lock` as a route-owned interlocking resource, not a writable static direction flag. Route setting acquires the required value, same-direction routes may share ownership, opposite routes remain blocked while ownership or protected occupancy exists, and release requires the last owner plus safely vacant derived coverage. Do not expose a public `set_direction_lock`; a maintenance recovery may clear a stale lock after fail-safe checks but must not choose a running direction.
- Never invent switch/detection IDs or infer a physical switch from graph degree. If the inventory itself is unconfirmed, use a schema-valid top-level `null # TODO(Preston): provide the complete confirmed inventory`; an empty list falsely asserts that an authorized reviewer confirmed there are no entities.
- Treat schema descriptions as review content, not decoration. Recursively verify every nested property description and reject generic generator text that describes the wrong field.
- **Current approved schema-v2 override:** when the reviewed TAPAS profile defines `block` as the sole logical vacancy-detection identity, do not author a parallel `detection_section`; add physical train-detection elements later only for device-level identity/binding. Define block membership once in `blocks[].sub_block_refs` and derive route/overlap block coverage from ordered sub-block paths. Model `stopping_place` as a point (`sub_block_ref + milepost_m`) with many-to-one attachment to sub-blocks; introduce a separate range/tolerance/platform-edge model only when an extent is explicitly required. Use pairwise `route_conflicts` for independent conflicts such as incompatible switch positions, not to duplicate opposite-direction exclusion already owned by a shared `direction_lock`.
- Every fillable schema must have a connected fictitious `EX-*` example. Before Gerrit publication, validate metaschemas, per-document examples, global IDs/references, graph/switch/path continuity, derived block coverage, direction-lock semantics, and exact route release partitioning; then preserve the Change-Id and verify the pushed Gerrit revision by remote refs read-back.
- Treat a user instruction to “forget the past process and refocus” as a hard design reset: reuse old data only as reference, discard earlier workflow assumptions, and rebuild the patch around the current requested deliverable.

See `references/plcsim-schema-v2-authoring.md` for the approved point/range, block/TVD, route/direction-lock, connected-example, and verification rules.

See `references/topology-data-intake-and-collapsed-trackwork.md` when reviewing the first real site dataset against schema v2.0, especially for unit mismatches, required-but-unresolved TVD fields, high-degree junction audits, or several physical turnouts collapsed into one schematic vertex.

See `references/canonical-yaml-migration-checkpoints.md` for the corrected Item-1 workflow, schema/data shape, cleanup boundary, and verification gates.

See `references/source-of-truth-data-compiler-and-dispatch-console.md` only when Items 2 or 4 are active; do not import its runtime/console concerns into Item 1.

See `references/wayside-simulation-mqtt-interface.md` when defining component state/command ownership, WSS MQTT topics, ACK-versus-completion semantics, simulator injection boundaries, or console/backend runtime contracts. Always re-fetch the live ICD before copying topic or payload details.

See `references/openplc-source-of-truth-contract-planning.md` only when Item 3 is active and Item 1 has been approved.

## Deliverable pattern for module-map tasks

When asked to draw daemons/modules/pages and relations, produce a Markdown artifact in `/opt/data/workspace/tapas-redesign/` with:

1. Status/caveat section distinguishing design input from approved requirements.
2. Overall Mermaid daemon/module map.
3. Runtime sequence diagrams for key flows:
   - normal scheduled trip,
   - delay/conflict/priority override,
   - restriction lifecycle,
   - emergency/global recovery if relevant.
4. MMS page/screen map covering both current known pages and proposed dispatcher-workstation additions.
5. Module responsibilities.
6. Draft data schemas in YAML-style blocks.
7. Candidate event catalog.
8. ADR/open-question list.

For Discord delivery, avoid markdown tables; use bullets, headings, and code blocks.

## Canonical topology review diagrams

When the user needs a topology base with items marked for engineering review:

- generate the drawing from the validated canonical topology, never from presentation artwork or a second hand-maintained graph;
- treat operator monitoring screenshots as display/reference evidence only: they may establish orientation, chainage formatting, site labels, and review hypotheses, but presentation-adjusted shapes and UI groups do not establish topology, detection, point, or safety boundaries;
- preserve supplied screenshots with provenance/hash and keep screenshot-supported signal adjacency as a hypothesis until formally confirmed;
- when an authorized reviewer supplies temporary vertex x/y, preserve it as a complete, strict, provenance-bearing manual-position overlay; merge it deterministically into canonical vertices, keep pixels distinct from GPS/surveyed geometry, use the full canvas for overview sheets, and fit selected coordinates to detail sheets;
- keep confirmed topology, provisional values, legacy discrepancies, and missing engineering inputs as distinct visual layers;
- label graph-derived junctions as candidates only—graph degree does not establish a physical switch or point machine;
- prefer focused overview, issue-overlay, area-detail, and inter-area-connector sheets over one unreadable diagram;
- emit scalable SVG, chat-friendly PNG, and a scrollable HTML index;
- visually inspect rendered PNG pixels and iterate on label collisions, clipping, legends, and known discrepancy prominence;
- keep generated diagrams read-only and write accepted corrections back to canonical YAML/importers before regeneration.

See `references/canonical-topology-review-visualization.md` for the reusable sheet set, visual semantics, label-layout pitfalls, and verification checklist.

### railML-aligned static topology reviews

When reviewing or replacing WSS/OpenPLC topology schemas against railML 3.3-SR2, this subsection overrides the legacy entity list and simulation-behavior assumptions in the earlier Item-1 rules:

- pin and inspect the actual SR2 XSD distribution; verify base-type inheritance, required children, cardinalities, enumerations, and documentation rather than relying on type names;
- use the native split `netElement/netRelation` (physical graph) → functional infrastructure assets → interlocking assets/control-table objects;
- when the reviewed authoring model deliberately retains `vertex`/`sub_block` for graph computation, preserve those authoring names but lower them into one semantic railML-aligned connectivity truth: sub-blocks become `NetElement` objects and validated degree-two endpoint/switch transitions become `NetRelation` objects. Do not maintain a second parallel graph, infer all-to-all junction connectivity from graph degree, or force the authoring YAML to mirror the XSD hierarchy;
- split physical and interlocking views of signals, switches, and detection; split monolithic routes into route, condition, conflict, overlap, and release objects;
- keep runtime/initial state, freshness, legacy interface codes, and PLC address bindings out of static topology;
- identify every non-native TAPAS extension explicitly and justify why no railML element is adequate;
- provide a migration disposition for every existing schema file and cite exact XSD types/elements;
- before publishing a complete design review, run three separate passes—static/XSD fidelity, runtime status/command ownership, and relationship/interaction safety—then reconcile conflicts explicitly rather than merging reviewer recommendations blindly. Prefer the stricter single-writer and achieved-state-proof interpretation when reviewers propose duplicate lock/occupancy truth.

See `references/railml-static-wss-plc-topology-profile.md` for the condensed native mapping, minimal profile, static-boundary exclusions, extension policy, and XSD review checklist. Pair it with `references/wayside-simulation-mqtt-interface.md` for runtime snapshots, command/result phases, ABS direction ownership, and PlatformDoor workflow boundaries.

When the requested authoring source must generate railML XML, one shared JSON bundle, and OpenPLC ST, use `references/minimal-topology-yaml-compiler-pattern.md`. It defines the graph-friendly semantic-IR pattern, current 10-class minimum review baseline, line/track hierarchy, milepost-based stopping places, railML-native switch positions, Type 13 block occupancy, route protection/release partitioning, route-owned direction locks, operational catalogs, and append-only PLC bindings. Treat it as a review pattern until the applicable ADR is accepted.

## Mermaid authoring notes

- Prefer multiple focused Mermaid diagrams over one unreadable mega-diagram.
- For daemon/module-map review artifacts, the first diagram should be a **pure hierarchy**: `daemon → module → responsibility → related logical schema`. Do **not** mix runtime message-flow arrows into that first overview; keep cross-daemon interactions in later sequence diagrams or focused flow diagrams. This is especially important when the user asks for a one-glance view of "which daemons, which modules, which responsibilities, which schemas".
- Use `flowchart LR/TD` for structural maps and `sequenceDiagram` for runtime flows.
- When a schema is grounded in ICD, fetch the live ICD page and explicitly cite the topic/frequency/ACK/field names in the schema note. Keep draft logical schemas clearly labeled as drafts and distinguish them from live ICD payloads.
- Do not stop at the first ICD page the user provides. The ICD is a Docusaurus multi-page spec; when the user names message type numbers, open/navigate the sidebar or direct pages for every requested type and extract the relevant main fields plus linked sub-schema tables before updating architecture diagrams. For daemon/module maps, common grounding pages are Type 2 Vehicle Status, Type 3 MA, Type 7 WSS Status, Type 8 WSS Setting, Type 13 TriOps Setting, Type 17 VSI-v2, and Type 18 VSIES-v2. See `references/icd-grounding-for-daemon-module-maps.md`.
- Mermaid sequence message labels may fail on semicolons in some parsers; use commas or split the message.
- If validating locally, extract Mermaid blocks and use Mermaid JS parser or Mermaid CLI when available. Local parser/browser issues such as DOMPurify errors can be environment-specific; fix concrete Mermaid syntax diagnostics, but do not encode transient local setup failures as design constraints.

## ADRs that should remain visible until resolved

- Certified/vital boundary: WSS only, SS+WSS, or another boundary.
- Topology SSoT: JPS ownership versus SS/WSS versioned local safety snapshots.
- Restriction authority: JPS lifecycle manager versus SS safety state for Scheduled/Effective/Expired behavior.
- Railroad terminology and rule validation for Form-A/Form-B/blue flag/foul time.
- New_JPS modularity: one daemon boundary with internal actors versus separate services.
- MMS command risk model: role gating, confirmation, two-person approval, and audit for emergency stop/revoke, EB reset, creep mode, PSD override, and track-protection commands.
