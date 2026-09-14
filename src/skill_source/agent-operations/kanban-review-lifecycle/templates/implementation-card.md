# Implementation card fields

Execution route: direct | single-worker | parallel-2
Delegation benefit: none | context | latency | independent-review
Review route: none | same_card | child:<task-id>
Parallel packages: none | <independent package list>
Acceptance criteria: <checkable outcomes>
Stop conditions: <blocking conditions>
Evidence required: <commands, exit codes, results, identities, and scope checks>

Terminal transition:
- `none` → complete this card.
- `same_card` → request review on this card once.
- `child:<task-id>` → confirm that exact existing child depends on this card, then complete this card to release it; do not request same-card review.

Worker boundary: do not delegate, create or rewire tasks, merge, publish, deploy, or apply unless the card separately grants that authority.
