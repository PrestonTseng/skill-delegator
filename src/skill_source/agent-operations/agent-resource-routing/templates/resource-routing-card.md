# Resource routing fields

Execution route: direct | single-worker | parallel-2 | canonical-kanban
Delegation benefit: none | context | latency | independent-review
Parallel packages: none | <two independent package names>
Representative pilot: none | <one package that exercises the full contract>
Coordinator-owned synthesis and acceptance: <owner and check>
Acceptance criteria: <checkable outcomes>
Stop conditions: <conditions that return control to Niles>
Evidence required: <stable locators and material results>

Independence gate for `parallel-2`:
- [ ] Exactly two read-only packages are named.
- [ ] Neither package needs the other's result to begin.
- [ ] They share no mutable state or write ownership.
- [ ] Each has separate acceptance checks.
- [ ] Both child briefs prohibit nested delegation and external actions.

Decision note: <why the selected route has lower total accepted-task cost than the alternatives>

Canonical Kanban gate:
- [ ] Work is durable, mutating, or multi-phase; a coherent reversible task stays direct.
- [ ] The canonical task contract reference is complete and names the Review route.
- [ ] One representative pilot runs before rolling fan-out.
- [ ] Later packages are independent in dependencies, mutable state, and acceptance checks.
- [ ] Completion and blockers are recorded in Kanban state; no duplicate lane, Arena, or nested delegation is used.
