# Static TrackMap semantic review

Use this when a patch claims to clarify Line / Track / Lane ownership or adds typed location identity to static railway topology.

## Review method

1. **Pin the authoritative vocabulary.** Read the Jira/spec acceptance criteria and approved design inputs. Record the expected Line identity/display name, Track IDs, physical-block membership, and Direction terms. Treat an assignee-authored implementation page as supporting evidence, not authority.
2. **Inventory every competing field.** Search all topology models and constants—not only the changed block model—for `line_id`, `track_id`, `lane_id`, and related aliases. A migration is incomplete when one model uses `line_id=T3` while another still uses `line_id=ET/WT` (track values).
3. **Trace active consumers.** Find comparisons, filtering, validation, serialization, GraphQL/API fields, and error messages that read those identifiers. A mislabeled field may still “work” because a consumer compares it to the old lane value; that is evidence of semantic inconsistency, not compatibility.
4. **Probe value domains deterministically.** Extract enum values and configured constants, then assert whether each field's values belong to the Line or Track domain. Compare physical-block ownership across producer/consumer repositories and detect duplicate or missing ownership.
5. **Compare patch sets.** If the prior patch set had explicit `LineDefinition` / `TrackDefinition`, display names, indexes, or fail-fast validation and the current patch removes them, evaluate the removal against the requirement. Current-inventory tests alone do not prove semantic completeness.
6. **Check documentation drift.** If a current design page still claims hierarchy objects or validation that the patch removed, use that as supporting evidence and ask that code and review evidence be reconciled.

## Finding calibration

- **High:** wrong identity changes live routing, bulletin scope, serialization, or cross-service interpretation.
- **Medium:** the core semantic-clarification requirement remains internally contradictory or omits queryable/display identity needed by the next consumer, even if current comparisons pass.
- **Low/Minor:** naming or documentation drift that cannot plausibly mis-scope behavior.

## Suggested fix shape

Prefer one canonical typed model:

- `line_id` contains only Line values;
- `track_id` contains only Track values;
- compatibility `lane_id` is an explicit alias/serializer where required;
- Line display names and Line → Track → physical Block ownership are queryable without inference from unrelated objects;
- tests cover normal membership plus duplicate, missing, unknown, and cross-model inconsistent ownership.
