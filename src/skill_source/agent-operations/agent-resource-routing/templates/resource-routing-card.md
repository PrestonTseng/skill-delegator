# Resource routing fields

Execution route: direct | single-worker | parallel-2
Delegation benefit: none | context | latency | independent-review
Parallel packages: none | <two independent package names>
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
