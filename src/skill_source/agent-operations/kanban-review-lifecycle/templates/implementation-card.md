# Implementation card fields

Execution route: direct | single-worker | parallel-2 | canonical-kanban
Delegation benefit: none | context | latency | independent-review
Review route: none | same_card | child:<task-id>
Parallel packages: none | <independent package list>
Acceptance criteria: <checkable outcomes>
Stop conditions: <blocking conditions>
Evidence required: <commands, exit codes, results, identities, and scope checks>
Final artifact identity: <commit SHA/head plus tree, or immutable artifact digest>
Verification surface: <same runtime/UI/integration surface, or unavailable with reason>
Verification verdict: VERIFIED | NOT_VERIFIED | INCONCLUSIVE

Terminal transition:
- `none` → complete this card.
- `same_card` → request review on this card once.
- `child:<task-id>` → confirm that exact existing child depends on this card, then complete this card to release it; do not request same-card review.

Worker boundary: do not delegate, create or rewire tasks, merge, publish, deploy, or apply unless the card separately grants that authority.

Identity rule: if the Final artifact identity changes, prior review and verification verdicts are stale and must be rerun. Proxy tests may supplement same-surface proof but cannot replace it; unavailable same-surface proof is `INCONCLUSIVE`.
