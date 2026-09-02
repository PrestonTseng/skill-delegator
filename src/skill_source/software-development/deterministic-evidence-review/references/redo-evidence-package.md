# Redo Evidence Packages

Use this checklist when implementation is already committed and the missing deliverable is an audit/evidence report, with no product changes authorized.

## Snapshot and authority

1. Pin accepted base, exact HEAD, worktree status, binding brief/plan, and any execution summary.
2. Inventory every commit in order with per-commit path lists. Prove test-only and plan-only commits contain no production changes, and that production lands only after the complete contract suite.
3. Never inspect a rejected branch/report/diff when the controller prohibits it. Accepted commit objects plus the supplied summary are sufficient authority.
4. Recheck HEAD and clean status after writing the out-of-tree report.

## RED provenance versus fresh GREEN

Treat these as different evidence classes:

- **Historical RED:** prove from accepted history. Show that the test commit imports/exercises an absent API in its parent, list later regression commits before production, and quote retained output only when it actually exists.
- **Reconstructed RED:** when useful and authorized, check out the pinned test commit in a disposable detached worktree and run the focused command against its pre-fix production tree. Label this as a fresh reconstruction, not retained historical output. Remove the disposable worktree afterward and preserve the exact exit code/failure cause. A collection error is valid RED only when the missing import/API is itself the intended pre-production failure; setup or dependency errors are not.
- **Isolate the reconstruction environment, not only the Git tree.** A detached worktree can still reuse a shared editable install or project virtualenv that imports the current fixed source, producing a false GREEN. First prove the target source/API is absent in the detached tree, then use a fresh/isolated runner (for example `uv run --isolated --with pytest ...`) and, when possible, print or otherwise verify the imported module path. If a supposedly pre-fix reconstruction unexpectedly passes, treat it as contaminated until isolation is proved; do not report it as RED or GREEN evidence.
- **Fresh GREEN:** rerun focused and full suites at pinned HEAD and preserve exact commands, counts, elapsed output, and exit status.
- Never fabricate historical RED counts. If logs retained only the failure cause, say exactly which portions are available: command, cause, regression subject, and commit ordering.

For terse pytest configurations that suppress the count, run the binding command exactly and recover counts with normal collection (`pytest --collect-only -q`) or by clearing repository addopts (for example `pytest -o addopts='' -q`). Prefer collector-reported per-file counts and arithmetic summation over grep patterns against progress output.

## Adjudicating test changes in the GREEN commit

A production commit may need to adapt existing test fixtures or monkeypatches after a private signature or evidence object becomes mandatory. Do not automatically classify every GREEN test edit as test weakening, and do not accept it on author intent alone.

1. Diff the test-only RED commit against the GREEN production commit with zero context.
2. Inventory added/removed `test_*` definitions. Every new behavioral regression should already exist in RED; GREEN should not introduce deferred behavior tests.
3. Inventory changed assertion and exception-expectation lines. Require semantic inspection of every changed assertion; stable counts alone are supporting evidence, not proof.
4. Use an AST check as a compact cross-check: compare test-name sets, `assert` counts, and `pytest.raises` counts before/after.
5. Accept only mechanical adaptations such as supplying a newly mandatory provenance fixture, wrapping a changed helper signature, or updating a monkeypatch from path-based to descriptor-relative arguments while preserving the same injected failure and assertions.
6. Reject removed/weakened assertions, changed expected behavior, fixtures that bypass the new validation, or new tests first appearing in GREEN.
7. Record the exact GREEN test-file numstat and explain each accepted adaptation in the report.

## Static and hygiene verification

- Compile every modified production module and test module.
- Run scoped type checking on the authorized production paths and whole-source type checking separately.
- Namespace-package repositories may require both the source import root and explicit package bases; distinguish an invocation/module-mapping error from code diagnostics, then record the valid command.
- If whole-source diagnostics occur only in unchanged accepted-base files, report the exact count/files as debt. Do not call the gate passing and do not edit unrelated files.
- Run diff check, authorized-path inventory, terminal-newline validation, and final clean-worktree/HEAD checks.

## Finding disposition matrix

For every prior concern, provide:

1. disposition (`closed`, `open`, or `needs independent adjudication`),
2. implementation seam,
3. named regression test or probe,
4. fresh verification result.

Include subtle cases individually: later-time zero-reader reuse, namespace isolation, matching corruption, ambiguity, symlink/no-follow access, private modes, canonical bytes and hashes, order restoration, exact pagination terminators, reader failure propagation, post-publication cleanup, and cleanup ownership.

## Atomic hard-link publication review

Do not equate “atomic” with “rename.” Analyze the actual primitive:

- A temp file created in the destination directory is on the same filesystem.
- Fully write and file-fsync it before publication.
- `link(temp, destination)` atomically installs a complete inode and natively fails if destination exists; readers see absent or complete bytes.
- After linking, temp and destination name the same inode. Unlinking temp decrements the link count without removing destination.
- Directory fsync makes link/unlink metadata durable; reread, byte-compare, and decode verify publication.
- Cleanup should unlink only when destination `(device, inode)` still matches the installed inode, preserving unrelated replacements.

This can be semantically stronger than `replace()` when the contract says never overwrite an existing destination. However, if the specification literally requires an atomic rename, record hard-link installation as an explicit compliance concern rather than silently treating it as identical. A true no-overwrite rename may require a platform primitive such as `renameat2(RENAME_NOREPLACE)`; a check-then-`replace()` sequence is race-prone, and plain `replace()` overwrites.

## Report shape

Write one decision-ready report with:

- status and exact pinned scope,
- full commit/path sequence and test-first proof,
- historical RED provenance with evidence limits,
- fresh GREEN/static/hygiene outputs,
- design analysis,
- complete finding matrix,
- atomic-publication rationale and concern,
- separate specification and quality verdicts,
- files/artifact locations and explicit statement that no product changes occurred.

Keep the chat response short: status, test counts, concerns, and report path. Put the complete evidence package in the report artifact.