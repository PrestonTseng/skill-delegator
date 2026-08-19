# Canonical topology review visualization

Use this pattern when a TAPAS/SafeART topology or interlocking-data review needs a visual base with unresolved engineering data layered on top.

## Core pattern

1. Treat the validated canonical topology as the only graph source. Do not redraw from a presentation or maintain a second hand-authored graph.
2. Render confirmed physical topology as the stable base layer.
3. Render provisional values, legacy discrepancies, and missing engineering inputs as separate overlays with an explicit legend.
4. Never promote graph structure into an engineered asset. A node with degree >= 3 may be marked as a **junction candidate**, but not as a confirmed switch or point machine.
5. Keep generated SVG/PNG/HTML as derived artifacts. Corrections go back to canonical YAML or the approved importer, followed by full regeneration.

## Recommended sheet set

Prefer several focused sheets over a single dense drawing:

- physical overview;
- provisional milepost and speed overlay;
- signal direction plus `from block -> authorized block` overlay;
- engineering-gap overlay for detection, points, approach, overlap, flank protection, and release;
- area/core detail sheets;
- a separate inter-area connector sheet when long links compress local details.

Give every unresolved item a stable review label shared by the diagram and discrepancy ledger. For graph-derived junction candidates, compact labels such as `J01`, `J02`, etc. are more legible than repeating long warnings at each node; include a visible `Jxx=vertex-id` key.

## Visual semantics

- Confirmed topology: cool/neutral stable colors.
- Provisional values: orange or red, with dashed lines where the entire segment needs review.
- Missing/incomplete source data: red and explicitly named; do not merely rely on color.
- Graph-derived candidates: yellow diamond plus `CANDIDATE ONLY` statement in title/legend.
- State prominently that vertical placement is a review layout, not surveyed geometry, unless coordinates are authoritative.

## Operator monitoring screenshots as reference evidence

When a user supplies a current trackmap/monitoring screenshot:

1. Preserve the original image under the task/repository evidence directory and record its message/source identifier, visible timestamp, and SHA-256.
2. Record the user's authority caveat verbatim. A display whose sub-block shapes were adjusted for presentation is not a topology or geometry source.
3. Use directly visible conventions that improve review continuity, such as:
   - left-to-right chainage orientation;
   - operator-facing `k+` chainage formatting;
   - site/platform names;
   - top/bottom track ordering;
   - visible signal placement as a review clue.
4. Keep raw canonical values available in detail sheets even when operator-facing formatting is added.
5. Treat adjacency-derived signal corrections as hypotheses. For example, a screenshot may support `from block -> authorized block`, but canonical data remains unchanged until a formal signal plan or authorized reviewer confirms it.
6. Do not infer switch geometry, point-machine identity/state, detection limits, overlap, flank protection, approach sections, release tables, or safety ownership boundaries from display shapes or UI groups such as `M1/M2/M3`.
7. Regenerate the full pack and visually re-check orientation and signal-label collision after reversing or otherwise changing the display axis.

## Provisional manual x/y overlays

When an authorized reviewer supplies temporary vertex positions:

1. Keep the supplied positions as an independently reviewable overlay rather than burying them in generated diagrams. Record canvas width/height, units, origin, source/message reference, and `provisional` status.
2. Merge the overlay deterministically into each vertex using a typed structure such as `manual_display_position {coordinate_space_id, x, y, data_status}`. Keep the coordinate-space definition in topology metadata.
3. Validate strict numeric coordinates, coordinate-space references, canvas bounds, duplicate spaces, unknown vertex IDs, and complete vertex coverage. A partial overlay must fail explicitly unless partial overlays are an approved use case.
4. Preserve the physical topology importer as the graph authority. Reapplying the manual-position overlay after a fresh physical import prevents position data from being silently lost.
5. Treat manual pixels and GPS as different coordinate types. Pixel x/y is display placement only—not surveyed geometry, physical distance, signal engineering, detection boundaries, or movement authority. Add GPS later as a separate typed/provenance-bearing location instead of relabeling pixel data.
6. Reviewer-supplied x/y supersedes inferred one-dimensional chainage placement. Remove tests and documentation that assert an old left-to-right axis if the approved layout is folded or multi-row.
7. Render overview sheets against the full supplied canvas. For area/detail sheets, fit the selected manual coordinates to the available page while preserving relative x/y ordering; otherwise small source regions can occupy only a fraction of the page and become unreadable.
8. Expose stable vertex IDs as SVG data attributes so tests can assert that generated positions follow canonical x/y rather than fallback geometry.
9. If the canonical contract gains optional coordinate-space/position fields, bump its schema version appropriately and verify generated JSON, schema, reports, and diagrams together.

## Readability and QA

- Produce SVG as the scalable primary artifact and PNG for chat review; provide a scrollable HTML index.
- Partition area details by edges whose two endpoints are inside the area. Put cross-area edges on a connector sheet instead of allowing them to expand every area view.
- Place edge and node labels on dark/opaque backing boxes. Some SVG rasterizers do not honor `paint-order`; a thick text stroke can cover the fill and make labels appear missing.
- Stagger dense node labels over multiple rows. Use short review IDs in overview sheets and full IDs in detail sheets.
- Keep overview labels sparse: named sites/platforms only. Put `chainage [raw-value]` labels in area details, and show only unresolved vertices on provisional overlays. Adding every raw value to the overview creates avoidable collisions around controlled points.
- Render the PNGs and inspect the pixels, not just the source SVG. Check label collision, clipping, legend clarity, and prominence of known discrepancies. Iterate until there are no blocking visual defects.

## Verification

- Test that all expected sheets are generated.
- Test that every canonical sub-block appears in an overview/detail artifact.
- Assert known discrepancies and review labels appear in the intended overlay.
- Generate twice and compare bytes or hashes for deterministic output.
- Run the repository test, lint, typecheck, build, and `git diff --check` gates after diagram changes.
