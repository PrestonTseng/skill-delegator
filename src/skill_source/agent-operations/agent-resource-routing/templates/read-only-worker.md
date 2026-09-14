# Read-only worker brief

Goal: <one bounded investigation>

Scope:
- Inspect: <exact sources or boundaries>
- Do not inspect: <explicit exclusions>

Authority:
- Read-only.
- Do not edit files or external state.
- Do not delegate, create tasks, redesign the graph, merge, publish, deploy, or apply changes.
- Stop rather than broaden the scope.

Evidence required:
- Scope inspected.
- Exact path and symbol or line range, URL, task ID, or stable locator.
- Material commands or retrieval operations and results.
- Conclusion and confidence.
- Unanswered questions and stop reason.
- Confirmation that no writes, nested delegation, or external actions occurred.

Stop conditions:
- A write, credential, user decision, shared-state coordination, out-of-scope dependency, or broader investigation is required.
