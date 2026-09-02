# Provenance snapshot tooling boundaries

Use this review pattern when a repository contains delegated, vendored, mirrored, or authority-owned source snapshots whose exact bytes are provenance/lock inputs and a formatter or linter reports defects inside them.

## Decision rule

A tooling exclusion is justified only when the excluded subtree is an immutable input boundary, not maintained product code. The change must preserve coverage of the engine, tests, repository configuration, schemas where supported by the tool, and workflows. Do not rewrite snapshot bytes merely to satisfy local style rules.

## Review procedure

1. Pin and inspect the exact diff. Confirm it changes only the tool configuration and its contract test; reject lock, snapshot, authority, engine, schema, or workflow-command mutation unless separately authorized.
2. Read the tool's authoritative path-pattern semantics. Prefer a project-root-relative directory pattern over a basename pattern. For Ruff, a pattern containing `/`, such as `src/skill_source`, is relative to the project root; a bare basename can match that name anywhere in the tree.
3. Require a parsed configuration contract with exact equality, not a substring check. Exact equality catches a missing key, changed path, or widening of that list. Do not duplicate the third-party glob engine in the unit test.
4. Run a disposable grammar probe containing the intended excluded subtree, maintained engine/test paths, a prefix sibling such as `src/skill_source_extra`, and a same-named subtree elsewhere such as `other/src/skill_source`. Use `--show-files` or verbose resolver output to prove only the intended root subtree is omitted.
5. Materialize the authority/provenance ref in a disposable worktree and overlay only the reviewed config/test files. Hash every tracked snapshot before and after lint/format commands and compare manifests byte-for-byte. Verify file discovery still includes maintained engine/tests and excludes the intended snapshot subtree.
6. Run unchanged release commands on the generic branch and, when the authority ref is internally runnable, on the disposable authority overlay. Record tests, format, lint, compile, artifact tests, and package builds separately.
7. If the authority ref has a pre-existing guard or fixture failure unrelated to the diff, report it as a verification note rather than a product finding. Still run independent tooling-scope and byte-retention probes.

## Robustness checks

- Inspect every exclusion mechanism, not only the newly added list (`exclude`, `extend-exclude`, formatter-specific, and linter-specific settings).
- Confirm sibling maintained paths remain discoverable by the tool.
- Treat forward-slash config globs as the portable syntax expected by tools that normalize project-relative paths; verify supported CI platforms when portability is binding.
- A green formatter/linter run alone is insufficient: it can pass because too much was hidden. Pair it with file-discovery evidence.
- A clean Git diff alone is insufficient to prove immutable snapshots were retained. Pair it with before/after content hashes in the disposable authority tree.
